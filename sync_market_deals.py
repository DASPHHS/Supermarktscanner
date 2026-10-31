"""Collect active food promotions for the HelloFresh and Plated recipe browser.

Source: public PrijsProfeet search API. Active promotion only, never impute shelf price.
"""
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone, date
from pathlib import Path

BASE="https://www.prijsprofeet.nl/api/v1/search"
TERMS=("boerenkool","rookworst","aardappelen","pompoen","sperziebonen","gehakt",
       "bospeen","vivera","kipfilet","walnoten","champignons","spinazie",
       "courgette","tomaten","broccoli","rijst","pasta","tofu","zalm",
       "ui","wortel","paprika","kikkererwten","kokosmelk","kaas","eieren","olijfolie","boter",
       "witte wijnazijn","lasagnebladen","garam masala","krieltjes","Italiaanse kruiden","gemberpuree","zout","peper")
STORES={"Jumbo":"jumbo","AH":"albertheijn","Lidl":"lidl"}
UA="HelloFresh-Supermarktscanner/1.0 (+https://github.com/DASPHHS/Supermarktscanner)"
def normalize(s):
    return "".join(x for x in str(s or "").lower() if x.isalnum())
# Search results are not guaranteed to be foods or to contain the
# searched ingredient. Reject obvious false positives rather than display
# detergent, cosmetics or meal mixes as ingredient promotions.
NONFOOD_WORDS=("wasmiddel","wasverzachter","vaatwas","shampoo","conditioner",
               "douchegel","deodorant","tandpasta","schoonmaak","allesreiniger",
               "toiletpapier","keukenpapier","kattenvoer","hondenvoer",
               "geurkaars","luchtverfrisser","zeep","waspoeder")
PREPARED_MIX_WORDS=("cup-a-soup","bakplaat mix","maaltijdmix","soepmix")
SINGULAR_TERMS={"aardappelen":"aardappel","sperziebonen":"sperzieboon",
                "champignons":"champignon","tomaten":"tomaat",
                "walnoten":"walnoot","wortelen":"wortel"}

def is_relevant_food(name,term):
    text=unicodedata.normalize("NFKD",str(name or "").casefold())
    text="".join(c for c in text if not unicodedata.combining(c))
    if any(word in text for word in NONFOOD_WORDS+PREPARED_MIX_WORDS):
        return False
    term=term.casefold()
    if term=="ui":
        return bool(re.search(r"(?<![a-z])ui(?![a-z])",text))
    return term in text or SINGULAR_TERMS.get(term,"\\x00") in text

CORE_TERMS=("aardappelen","ui","wortel","kipfilet","broccoli","tomaten",
            "rijst","pasta","eieren","kaas","kikkererwten","kokosmelk")
ROTATING_TERMS=12

def select_terms(day, families):
    """Bound requests and rotate extra ingredients without hiding partial coverage."""
    all_terms=tuple(dict.fromkeys(TERMS+tuple(families)))
    core=tuple(t for t in CORE_TERMS if t in all_terms)
    others=tuple(t for t in all_terms if t not in core)
    if not others:
        return core,len(all_terms)
    start=(day.toordinal()*ROTATING_TERMS)%len(others)
    extra=tuple(others[(start+i)%len(others)] for i in range(min(ROTATING_TERMS,len(others))))
    return core+extra,len(all_terms)

def query(term):
    url=BASE+"?"+urllib.parse.urlencode({"q":term,"page_size":25})
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    # Public search is rate-limited. A bounded, sequential request stream
    # avoids the burst of parallel searches that previously caused HTTP 429.
    time.sleep(1.5)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=20) as f:
                return json.load(f)
        except urllib.error.HTTPError as exc:
            if exc.code!=429 or attempt==2:
                raise
            retry_after=exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay=max(1.0,min(float(retry_after),15.0))
            except (ValueError,TypeError):
                delay=4.0*(attempt+1)
            time.sleep(delay)

