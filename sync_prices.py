"""Daily price snapshot for HelloFresh scanner, based on Checkjebon open price data.

Fail closed: no price if unit or ingredient match is uncertain. A Checkjebon
price is not automatically an AH Bonus/Jumbo action. Data source has incomplete
Lidl shelf coverage, so those recipes stay explicitly unpriced.
"""
from __future__ import annotations
import datetime as dt
import json, math, os, re, unicodedata, urllib.request
from collections import defaultdict
from pathlib import Path

SOURCE = 'https://raw.githubusercontent.com/supermarkt/checkjebon/main/data/supermarkets.json'
AGENT = 'HelloFreshSupermarktscanner/1.0 (https://github.com/DASPHHS/Supermarktscanner)'
STORES = {'ah':'AH','jumbo':'Jumbo','lidl':'Lidl'}
BLOCKED = {'saus','soep','maaltijd','pizza','dip','chips','wrap','quiche','poeder','smaak','puree','snack','burger','gevuld','gekruid','kruidenmix'}

def norm(text: str) -> str:
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def ingredient_parts(label: str):
    m = re.search(r'\((g|ml|stuk\(s\)|el|tl|plakje\(s\)|zakje\(s\))\)', label, flags=re.I)
    if not m:
        return norm(label.replace('*','')), None
    return norm(label[:m.start()].replace('*','').replace('[','').replace(']','')),m.group(1).lower()

def number(raw):
    raw=raw.strip().replace(',','.')
    for k,v in [('½','.5'),('¼','.25'),('¾','.75')]: raw=raw.replace(k,v)
    try: return float(raw)
    except ValueError:return None

def amount(product_size):
    """Return size in g/ml/stuks, explicitly refusing ambiguous formats."""
    s=norm(product_size)
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(kg|kilogram|g|gram|liter|l|ml|milliliter|stuks|stuk)',s):
        v=float(m.group(1));u=m.group(2)
        if u in ('kg','kilogram'):return v*1000,'g'
        if u in ('g','gram'):return v,'g'
        if u in ('liter','l'):return v*1000,'ml'
        if u in ('ml','milliliter'):return v,'ml'
        if u in ('stuk','stuks'):return v,'stuk'
    return None,None

def unit_quantity(quantity,unit):
    if unit=='g':return quantity,'g'
    if unit=='ml':return quantity,'ml'
    if unit=='stuk(s)':return quantity,'stuk'
    if unit=='plakje(s)':return quantity,'stuk'
    if unit=='el':return quantity*15,'ml'
    if unit=='tl':return quantity*5,'ml'
    return None,None

def products(source):
    if not isinstance(source,list):raise ValueError('Checkjebon schema veranderd: supermarktdata geen array')
    index=defaultdict(list)
    for shop in source:
        code=str(shop.get('n','')).lower()
        if code not in STORES:continue
        if not isinstance(shop.get('d'),list):continue
        for row in shop['d']:
            if not isinstance(row,dict):continue
            name=row.get('n');value=row.get('p');s=row.get('s')
            if not isinstance(name,str) or not isinstance(value,(int,float)) or value<=0 or value>1000:continue
            qty,u=amount(str(s or ''))
            if qty is None:continue
            index[STORES[code]].append({'name':name,'n':norm(name),'price':round(value,2),'quantity':qty,'unit':u,'amount':s,'link':str(shop.get('u',''))+str(row.get('l','')) if row.get('l') else None})
    if not index['Jumbo'] or not index['AH']:raise ValueError('Geen actuele Jumbo/AH-productrecords; vorige snapshot behouden')
    return index

def matches(name,product_name):
    target=name.split();candidate=product_name.split()
    if not target or not all(t in candidate for t in target):return False
    # Prevent accidental matches to soups/sauces/meal products when the recipe needs a raw item.
    if any(t in candidate and t not in target for t in BLOCKED):return False
    return True

