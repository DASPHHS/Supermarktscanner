"""Daily price snapshot for HelloFresh scanner, based on Checkjebon open price data.

Fail closed: no price if unit or ingredient match is uncertain. A Checkjebon
price is not automatically an AH Bonus/Jumbo action. Data source has incomplete
Lidl shelf coverage, so those recipes stay explicitly unpriced.
"""
from __future__ import annotations
import datetime as dt
import json, math, os, re, unicodedata, urllib.request
from fractions import Fraction
from collections import defaultdict
from pathlib import Path

SOURCE = 'https://raw.githubusercontent.com/supermarkt/checkjebon/main/data/supermarkets.json'
AGENT = 'HelloFreshSupermarktscanner/1.0 (https://github.com/DASPHHS/Supermarktscanner)'
STORES = {'ah':'AH','jumbo':'Jumbo','lidl':'Lidl'}
BLOCKED = {'saus','soep','maaltijd','pizza','dip','chips','wrap','quiche','poeder','smaak','puree','snack','burger','gevuld','gekruid','kruidenmix','salade','hummus','hoemoes','gebakken','geroosterd','vegetarisch','vegetarische','vegan','plantaardig','plantaardige','chocolade','surprise','snoep','gedroogd','gedroogde','zongedroogd','zongedroogde','granulaat'}
QUALIFIERS=set('ah jumbo lidl albert heijn biologisch biologische bio verse vers extra vierge mild milde naturel ongezouten gezouten gesneden heel hele kruimig vastkokend vastkokende fijne fijn grof grove zoutarm zoutarme g gr gram kg ml milliliter liter l stuk stuks st'.split())

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
    fractions={'½':.5,'¼':.25,'¾':.75,'⅓':1/3,'⅔':2/3,'⅛':.125,'⅜':.375,'⅝':.625,'⅞':.875}
    try:
        if raw and raw[-1] in fractions:
            prefix=raw[:-1].strip()
            if prefix and not re.fullmatch(r'\d+',prefix):return None
            value=(float(prefix) if prefix else 0)+fractions[raw[-1]]
        elif re.fullmatch(r'(?:\d+\s+)?\d+/[1-9]\d*',raw):
            parts=raw.split();value=sum(float(Fraction(p)) for p in parts)
        elif re.fullmatch(r'\d+(?:\.\d+)?',raw):value=float(raw)
        else:return None
        return value if math.isfinite(value) and value>=0 else None
    except (ValueError,ZeroDivisionError):return None

def amount(product_size):
    """Return size in g/ml/stuks, explicitly refusing ambiguous formats."""
    # Normalization for product names removes decimal punctuation. Never use it
    # for quantities: 1.5 kg otherwise becomes 5 kg, and 1,5 l becomes 5 l.
    s=str(product_size).strip().lower().replace(',','.')
    if s in ('per stuk','per stuks'):return 1.,'stuk'
    m=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(kilogram|kg|gram|g|milliliter|ml|liter|l|stuks|stuk)',s)
    if m:
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
    # One counted cheese block or loaf is not one slice.
    if unit=='plakje(s)':return None,None
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
            if qty is None or qty<=0 or not math.isfinite(value):continue
            index[STORES[code]].append({'name':name,'n':norm(name),'price':round(value,2),'quantity':qty,'unit':u,'amount':s,'link':str(shop.get('u',''))+str(row.get('l','')) if row.get('l') else None})
    if not index['Jumbo'] or not index['AH']:raise ValueError('Geen actuele Jumbo/AH-productrecords; vorige snapshot behouden')
    return index

def matches(name,product_name):
    target=name.split();candidate=product_name.split()
    if not target or not all(t in candidate for t in target):return False
    # Prevent accidental matches to soups/sauces/meal products when the recipe needs a raw item.
    if any(t in candidate and t not in target for t in BLOCKED):return False
    # All unexplained words matter. A one-word overlap such as 'ui' does not
    # turn Filet Americain Ui or a Peen-en-Ui mixture into a raw onion.
    return all(t in target or t in QUALIFIERS or re.fullmatch(r'\d+(?:g|gr|gram|kg|ml|l|st|stuks|x)?',t) for t in candidate)

def calculate(recipe, catalog, store, servings=4):
    if servings not in (2,4):raise ValueError('Alleen bronkolommen voor 2 of 4 porties worden ondersteund')
    matched=[];missing=[];used=0.;cash=0.; seen=set()
    ingredients=recipe.get(f'ingredients_{servings}p') or []
    if not ingredients and servings==2:
        missing.append({'ingredient':'Bronkolom voor twee personen','reason':'ontbreekt; niet afgeleid door vierpersoonskolom te halveren'})
    for ing in ingredients:
        label=ing['ingredient'];name,unit=ingredient_parts(label)
        if name in seen:
            missing.append({'ingredient':label,'reason':'dubbele ingrediëntregel; broncontrole en samenvoeging nodig'})
            continue
        seen.add(name)
        if name=='water':
            matched.append({'ingredient':label,'status':'voorraad','cost':0})
            continue
        qty=number(str(ing.get(f'quantity_{servings}p_source','')))
        # A tablespoon of dry seasoning or butter is not 15 millilitres of a
        # product sold by weight. Only explicit liquid spoon measures convert.
        liquid=name in {'olijfolie','extra vierge olijfolie','zonnebloemolie','wittewijnazijn','rodewijnazijn','balsamicoazijn','sojasaus','water'}
        needed,u=unit_quantity(qty,unit) if qty is not None and (unit not in ('el','tl') or liquid) else (None,None)
        if needed is None or not math.isfinite(needed) or needed <= 0:
            missing.append({'ingredient':label,'reason':'eenheid/hoeveelheid controleren (positieve hoeveelheid vereist)'})
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
    complete=bool(ingredients) and not missing and validated
    result={'recipe_id':recipe['id'],'store':store,'complete':complete,
            'servings':servings,
            'price_per_portion_eur':round(used/servings,2) if complete else None,
            'used_cost_eur':round(used,2) if complete else None,
            'used_cost_4p_eur':round(used,2) if complete and servings==4 else None,
            'whole_packages_eur':round(cash,2) if complete else None,
            'known_cost_eur':round(used,2),'matches':matched,'missing':missing,
            'recipe_review_required':not validated,
            'ingredient_matches_complete':bool(ingredients) and not missing}
    # Keep the large daily snapshot compact; detailed sign-off diagnostics
    # are useful only when every ingredient already has a price match.
    if result['ingredient_matches_complete'] and not validated:
        result['validation_missing']=[key for key in
            ('quality','pricing_eligible','ingredients_verified',
             'quantities_verified','servings_verified','servings')
            if not (recipe.get(key)=='verified' if key=='quality'
                    else recipe.get(key)==4 if key=='servings'
                    else recipe.get(key) is True)]
    return result