def main(out="market_deals.json"):
    from indicative_prices import FAMILIES
    from zoneinfo import ZoneInfo
    today=datetime.now(ZoneInfo("Europe/Amsterdam")).date().isoformat()
    terms,all_terms_count=select_terms(date.fromisoformat(today),FAMILIES)
    now=datetime.now(timezone.utc).isoformat()
    result={"updated_at_utc":now,"source":"PrijsProfeet API /search",
            "limitations":["Rotating partial food-term search; not a complete assortment",
                           "All products must be active, not upcoming/historical",
                           "Promotion is not automatically applied to recipe price"],
            "search_coverage":{"requested_terms":len(terms),
                               "available_terms":all_terms_count,
                               "complete":len(terms)==all_terms_count},
            "stores":{k:{"updated_at":now,"deals":[],"products":[]} for k in STORES}}
    seen={k:set() for k in STORES}
    product_seen={k:set() for k in STORES}
    errors=[]
    def fetch_term(term):
        try:
            return term,query(term),None
        except Exception as exc:
            return term,None,term+": "+type(exc).__name__+": "+str(exc)[:120]
    for term in terms:
        term,data,error=fetch_term(term)
        if error:
            errors.append(error)
            continue
        for p in data.get("results",[]):
            retailer=normalize(p.get("retailer"))
            target=next((k for k,v in STORES.items()
                         if retailer==v or (k=="AH" and retailer in ("ah","albertheijn"))),None)
            if not target:continue
            name=str(p.get('name') or '').strip()
            identity=str(p.get('base_product_id') or p.get('product_id') or (name+'|'+str(p.get('quantity'))))
            # Keep dated product records as a second price source; ingredient
            # identity is checked again by the indicative price engine.
            extracted=str(p.get('extracted_at') or '')[:10]
            try:recent=0<=(date.fromisoformat(today)-date.fromisoformat(extracted)).days<=3
            except ValueError:recent=False
            shelf=p.get('original_price') if p.get('is_promotional') else p.get('price')
            if recent and name and identity not in product_seen[target] and isinstance(shelf,(int,float)) and shelf>0 and p.get('quantity'):
                product_seen[target].add(identity)
                result['stores'][target]['products'].append({
                    'name':name,'quantity':p['quantity'],'price':shelf,'product_url':p.get('product_url'),
                    'product_id':p.get('product_id'),'base_product_id':p.get('base_product_id'),
                    'extracted_at':p.get('extracted_at'),'source':'PrijsProfeet product search'})
            if p.get("promotion_status")!="active":continue
            start=str(p.get("valid_from") or "")[:10]
            end=str(p.get("valid_until") or "")[:10]
            try:
                date.fromisoformat(start);date.fromisoformat(end)
            except ValueError:continue
            if start>today or end<today:continue
            name=str(p.get("name") or "").strip()
            if not name or not is_relevant_food(name,term):continue
            key=str(p.get("product_id") or p.get("id") or (target+":"+name.casefold()))
            if key in seen[target]:continue
            seen[target].add(key)
            pct=p.get("savings_percentage")
            original=p.get("original_price")
            price=p.get("price")
            discount=("%g%% korting" % pct if isinstance(pct,(float,int)) and pct>0 else "Actieve aanbieding")
            detail={field:p.get(field) for field in (
                'product_id','base_product_id','ean','quantity','product_url','promotion_type',
                'multi_buy_quantity','multi_buy_price','loyalty_program','loyalty_price',
                'max_per_customer','in_store_only','online_only','valid_until_estimated')}
            detail['card_required']=(target=='AH' or bool(p.get('loyalty_program')) or p.get('loyalty_price') is not None
                or any('plus' in str(x).casefold() or 'extra' in str(x).casefold() for x in p.get('promotional_keywords',[])))
            detail['personal_offer']=any(any(word in str(x).casefold() for word in ('persoonlijk','personal','bonus box','bonusbox')) for x in p.get('promotional_keywords',[]))
            result["stores"][target]["deals"].append({**detail,"name":name,"discount":discount,
                "price":price,"original_price":original,
                "valid_from":start,"valid_until":end,"source_term":term,
                "source_url":"https://www.prijsprofeet.nl/supermarkt-aanbiedingen-api/"})
    if len(errors)>max(3,len(terms)//5):
        raise RuntimeError("Te veel bronfouten; vorige volledige actiesnapshot behouden. "+str(errors[:3]))
    result["errors"]=errors[:25]
    result["search_coverage"]["successful_terms"]=len(terms)-len(errors)
    for v in result["stores"].values():
        v["deals"].sort(key=lambda x:(-float(x["discount"].split("%")[0]) if "%" in x["discount"] else 0,x["name"]))
    if not any(v["deals"] for v in result["stores"].values()):
        raise RuntimeError("No active food promotions fetched; retain last successful snapshot. "+str(errors[:3]))
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Live food deals:",{k:len(v["deals"]) for k,v in result["stores"].items()},"search errors:",len(errors))
if __name__=="__main__":main()