def calculate(recipe, catalog, store):
    matched=[];missing=[];used=0.;cash=0.; seen=set()
    for ing in recipe['ingredients_4p']:
        label=ing['ingredient'];name,unit=ingredient_parts(label)
        if name in seen:continue
        seen.add(name)
        if name.startswith('water') or name=='peper zout':
            matched.append({'ingredient':label,'status':'voorraad','cost':0})
            continue
        qty=number(str(ing['quantity_4p_source']));needed,u=unit_quantity(qty,unit) if qty is not None else (None,None)
        if needed is None:
            missing.append({'ingredient':label,'reason':'eenheid/hoeveelheid controleren'})
            continue
        candidates=[p for p in catalog.get(store,[]) if p['unit']==u and matches(name,p['n'])]
        if not candidates:
            missing.append({'ingredient':label,'reason':'geen veilig product- of eenheidsmatch'})
            continue
        offers=[(math.ceil(needed/p['quantity'])*p['price'],p) for p in candidates]
        price,p=min(offers,key=lambda x:(x[0],x[1]['price']/x[1]['quantity']))
        packs=math.ceil(needed/p['quantity'])
        use=needed*p['price']/p['quantity']
        used+=use;cash+=price
        matched.append({'ingredient':label,'quantity':needed,'unit':u,'product':p['name'],'package_size':p['amount'],'package_price':p['price'],'packages':packs,'used_cost':round(use,2),'cash_cost':round(price,2),'link':p['link'],'status':'REGULIERE BRONPRIJS; actie niet bevestigd'})
    # A complete product match is not evidence that OCR quantities, ingredients,
    # or the four-portion basis were checked against the original recipe card.
    # Require explicit positive manual sign-offs; never infer approval from
    # having no unmatched products.
    validated=(recipe.get('quality')=='verified'
               and recipe.get('pricing_eligible') is True
               and recipe.get('ingredients_verified') is True
               and recipe.get('quantities_verified') is True
               and recipe.get('servings_verified') is True
               and recipe.get('servings')==4)
    complete=bool(recipe.get('ingredients_4p')) and not missing and validated
    return {'recipe_id':recipe['id'],'store':store,'complete':complete,'price_per_portion_eur':round(used/4,2) if complete else None,'used_cost_4p_eur':round(used,2) if complete else None,'whole_packages_eur':round(cash,2) if complete else None,'known_cost_eur':round(used,2),'matches':matched,'missing':missing,'recipe_review_required':not validated,
            'ingredient_matches_complete':bool(recipe.get('ingredients_4p')) and not missing,
            'validation_missing':[] if validated else [key for key in ('quality','pricing_eligible','ingredients_verified','quantities_verified','servings_verified','servings') if not (recipe.get(key)=='verified' if key=='quality' else recipe.get(key)==4 if key=='servings' else recipe.get(key) is True)]}

def run(repo_dir:Path,source_json=None):
    data=json.loads((repo_dir/'recipes_extracted.json').read_text(encoding='utf8'))
    if source_json is None:
        request=urllib.request.Request(SOURCE,headers={'User-Agent':AGENT})
        with urllib.request.urlopen(request,timeout=45) as resp:source_json=json.load(resp)
    catalog=products(source_json)
    output={'fetched_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'Checkjebon open product prices; NOT confirmed promotions','limitations':['No verified Lidl full assortment in Checkjebon','Prices can differ by branch','Ingredient substitutions and 4p PDF parsing require manual review','Only exact ingredient words with compatible package units are priced'],'stores':{s:len(catalog.get(s,[])) for s in STORES.values()},'results':[]}
    for r in data['recipes']:
        for s in STORES.values():output['results'].append(calculate(r,catalog,s))
    # Protect against publishing an empty or stale price snapshot.
    if not any(x['complete'] for x in output['results']):
        # Still publish partial coverage for diagnostics; never claim full costs.
        output['warning']='Geen volledig verifieerbare recepten; exacte prijzen worden onderdrukt.'
    (repo_dir/'recipe_prices.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    return output

if __name__=='__main__':
    x=run(Path(os.environ.get('REPO_DIR','.')))
    print('Prices fetched',x['stores'],'fully matched',sum(i['complete'] for i in x['results']))