def run(repo_dir:Path,source_json=None):
    from indicative_prices import prepare_catalog,add_market_products,estimate_with_sensitivity,VERSION,FAMILIES,SPOONS
    from zoneinfo import ZoneInfo
    data=json.loads((repo_dir/'recipes_extracted.json').read_text(encoding='utf8'))
    if source_json is None:
        request=urllib.request.Request(SOURCE,headers={'User-Agent':AGENT})
        with urllib.request.urlopen(request,timeout=45) as resp:source_json=json.load(resp)
    catalog=products(source_json)
    estimate_catalog=prepare_catalog(source_json)
    market_path=repo_dir/'market_deals.json'
    market=json.loads(market_path.read_text()) if market_path.exists() else {}
    try:
        market_at=dt.datetime.fromisoformat(market['updated_at_utc'])
        if market_at.tzinfo is None:market_at=market_at.replace(tzinfo=dt.timezone.utc)
        if not 0<=(dt.datetime.now(dt.timezone.utc)-market_at).total_seconds()<48*3600:market={}
    except (KeyError,ValueError,TypeError):market={}
    today=dt.datetime.now(ZoneInfo('Europe/Amsterdam')).date()
    add_market_products(estimate_catalog,market,today)
    output={'fetched_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'servings':2,'location':'Bleiswijk; landelijke bronprijzen, geen filiaalbevestiging','source':'Checkjebon open product prices; NOT confirmed promotions','limitations':['No verified Lidl full assortment in Checkjebon','Prices can differ by branch','Ingredient substitutions and PDF parsing require manual review','Only exact ingredient words with compatible package units are priced','Two-person source column required; no automatic halving'],'stores':{s:len(catalog.get(s,[])) for s in STORES.values()},'results':[]}
    output['estimate_policy']={'version':VERSION,'label':'Indicatieve prijsraming met zichtbare normgewichten',
        'weights_g_per_piece':{f:v for f,(_,v) in FAMILIES.items() if v is not None},
        'spoon_rules':{f:{'quantity_per_tablespoon':v,'unit':u,'note':note,'source':source} for f,(v,u,note,source) in SPOONS.items()},
        'notes':['Alleen recepten met herstelde tweepersoonskolom kunnen volledig geraamd worden.',
                 'Prijsramingen zijn geen handmatig geverifieerde receptprijzen.',
                 'Onbekende ingrediënten en ontbrekende prijzen worden niet als nul gerekend.',
                 'Verbruikskosten verdelen voordeelverpakkingen over alle gekochte inhoud; gebruik de rest ook op.',
                 'Kassabedrag omvat hele verpakkingen; geen voorraad verondersteld. Water en energie buiten vergelijking.',
                 'Bonus en herkenbare kaartacties tellen alleen mee met de kaartoptie aan.',
                 'Prijs- en actiegegevens via Checkjebon en PrijsProfeet; beschikbaarheid en filiaalprijzen kunnen afwijken.']}
    for r in data['recipes']:
        for s in STORES.values():
            record=calculate(r,catalog,s,servings=2)
            deals=market.get('stores',{}).get(s,{}).get('deals',[])
            record['estimate']=estimate_with_sensitivity(r,estimate_catalog,s,deals,today,cards=False)
            if any(d.get('card_required') or d.get('loyalty_program') or d.get('loyalty_price') is not None for d in deals):
                with_cards=estimate_with_sensitivity(r,estimate_catalog,s,deals,today,cards=True)
                if dict(with_cards,cards_included=False)!=record['estimate']:record['estimate_with_cards']=with_cards
            output['results'].append(record)
    output['estimate_counts']={s:sum(x['store']==s and x['estimate']['eligible'] for x in output['results']) for s in STORES.values()}
    if not any(output['estimate_counts'].values()) and (repo_dir/'recipe_prices.json').exists():
        previous=json.loads((repo_dir/'recipe_prices.json').read_text())
        if any(previous.get('estimate_counts',{}).values()):
            raise RuntimeError('Geen volledige ramingen in nieuwe brondata; vorige bruikbare snapshot behouden')
    # Protect against publishing an empty or stale price snapshot.
    if not any(x['complete'] for x in output['results']):
        # Still publish partial coverage for diagnostics; never claim full costs.
        output['warning']='Geen volledig verifieerbare recepten; exacte prijzen worden onderdrukt.'
    (repo_dir/'recipe_prices.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    return output

if __name__=='__main__':
    x=run(Path(os.environ.get('REPO_DIR','.')))
    print('Prices fetched',x['stores'],'fully matched',sum(i['complete'] for i in x['results']))
    print('Indicatieve ramingen per winkel:',x['estimate_counts'])
