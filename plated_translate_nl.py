"""Dutch Plated display layer and cautious supermarket ingredient normalization.

The input review queue and original PDF never change. Any uncertain US measures,
ingredient identities or OCR omissions remain explicitly unverified. No prices.
"""
import json,re,unicodedata
from fractions import Fraction
from pathlib import Path

TITLES={
 "Argentine Beef Empanadas":"Argentijnse empanada's met rundvlees",
 "Apple-Cherry Cobbler with Flaky Biscuit":"Appel-kersencrumble met luchtige biscuits",
 "Baba Ganoush with Roasted Root Vegetables and Za’atar Naan":"Baba ganoush met geroosterde wortelgroenten en za'atar-naan",
 "Balsamic-Marinated Grilled Chicken with Bleu Cheese and Marcona Almonds":"Gegrilde balsamicokip met blauwe kaas en Marcona-amandelen",
 "Balsamic-Marinated Steak":"Biefstuk gemarineerd in balsamico",
 "Barbecue Chicken":"Barbecuekip",
 "Barbecue Glazed Chicken Thighs":"Kippendijen met barbecuesaus",
 "Barbecue Turkey Meatloaf":"Kalkoengehaktbrood met barbecuesaus",
 "Bánh Mì Turkey Burgers":"Bánh mì-burgers met kalkoen",
 "Beef and Broccoli":"Rundvlees met broccoli",
 "Beef and Butternut Skillet":"Eenpansgerecht met rundvlees en flespompoen",
 "Beef and Cheddar Hand Pies":"Hartige pasteitjes met rundvlees en cheddar",
 "Beef and Cheese Empanadas":"Empanada's met rundvlees en kaas",
 "Beef and Roasted Carrot Ragu":"Ragù van rundvlees met geroosterde wortel",
 "Beef Biryani":"Biryani met rundvlees",
 "Beef Bolognese over Roasted Spaghetti Squash":"Bolognesesaus met geroosterde spaghettipompoen",
 "Beef Bolognese with roasted zucchini steaks":"Bolognese met geroosterde courgette",
 "Beef Bulgogi Buns with Kimchi Slaw and Cheesy Corn":"Broodjes bulgogi-rundvlees met kimchi-koolsalade en mais",
 "Beef Chili with Cheddar and Beet Chips":"Rundvleeschili met cheddar en bietenchips",
 "Beef Kibbeh with Tomato-Herb Salsa and Creamy Feta":"Kibbeh van rundvlees met tomaten-kruidensalsa en feta",
}
# Only unambiguous equivalences. Product size and culinary equivalents are separate.
ALIASES={
 "ground beef":("rundergehakt","meat"), "beef mince":("rundergehakt","meat"),
 "ground turkey":("kalkoengehakt","meat"),"ground pork":("varkensgehakt","meat"),
 "boneless skinless chicken breasts":("kipfilet","meat"),
 "boneless skinless chicken thighs":("kippendijfilet","meat"),
 "chicken breasts":("kipfilet","meat"),"chicken thighs":("kippendijen","meat"),
 "green beans":("sperziebonen","vegetable"),"sweet potatoes":("zoete aardappelen","vegetable"),
 "yellow onion":("gele ui","vegetable"),"red onion":("rode ui","vegetable"),
 "garlic":("knoflook","vegetable"),"garlic cloves":("knoflooktenen","vegetable"),
 "lemon":("citroen","fruit"),"lime":("limoen","fruit"),
 "broccoli":("broccoli","vegetable"),"butternut squash":("flespompoen","vegetable"),
 "carrots":("wortelen","vegetable"),"yellow beets":("gele bieten","vegetable"),
 "tomato paste":("tomatenpuree","sauce"),"crushed tomatoes":("tomatenblokjes","sauce"),
 "butter":("roomboter","dairy"),"heavy cream":("slagroom","dairy"),
 "balsamic vinegar":("balsamicoazijn","sauce"),"dijon mustard":("dijonmosterd","sauce"),
 "honey":("honing","sauce"),"crumbled bleu cheese":("verkruimelde blauwe kaas","dairy"),
 "pistachios":("pistachenoten","nuts"),"sugar":("suiker","pantry"),
 "baking powder":("bakpoeder","pantry"),"flour":("bloem","pantry"),
 "gala apples":("gala-appels","fruit"),"cherries":("kersen","fruit"),
 "dried mission figs":("gedroogde vijgen","fruit"),
 "jalapeno":("jalapeño","vegetable"),"jalapeño":("jalapeño","vegetable"),
 "roasted red peppers":("geroosterde rode paprika","vegetable"),
 "cheddar cheese":("cheddar","dairy"),"monterey jack":("monterey jack","dairy"),
 "worcestershire sauce":("worcestersaus","sauce"),
 "chipotle pepper in adobo":("chipotlepeper in adobosaus","sauce"),
 "aluminum tin":("aluminium bakvorm","nonfood"),
 "aluminum tins":("aluminium bakvormen","nonfood"),
 "parchment paper":("bakpapier","nonfood"),
 "herbes de provence":("Provençaalse kruiden","spice"),
 "spice mix":("kruidenmix","spice"),
}
TITLE_WORDS=[
 ("ground beef","rundergehakt"),("chicken thighs","kippendijen"),
 ("chicken","kip"),("turkey","kalkoen"),("beef","rundvlees"),
 ("pork","varkensvlees"),("shrimp","garnalen"),("salmon","zalm"),
 ("butternut","flespompoen"),("green beans","sperziebonen"),
 ("sweet potatoes","zoete aardappelen"),("carrots","wortelen"),
 ("mushrooms","champignons"),("with","met"),("and","en"),
 ("roasted","geroosterde"),("creamy","romige"),("spicy","pittige"),
 ("salad","salade"),("soup","soep"),("bowl","bowl"),
 ("garlic","knoflook"),("cheese","kaas"),("lemon","citroen"),
]
UNIT_NL={
 "ounce":"oz","ounces":"oz","oz":"oz","pound":"lb","pounds":"lb","lbs":"lb","lb":"lb",
 "cup":"cup","cups":"cup","tablespoon":"eetlepel","tablespoons":"eetlepel",
 "tbsp":"eetlepel","teaspoon":"theelepel","teaspoons":"theelepel","tsp":"theelepel",
 "clove":"teen","cloves":"tenen","packet":"zakje","packets":"zakjes",
 "can":"blik","cans":"blikken","piece":"stuk","pieces":"stuks",
}
def clean(s):
 return " ".join(unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower().split())
