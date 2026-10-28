"""Public, verifiable supermarket promotion snapshot for the recipe UI.

Does NOT claim matched recipe totals. Stores only active promotions and dates.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API="https://www.prijsprofeet.nl/api/v1/deals/top"
STORES={"Jumbo":"jumbo","AH":"albert_heijn","Lidl":"lidl"}
def fetch(store):
    url=API+"?"+urllib.parse.urlencode({"retailer":store,"limit":80})
    req=urllib.request.Request(url,headers={"User-Agent":"HelloFresh-Supermarktscanner/1.0 (github.com/DASPHHS/Supermarktscanner)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=25) as resp:
        return json.load(resp)
def extract(data):
    result=[]
    seen=set()
    for label in ("top_by_percentage","top_by_amount"):
        for deal in data.get(label,[]) or []:
            product=deal.get("representative_product") or {}
            name=product.get("name") or ""
            if not name or name.casefold() in seen:continue
            seen.add(name.casefold())
            off=deal.get("savings_percentage")
            amount=deal.get("savings_amount")
            tag=("%g%% korting" % off if isinstance(off,(int,float)) and off>0 else
                 ("€ %.2f besparing" % amount if isinstance(amount,(int,float)) and amount>0 else "Aanbieding"))
            result.append({"name":name,"discount":tag,
                           "brand":deal.get("brand"),"variant_count":deal.get("variant_count")})
    return result[:80]
def main(out="market_deals.json"):
    result={"updated_at_utc":datetime.now(timezone.utc).isoformat(),"source":"PrijsProfeet API /deals/top", "limitations":["Only promotion examples; not complete supermarket assortment","No implied recipe pricing or 1+1 calculations"],"stores":{}}
    for name,code in STORES.items():
        try:
            data=fetch(code)
            result["stores"][name]={"updated_at":result["updated_at_utc"],"deals":extract(data)}
        except Exception as exc:
            print("PrijsProfeet fetch error for",name, type(exc).__name__,str(exc)[:250])
            result["stores"][name]={"updated_at":None,"deals":[],"error":type(exc).__name__+": "+str(exc)[:140]}
    print("Deal API counts:",{k:len(v["deals"]) for k,v in result["stores"].items()})
    # Never replace a previously saved complete feed with a wholly failed snapshot.
    if all(len(x["deals"])==0 for x in result["stores"].values()):
        raise RuntimeError("No promotions received; retain previous snapshot")
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Saved offer counts:",{k:len(v["deals"]) for k,v in result["stores"].items()})
if __name__=="__main__":main()
