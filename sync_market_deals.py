"""Collect active food promotions for the HelloFresh and Plated recipe browser.

Source: public PrijsProfeet search API. Active promotion only, never impute shelf price.
"""
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

BASE="https://www.prijsprofeet.nl/api/v1/search"
TERMS=("boerenkool","rookworst","aardappelen","pompoen","sperziebonen","gehakt",
       "bospeen","vivera","kipfilet","walnoten","champignons","spinazie",
       "courgette","tomaten","broccoli","rijst","pasta","tofu","zalm",
       "ui","wortel","paprika","kikkererwten","kokosmelk")
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

def query(term):
    url=BASE+"?"+urllib.parse.urlencode({"q":term,"page_size":25})
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as f:
        return json.load(f)
def main(out="market_deals.json"):
    today=date.today().isoformat()
    now=datetime.now(timezone.utc).isoformat()
    result={"updated_at_utc":now,"source":"PrijsProfeet API /search",
            "limitations":["Food term search is a selection, not a complete assortment",
                           "All products must be active, not upcoming/historical",
                           "Promotion is not automatically applied to recipe price"],
            "stores":{k:{"updated_at":now,"deals":[]} for k in STORES}}
    seen={k:set() for k in STORES}
    errors=[]
    for term in TERMS:
        try:
            data=query(term)
        except Exception as exc:
            errors.append(term+": "+type(exc).__name__+": "+str(exc)[:120])
            continue
        for p in data.get("results",[]):
            retailer=normalize(p.get("retailer"))
            target=next((k for k,v in STORES.items()
                         if retailer==v or (k=="AH" and retailer in ("ah","albertheijn"))),None)
            if not target or p.get("promotion_status")!="active":continue
            start=str(p.get("valid_from") or "")[:10]
            end=str(p.get("valid_until") or "")[:10]
            try:
                date.fromisoformat(start);date.fromisoformat(end)
            except ValueError:continue
            if start>today or end<today:continue
            name=str(p.get("name") or "").strip()
            if not name or not is_relevant_food(name,term):continue
            key=str(p.get("id") or (target+":"+name.casefold()))
            if key in seen[target]:continue
            seen[target].add(key)
            pct=p.get("savings_percentage")
            original=p.get("original_price")
            price=p.get("price")
            discount=("%g%% korting" % pct if isinstance(pct,(float,int)) and pct>0 else "Actieve aanbieding")
            result["stores"][target]["deals"].append({"name":name,"discount":discount,
                "price":price,"original_price":original,
                "valid_from":start,"valid_until":end,"source_term":term,
                "source_url":"https://www.prijsprofeet.nl/supermarkt-aanbiedingen-api/"})
    result["errors"]=errors[:25]
    for v in result["stores"].values():
        v["deals"].sort(key=lambda x:(-float(x["discount"].split("%")[0]) if "%" in x["discount"] else 0,x["name"]))
    if not any(v["deals"] for v in result["stores"].values()):
        raise RuntimeError("No active food promotions fetched; retain last successful snapshot. "+str(errors[:3]))
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Live food deals:",{k:len(v["deals"]) for k,v in result["stores"].items()},"search errors:",len(errors))
if __name__=="__main__":main()