def remove_suffix(name):
 return re.sub(r"(\s+\([234]\)|_card|-?\d{4,})+$","",re.sub(r"\.pdf$","",str(name),flags=re.I)).strip()
def translated_title(title):
 base=remove_suffix(title)
 exact=next((nl for en,nl in TITLES.items() if clean(en)==clean(base)),None)
 if exact:return exact,"reviewed_dictionary"
 result=base
 count=0
 for en,nl in TITLE_WORDS:
  new,n=re.subn(r"(?<!\w)"+re.escape(en)+r"(?!\w)",nl,result,flags=re.I)
  if n:result=new;count+=n
 return (result,"partial_machine_glossary" if count else "original_english")
def translated_ingredient(name):
 original=str(name or "").strip()
 # Do not remove critical qualifiers silently; simply remove a known trailing "divided".
 base=re.sub(r",?\s*divided\s*$","",original,flags=re.I).strip()
 base=re.sub(r"^\s*container\s+","",base,flags=re.I)
 for en,(nl,kind) in sorted(ALIASES.items(),key=lambda kv:-len(kv[0])):
  if clean(base)==clean(en):return {"name_nl":nl,"canonical_nl":nl,"type":kind,"translation_status":"dictionary_exact"}
 return {"name_nl":original,"canonical_nl":None,"type":"unknown","translation_status":"original_english_unmatched"}
QTY=re.compile(r"^\s*(\d+(?:/\d+)?(?:\s+\d+/\d+)?)\s+([a-zA-Z]+)\s*$")
def quantity_nl(raw):
 raw=str(raw or "").strip()
 m=QTY.match(raw)
 if not m:return {"quantity_display_nl":raw,"quantity_metric":None,"unit_metric":None,"conversion_status":"unparsed"}
 amount,unit=m.groups()
 try:q=sum((Fraction(x) for x in amount.split()),Fraction(0))
 except (ValueError,ZeroDivisionError):return {"quantity_display_nl":raw,"quantity_metric":None,"unit_metric":None,"conversion_status":"unparsed"}
 unit=unit.lower()
 display=f"{float(q):g}".replace(".",",")+" "+UNIT_NL.get(unit,unit)
 if unit in ("oz","ounce","ounces","lb","lbs","pound","pounds"):
  grams=round(float(q)* (28.349523125 if unit in ("oz","ounce","ounces") else 453.59237))
  return {"quantity_display_nl":display+f" (≈ {grams} g)","quantity_metric":grams,"unit_metric":"g","conversion_status":"exact_mass_conversion_rounded"}
 if unit in ("stuks","stuk","pieces","piece"):
  return {"quantity_display_nl":display,"quantity_metric":float(q),"unit_metric":"stuk","conversion_status":"count_only"}
 # Cups/tablespoons of solids cannot be turned into grams safely.
 return {"quantity_display_nl":display,"quantity_metric":None,"unit_metric":None,"conversion_status":"needs_density_or_pack_size"}
def enrich(recipe):
 title,status=translated_title(recipe.get("title_extracted",""))
 ingredients=[]
 for r in recipe.get("ingredients_4p",[]):
  ingredients.append({"original_name":r.get("ingredient",""),
                      "original_quantity_4p":r.get("quantity_4p_source",""),
                      **translated_ingredient(r.get("ingredient","")),
                      **quantity_nl(r.get("quantity_4p_source",""))})
 return {"id":recipe.get("source_identity") or recipe.get("id"),
         "source_identity":recipe.get("source_identity"),
         "title_original":recipe.get("title_extracted",""),
         "title_nl":title,"title_translation_status":status,
         "ingredients_nl":ingredients,
         "servings_source":recipe.get("servings_original"),
         "servings_4p_unverified":recipe.get("servings",4),
         "ingredient_ocr_missing":len(ingredients)==0,
         "pricing_eligible":False,
         "review_status":"needs_manual_original_card_comparison"}
def run(inp="plated_release_review_queue.json",out="plated_nl_catalog.json"):
 d=json.loads(open(inp,encoding="utf8").read())
 enriched=[enrich(r) for r in d.get("recipes",[])]
 report={"source":"Plated review queue; Dutch glossary; NOT human validated",
         "records":len(enriched),"without_ingredients":sum(x["ingredient_ocr_missing"] for x in enriched),
         "ingredient_translations_exact":sum(i["translation_status"]=="dictionary_exact" for r in enriched for i in r["ingredients_nl"]),
         "ingredient_translations_unknown":sum(i["translation_status"]!="dictionary_exact" for r in enriched for i in r["ingredients_nl"]),
         "pricing_eligible":0}
 with open(out,"w",encoding="utf8") as fh:json.dump({"metadata":report,"recipes":enriched},fh,ensure_ascii=False,indent=2)
 print(report)
 return report
if __name__=="__main__":run()
