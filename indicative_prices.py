"""Reproducible indicative costs. No inferred price for an unknown ingredient.

Only recovered six-column source tables are eligible. Norm weights and curated
name equivalences are disclosed on each line. This never changes certified prices.
"""
from __future__ import annotations
import math,re
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from sync_prices import norm,number,amount

VERSION='2026-10-30.1'
VC='https://www.voedingscentrum.nl/nl/service/vraag-en-antwoord/gezonde-voeding-en-voedingsstoffen/hoeveel-voedingswaarden-zitten-erin/'
WORK='Werkaanname voor prijsraming; geen exact HelloFresh-verpakkingsgewicht'
# Canonical family: accepted names, grams per source piece (when relevant).
FAMILIES={
 'ui':(['ui','uien','gele uien','ui geel','uien geel'],100),
 'rode ui':(['rode ui','rode uien','uien rood'],100),
 'knoflook':(['knoflook','knoflookteen','knoflooktenen','knoflookteentjes'],2),
 'tomaat':(['tomaat','tomaten','trostomaten','tros tomaten'],100),
 'courgette':(['courgette','courgettes'],300),
 'komkommer':(['komkommer','komkommers'],400),
 'wortel':(['wortel','wortelen','winterpeen','winterpenen'],150),
 'paprika':(['paprika','paprikas','rode paprika','paprika rood'],150),
 'groene paprika':(['groene paprika','paprika groen'],150),
 'rode puntpaprika':(['rode puntpaprika','puntpaprika','puntpaprikas'],120),
 'aubergine':(['aubergine','aubergines'],300),
 'citroen':(['citroen','citroenen'],120),
 'limoen':(['limoen','limoenen'],70),
 'rode peper':(['rode peper','rode pepers','chilipeper','chili pepers'],15),
 'groene peper':(['groene peper','groene pepers'],15),
 'prei':(['prei'],200),'sjalot':(['sjalot','sjalotten'],50),
 'appel':(['appel','appels','jonagold appels','elstar appels'],150),
 'peer':(['peer','peren','conference peren'],170),
 'avocado':(['avocado','avocados'],150),'witlof':(['witlof'],100),
 'venkel':(['venkel'],250),'bosui':(['bosui','bosuitjes','lente ui','bosuien'],100),
 'bospeen':(['bospeen'],500),
 'radijs':(['radijs','radijzen'],125),
 'kipfilet':(['kipfilet','kipfilets'],125),'kippendijfilet':(['kippendijfilet','kippendijfilets'],125),
 'zalmfilet':(['zalmfilet','zalmfilets'],125),'kabeljauwfilet':(['kabeljauwfilet'],100),
 'heekfilet':(['heekfilet'],100),'doradefilet':(['doradefilet'],100),
 'varkenshaas':(['varkenshaas'],125),'ei':(['ei','eieren'],None),
 'aardappelen':(['aardappelen','aardappel'],None),
 'krieltjes':(['krieltjes','kriel'],None),'zoete aardappel':(['zoete aardappel','zoete aardappelen'],None),
 'spinazie':(['spinazie'],None),'champignons':(['champignons','champignon'],None),
 'kastanjechampignons':(['kastanjechampignons','kastanje champignons'],None),
 'gemengde paddenstoelen':(['paddenstoelenmix','paddestoelenmix','gemengde paddenstoelen','gemengde paddestoelen'],None),
 'warmgerookte zalmsnippers':(['warmgerookte zalmsnippers','warmgerookte zalm flakes','zalm flakes warmgerookt','warmgerookte zalmstukjes','warmgerookte zalm'],None),
 'pistachenoten':(['gepelde pistachenoten','pistachenoten gepeld','pistachepitten','pistache noten gepeld','pistache fijngehakt','gehakte pistache'],None),
 'dragon':(['dragon'],None),
 'gele wortel':(['gele wortel','wortel geel','gele wortelen'],150),
 'broccoli':(['broccoli'],None),'sperziebonen':(['sperziebonen'],None),
 'snijbonen':(['snijbonen'],None),'witte asperges':(['witte asperges'],None),
 'roomboter':(['roomboter'],None),'olijfolie':(['olijfolie'],None),
 'extra vierge olijfolie':(['extra vierge olijfolie','olijfolie extra vierge','olijfolie vierge','vierge olijfolie'],None),
 'zonnebloemolie':(['zonnebloemolie'],None),
 'suiker':(['suiker','kristalsuiker','witte suiker'],None),
 'bruine basterdsuiker':(['bruine basterdsuiker','basterdsuiker bruin','donkere basterdsuiker'],None),
 'bloem':(['bloem','tarwebloem','patentbloem'],None),
 'honing':(['honing','bloemenhoning'],None),'mosterd':(['mosterd'],None),
 'mayonaise':(['mayonaise','mayo'],None),
 'wittewijnazijn':(['wittewijnazijn','witte wijnazijn','witte wijn azijn','wijnazijn wit','wijnazijn witte'],None),
 'rodewijnazijn':(['rodewijnazijn','rode wijnazijn','rode wijn azijn','wijnazijn rood'],None),
 'witte balsamicoazijn':(['witte balsamicoazijn','balsamico azijn wit','balsamico bianco','balsamicoazijn wit'],None),
 'zwarte balsamicoazijn':(['balsamicoazijn','balsamico azijn','balsamico azijn modena'],None),
 'balsamicocreme':(['balsamicocreme','balsamico creme','cremissimo balsamico azijn uit modena','cremissimo van balsamico azijn uit modena','crema di balsamico'],None),
 'sojasaus':(['sojasaus','soja saus'],None),'ketjap manis':(['ketjap manis'],None),
 'sesamolie':(['sesamolie'],None),'vissaus':(['vissaus'],None),
 'kookroom':(['kookroom'],None),'slagroom':(['slagroom'],None),
 'melk':(['melk','volle melk','halfvolle melk'],None),
 'kokosmelk':(['kokosmelk'],None),'passata':(['passata','tomaten passata gezeefd'],None),
 'tomatenblokjes':(['tomatenblokjes','tomaten blokjes'],None),
 'tomatenpuree':(['tomatenpuree','tomaten puree'],None),
 'rode kidneybonen':(['rode kidneybonen','kidneybonen','kidney bonen'],None),
 'kikkererwten':(['kikkererwten'],None),'zwarte bonen':(['zwarte bonen'],None),
 'linzen':(['linzen'],None),'rode splitlinzen':(['rode splitlinzen','rode linzen'],None),
 'rijst':(['witte rijst','witte langgraanrijst','langgraanrijst','rijst langgraan'],None),
 'jasmijnrijst':(['jasmijnrijst','pandanrijst'],None),
 'zilvervliesrijst':(['zilvervliesrijst','bruine rijst','volkoren rijst','bruine snelkookrijst'],None),
 'basmatirijst':(['basmatirijst','basmati rijst'],None),
 'risottorijst':(['risottorijst','risotto rijst'],None),
 'orzo':(['orzo'],None),'parelcouscous':(['parelcouscous'],None),
 'bulgur':(['bulgur'],None),'spaghetti':(['spaghetti'],None),
 'volkoren spaghetti':(['volkoren spaghetti','spaghetti volkoren'],None),
 'penne':(['penne'],None),'volkoren penne':(['volkoren penne','penne volkoren'],None),
 'linguine':(['linguine'],None),'casarecce':(['casarecce'],None),
 'rigatoni':(['rigatoni'],None),'farfalle':(['farfalle'],None),
 'verse lasagnebladen':(['verse lasagnebladen','lasagnebladen'],None),
 'witte kaas':(['witte kaas','witte kaasblokjes'],None),'feta':(['feta'],None),
 'mozzarella':(['mozzarella'],125),'burrata':(['burrata'],125),
 'kruidenroomkaas':(['kruidenroomkaas','roomkaas kruiden','roomkaas knoflook kruiden','roomkaas met kruiden'],None),
 'geraspte goudse kaas':(['goudse kaas geraspt','geraspte goudse kaas','geraspte kaas','geraspte kaas mild'],None),
 'geraspte belegen kaas':(['geraspte belegen kaas','geraspte kaas belegen','belegen kaas geraspt'],None),
 'geraspte oude goudse kaas':(['geraspte oude kaas','oude kaas geraspt'],None),
 'geraspte cheddar':(['geraspte cheddar','cheddar geraspt'],None),
 'pecorino':(['pecorino','pecorino romano','geraspte pecorino'],None),
 'grana padano':(['grana padano','grana padano geraspt','grana padano flakes'],None),
 'zure room':(['zure room','sour cream'],None),'creme fraiche':(['creme fraiche'],None),
 'gruyere':(['gruyere','geraspte gruyere'],None),'volle yoghurt':(['volle yoghurt','yoghurt vol'],None),
 'peterselie':(['peterselie','bladpeterselie','krulpeterselie'],None),
 'koriander':(['koriander'],None),'basilicum':(['basilicum'],None),
 'dille':(['dille'],None),'bieslook':(['bieslook'],None),'munt':(['munt'],None),
 'rozemarijn':(['rozemarijn'],1),'tijm':(['tijm'],None),
 'oregano':(['oregano'],None),'italiaanse kruiden':(['italiaanse kruiden'],None),
 'gerookt paprikapoeder':(['gerookt paprikapoeder','paprikapoeder gerookt'],None),
 'kerriepoeder':(['kerriepoeder','kerrie'],None),
 'gemalen komijnzaad':(['gemalen komijnzaad','komijn gemalen','komijnzaad gemalen'],None),
 'garam masala':(['garam masala'],None),'ras el hanout':(['ras el hanout'],None),
 'mexicaanse kruiden':(['mexicaanse kruiden','mexicaanse kruidenmix'],None),
 'sesamzaad':(['sesamzaad'],None),'zwarte sesamzaad':(['zwart sesamzaad'],None),
 'walnoten':(['walnoten','walnoten ongezouten','walnootstukjes'],None),
 'cashewnoten':(['cashewnoten','cashew noten','cashewstukjes'],None),
 'amandelschaafsel':(['amandelschaafsel'],None),'pompoenpitten':(['pompoenpitten'],None),
 'spekreepjes':(['spekreepjes','gerookte spekreepjes'],None),
 'ontbijtspek':(['ontbijtspek'],10),'achterham':(['achterham'],15),
 'rundergehakt':(['rundergehakt'],None),'varkensgehakt':(['varkensgehakt'],None),
 'groentebouillon':(['bouillon groente','groente bouillon','groentebouillon','groentebouillonblokjes','groentebouillonblok','groente bouillonblokjes'],10),
 'kippenbouillon':(['bouillon kip','kippenbouillon','kippen bouillon','kippenbouillonblokjes','kippenbouillonblok'],10),
 'runderbouillon':(['bouillon rund','runderbouillon','rundvlees bouillon','runderbouillonblokjes'],10),
 'zout':(['zout','keukenzout','tafelzout','fijn zout','jodium zout'],None),
 'zwarte peper':(['zwarte peper','peper zwart'],None),
}
ALIASES={norm(a):key for key,(names,_) in FAMILIES.items() for a in names}
ALIASES.update({'witte langgraanrijst':'rijst','bruine snelkookrijst':'zilvervliesrijst',
 'verse bladpeterselie':'peterselie','verse krulpeterselie':'peterselie',
 'geraspte pecorino dop':'pecorino','grana padanovlokken':'grana padano','grana padanovlokken dop':'grana padano',
 'geraspte gruyere':'gruyere','walnootstukjes':'walnoten','cashewstukjes':'cashewnoten',
 'biologische zure room':'zure room','biologische creme fraiche':'creme fraiche',
 'biologische volle yoghurt':'volle yoghurt','varkensboerengehakt':'varkensgehakt'})
QUALIFIERS=set('ah jumbo s lidl biologisch biologische bio vers verse hollandse nederlandse extra vierge groot middel fijn fijne grof grove ongezouten gezouten mild milde naturel room romige gezeefd gesneden gesnipperde gesnipperd stuk stuks st g gr gram kg ml l liter milliliter vet van goede aarde al bronzo tradizionali dop vrij vrije uitloop scharrel scharreleieren scharrelmais mais grasboter botergoud voordeelpak fles blik pak verpakking wit witten vol volle halfvolle rood rode geel gele groen groene punt glutenvrij gedroogd gemalen gedroogde vriesdroog diepvries vriesvers iets kruim kruimig vastkokend vastkokende zacht zacht en romig belgische franse gemengd 48'.split())
BRANDS=set('verstegen silvo euroma essential grand italia fairtrade original fair trade fto knorr maggi zonnatura jozo van gilse campina botergoud bertolli carbonell lassie la molisana rummo lenta lavorazione hak bonduelle kikkoman olitalia crest dulano milbona freshona golden sun combino vita dor alesto kania chef select sol mar na elstar jonagold conference calve heinz hellmanns hellmann echte de'.split())
SPOONS={
 'roomboter':(15,'g','Voedingscentrum: eetlepel roomboter 15 g',VC+'roomboter.aspx'),
 'suiker':(20,'g',WORK,None),'bruine basterdsuiker':(15,'g',WORK,None),
 'bloem':(10,'g',WORK,None),'honing':(20,'g',WORK,None),
 'mosterd':(20,'g',WORK,None),'mayonaise':(17,'g',WORK,None),
 'gerookt paprikapoeder':(7,'g',WORK,None),'kerriepoeder':(6,'g',WORK,None),
 'gemalen komijnzaad':(6,'g',WORK,None),
 'olijfolie':(15,'ml','Rekenmaat: eetlepel 15 ml; theelepel 5 ml',None),
 'zonnebloemolie':(15,'ml','Rekenmaat: eetlepel 15 ml; theelepel 5 ml',None),
 'extra vierge olijfolie':(15,'ml','Rekenmaat: eetlepel 15 ml; theelepel 5 ml',None),
 'wittewijnazijn':(15,'ml',WORK,None),'rodewijnazijn':(15,'ml',WORK,None),
 'witte balsamicoazijn':(15,'ml',WORK,None),'zwarte balsamicoazijn':(15,'ml',WORK,None),
 'sojasaus':(15,'ml',WORK,None),'ketjap manis':(15,'ml',WORK,None),
}
PACKS={'tomatenblokjes':400,'tomatenpuree':70,'rode kidneybonen':380,'kikkererwten':380,'linzen':380,'zwarte bonen':380}
FAMILIES['witte kaas'][0].extend(['witte kaas grote plak','witte kaas plak'])
FAMILIES['geraspte belegen kaas'][0].extend(['goudse belegen geraspte kaas','geraspte goudse belegen kaas'])
FAMILIES['geraspte goudse kaas'][0].extend(['goudse jong geraspte kaas','geraspte kaas jong','gouda geraspte kaas'])
FAMILIES['spekreepjes'][0].append('spekreepjes gerookt')
FAMILIES['rode puntpaprika'][0].extend(['zoete puntpaprika','zoete rode puntpaprika','sweet palermo rode puntpaprika'])
FAMILIES['rijst'][0].extend(['rijst','langkorrel rijst','long grain rijst','witte langkorrelrijst'])
FAMILIES['krieltjes'][0].append('mini krieltjes')
FAMILIES['krieltjes'][0].append('minikrieltjes')
FAMILIES['gemengde paddenstoelen'][0].extend(['paddenstoelen mix','roerbak paddenstoelenmix'])
FAMILIES['geraspte goudse kaas'][0].append('goudse geraspte kaas')
FAMILIES['wittewijnazijn'][0].append('wijnazijn wit')
FAMILIES['wittewijnazijn'][0].extend(['wijn azijn wit','witte wijn azijn'])
FAMILIES['rodewijnazijn'][0].append('wijn azijn rood')
FAMILIES['mexicaanse kruiden'][0].extend(['taco kruidenmix','taco seasoning mix'])
FAMILIES['passata'][0].extend(['tomaten passata','tomaten gezeefd passata','passata gezeefde tomaten','passata gezeefde fluweelzachte tomaten'])
QUALIFIERS.update('grote plak gerookt gerookte gerijpte zoete sweet palermo voordeelverpakking xxl bl mini jong belegen'.split())
QUALIFIERS.update('eierpasta eier fijngehakt fijngehakte flakes pitten gepeld gepelde roerbak'.split())
BRANDS.update('mutti arla apetina santa maria jonnie boer by world spice blend mill mortar'.split())
FAMILIES['kippenbouillon'][0].extend(['kippenbouillonblok','kippen bouillonblokjes'])
FAMILIES['runderbouillon'][0].append('runderbouillonblok')
# Canonical labels remain separate from product-name variants.
ALIASES['verse lasagnebladen']='verse lasagnebladen'
ALIASES.update({'gemengde gesneden paddenstoelen':'gemengde paddenstoelen',
 'zwarte balsamicoazijn':'zwarte balsamicoazijn','witte balsamicoazijn':'witte balsamicoazijn',
 'extra vierge olijfolie':'extra vierge olijfolie'})
ALIASES.update({'warmgerookte zalmsnippers':'warmgerookte zalmsnippers','pistachenoten':'pistachenoten',
 'gele wortel':'gele wortel','verse dragon':'dragon','dragon':'dragon'})
SPICE_PROXIES={'siciliaanse kruidenmix':'italiaanse kruiden','peruaanse kruidenmix':'mexicaanse kruiden',
 'midden oosterse kruidenmix':'ras el hanout','afrikaanse kruidenmix':'ras el hanout','griekse kruidenmix':'italiaanse kruiden'}

# Explicit food families; aliases never permit arbitrary prepared products.
FAMILIES.update({
 'gember':(['gember'],None), 'gemberpuree':(['gemberpuree','gember puree'],None),
 'garnalen':(['garnalen rauw gepeld','rauwe gepelde garnalen','roerbakgarnalen','garnalen'],None),
 'veldsla':(['veldsla'],None),'rucola':(['rucola'],None),
 'rucola en veldsla':(['slamelange rucola veldsla','rucola veldsla'],None),
 'cherrytomaten':(['cherrytomaten','cherry tomaten','sweet cherry trostomaten'],None),
 'mini romatomaten':(['romaatjes','mini roma tomaten','mini romatomaten','snoeptomaatjes roma'],None),
 'mais':(['maiskorrels','mais korrels','mais'],None),
 'panko':(['panko','panko paneermeel','paneermeel panko'],None),
 'kappertjes':(['kappertjes'],None), 'pangasiusfilet':(['pangasiusfilet'],None),
 'ravigotesaus':(['ravigotesaus','ravigotte saus','ravigote saus'],None),
 'blauwe kaas':(['blauwe kaas','blauwekaas','danablu','danish blue'],None),
 'half om half gehakt':(['half om half gehakt','gemengd gehakt'],None),
 'aardappelblokjes':(['aardappelblokjes','aardappelen blokjes'],None),
 'flammkuchen':(['flammkuchen bodem','flammkuchenbodem','flammkuchen bodems'],120),
 'zachte geitenkaas':(['geitenkaas schijfjes naturel','zachte geitenkaas naturel','verse geitenkaas'],None),
 'lente ui':(['lente ui','lente uitjes','lente uien','salade ui','salade uien','salade uitjes'],100),
})
FAMILIES['bosui'][0].extend(FAMILIES.pop('lente ui')[0])
FAMILIES['geraspte cheddar'][0].append('cheddar geraspte kaas')
FAMILIES['geraspte oude goudse kaas'][0].extend(['geraspte oude goudse kaas','goudse oude geraspte kaas'])
FAMILIES['jasmijnrijst'][0].extend(['pandan rijst','thaise pandanrijst'])
ALIASES.update({norm(a):f for f,(names,_) in FAMILIES.items() for a in names})
ALIASES.update({'mais in blik':'mais','rode cherrytomaten':'cherrytomaten',
 'blauwekaas blokjes':'blauwe kaas','verse geitenkaas':'zachte geitenkaas',
 'panko paneermeel':'panko','mini romatomaten':'mini romatomaten',
 'zoutarme paddenstoelen of groentebouillon':'groentebouillon',
 'geraspte oude goudse kaas':'geraspte oude goudse kaas'})
# Small or seasoned components use explicit, visible price proxies, never silent swaps.
FOOD_PROXIES={
 'rundergehakt met italiaanse kruiden':'rundergehakt',
 'gemengd gekruid gehakt':'half om half gehakt',
 'kippendijreepjes met kebabkruiden':'kippendijfilet',
 'gemberpuree':'gember',
}
SPOONS['gember']=(6,'g',WORK,None)
QUALIFIERS.update('rauw rauwe gepeld gepelde geraspte slamelange grootverpakking kleinverpakking bodem bodems schijfjes'.split())
BRANDS.update(['terra'])

FAMILIES.update({
 'little gem':(['little gem','mini romaine sla','romaine mini'],100),
 'botersla':(['botersla','kropsla'],150),
 'mesclun':(['mesclun','mesclun slamelange'],None),
 'rodekool':(['rodekool','rode kool'],None),
 'wittekool':(['wittekool','witte kool'],None),
 'gehaktballetjes':(['gehaktballetjes naturel','gehaktballetjes rund varken','gemengde gehaktballetjes'],25),
})
ALIASES.update({norm(a):f for f,(names,_) in FAMILIES.items() for a in names})
ALIASES.update({'rucola en veldsla':'rucola en veldsla','geitenkaas':'zachte geitenkaas',
 'botersla':'botersla','little gem':'little gem','lollo biondo':'botersla',
 'gehaktballetjes van varken en rund':'gehaktballetjes'})
FOOD_PROXIES.update({'witte balsamicoazijn':'wittewijnazijn'})

def prepare_catalog(raw):
 """Extend the strict catalog only with explicit name sizes or disclosed piece assumptions."""
 from sync_prices import products
 catalog=products(raw)
 for shop in raw:
  store={'ah':'AH','jumbo':'Jumbo','lidl':'Lidl'}.get(str(shop.get('n','')).lower())
  if not store:continue
  known={p.get('link') for p in catalog[store] if p.get('link')}
  for row in shop.get('d',[]):
   name=row.get('n','');price=row.get('p')
   if not isinstance(name,str) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0 or price>1000:continue
   link=str(shop.get('u',''))+str(row.get('l','')) if row.get('l') else None
   if link and link in known:continue
   # No inferred count for eggs or cans: count must be literally present.
   size,u=amount(str(row.get('s') or ''));assumed=False
   if size is not None:continue # already retained by the strict source parser
   if size is None:
    suffix=re.search(r'(?<![x\d])\b(\d+(?:[.,]\d+)?\s*(?:kg|g|gram|ml|l|liter|stuks|stuk))\s*$',name,re.I)
    if suffix and not re.search(r'\d+\s*[x×]',name,re.I):size,u=amount(suffix.group(1))
   if size is None and not str(row.get('s') or '').strip():
    probe={'name':name,'unit':'stuk','quantity':1}
    families=[f for f,(_,v) in FAMILIES.items() if v and f in ('courgette','komkommer','aubergine','paprika','rode puntpaprika','citroen','limoen','prei','avocado','venkel','bosui','bospeen') and product_matches(f,probe)]
    if families and price<=4.0:size,u=1.,'stuk';assumed=True
   package_note=None
   if size is None and not str(row.get('s') or '').strip():
    probe={'name':name,'unit':'ml','quantity':500}
    if price<=4 and any(product_matches(f,probe) for f in ('wittewijnazijn','rodewijnazijn','witte balsamicoazijn','zwarte balsamicoazijn')):
     size,u=500.,'ml';assumed=True;package_note='Bron zonder inhoud: fles 500 ml aangenomen voor de prijsraming'
   if size is None and not str(row.get('s') or '').strip() and price<=2 and any(product_matches(f,{'name':name,'unit':'g','quantity':120}) for f in ('kippenbouillon','runderbouillon','groentebouillon')):
    size,u=120.,'g';assumed=True;package_note='Bron zonder inhoud: doos bouillonblokjes 120 g aangenomen voor prijsraming; controleer verpakking'
   if not size or not u:continue
   catalog[store].append({'name':name,'n':norm(name),'price':float(price),'quantity':size,'unit':u,
    'amount':str(row.get('s') or (str(size)+' '+u))+(' (eenheid per stuk aangenomen)' if assumed else ' (inhoud uit productnaam)' if not row.get('s') else ''),
    'link':link,'assumed_package_unit':assumed,'package_assumption_note':package_note})
 return catalog

def add_market_products(catalog,market,today):
 for store,group in market.get('stores',{}).items():
  if store not in ('AH','Jumbo','Lidl'):continue
  # Reset known action SKUs to their original package price, so effective
  # multi-buy prices in a source cannot receive the same discount twice.
  def sku(url):
   from urllib.parse import urlsplit
   text=str(url or '').rstrip('/').casefold();parsed=urlsplit(text)
   matches=re.findall(r'\b(wi\d+|\d{5,}[a-z]{2})\b',parsed.path)
   return matches[-1] if matches else text.split('?',1)[0]
  for d in group.get('deals',[]):
   if not active_action(d,today,True):continue
   try:
    original=float(d['original_price']);size,u=amount(d.get('quantity',''))
    if not math.isfinite(original) or original<=0 or not size:continue
   except (KeyError,ValueError,TypeError):continue
   key=sku(d.get('product_url'))
   if not key:continue
   for p in catalog.get(store,[]):
    if sku(p.get('link'))==key:
     p.update(price=original,quantity=size,unit=u,amount=d['quantity'],price_source='Checkjebon; oorspronkelijke prijs en inhoud uit PrijsProfeet actiebron')
  for p in group.get('products',[]):
   try:
    age=(today-date.fromisoformat(str(p['extracted_at'])[:10])).days
    size,u=amount(p['quantity']);price=float(p['price'])
    if not 0<=age<=3 or not size or not math.isfinite(price) or price<=0:continue
   except (KeyError,ValueError,TypeError):continue
   catalog.setdefault(store,[]).append({'name':p['name'],'n':norm(p['name']),'quantity':size,'unit':u,
    'amount':p['quantity'],'price':price,'link':p.get('product_url'),'price_source':'PrijsProfeet',
    'price_extracted_at':p['extracted_at']})
 catalog.pop('_indicative_families',None)
 return catalog

def money(x):return float(Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))

def parts(label):
 m=re.search(r'\s*\((g|ml|el|tl|[^()]+\([^()]+\)|naar smaak|scheutje)\)\s*$',label,re.I)
 if not m:return None,None
 name=norm(label[:m.start()].replace('*','').replace('[Plantaardige]',''))
 name=re.sub(r'\b(verse|vers|biologische)\b','',name).strip()
 name=re.sub(r'\s+',' ',name).replace('bouillon blokje','bouillonblokje').replace('champignons','champignons')
 return name,m.group(1).lower()

def canonical(name):
 return ALIASES.get(name) or ALIASES.get(re.sub(r'^gedroogde ','',name)) or ALIASES.get(name.replace('zoutarme ','').replace('zoutarm ','').replace('zoutarme ','').replace('bouillonblokje','bouillon'))

def requirements(ingredient):
 label=ingredient['ingredient'];name,unit=parts(label)
 q=number(str(ingredient.get('quantity_2p_source','')))
 if name=='rodekool wittekool en wortel' and unit=='g' and q is not None:
  return [dict(family=f,quantity=q/3,unit='g',norm=True,note='Gemengde groenten: elk een derde van het brongewicht; kostenbenadering, mengverhouding onbekend',source=None,proxy=True,fixed_quantity=True) for f in ('rodekool','wittekool','wortel')]
 if name in ('water','water voor saus','kokend water'):
  return [dict(family='water',quantity=0,unit='ml',norm=False,note='Leidingwater; water- en energiekosten niet meegerekend',source=None)]
 if name in ('peper zout','peper en zout') and unit=='naar smaak':
  return [dict(family=f,quantity=v,unit='g',norm=True,note='Kostenreserve voor twee porties: 1 g zout en 0,4 g peper; geen doseringsadvies',source=None) for f,v in [('zout',1),('zwarte peper',.4)]]
 proxy=SPICE_PROXIES.get(name or '') or FOOD_PROXIES.get(name or '')
 family=proxy or canonical(name or '')
 if not family or family not in FAMILIES:return None
 note=None;source=None;assumed=False
 if q is None:
  if unit in ('scheutje','naar smaak') and family=='melk':q=30;unit='ml';note='Scheutje melk: 30 ml voor twee porties';assumed=True
  elif unit=='naar smaak' and family in ('mayonaise','olijfolie','extra vierge olijfolie'):
   q=15;unit='g' if family=='mayonaise' else 'ml';note='Naar smaak: 15 '+unit+' voor twee porties';assumed=True
  else:return None
 if unit in ('g','ml'):value=q;u=unit
 elif unit in ('el','tl') and family in SPOONS:
  v,u,note,source=SPOONS[family];value=q*v/(3 if unit=='tl' else 1);assumed=True
 elif unit in ('stuk(s)','bol(len)','bosje(s)','takje(s)','plakje(s)','krop(pen)'):
  if family=='ei':value=q;u='stuk'
  elif FAMILIES[family][1] is not None:
   v=FAMILIES[family][1];value=q*v;u='g';assumed=True;note=f'1 {unit} {family} ≈ {v} g. '+WORK
   if family=='knoflook':note='1 teen knoflook ≈ 2 g (Voedingscentrum)';source=VC+'knoflook.aspx'
   if family=='rode ui':source=VC+'rode-ui.aspx'
  else:return None
 elif unit in ('pak(ken)','blik(ken)','kuipje(s)') and family in PACKS:
  value=q*PACKS[family];u='g';assumed=True;note=f'1 {unit} ≈ {PACKS[family]} g product inclusief vocht; '+WORK
 elif unit=='zakje(s)' and family in ('italiaanse kruiden','oregano','tijm','kerriepoeder','garam masala','ras el hanout','mexicaanse kruiden','gemalen komijnzaad','sesamzaad'):
  v=10 if family=='sesamzaad' else 3;value=q*v;u='g';assumed=True;note=f'1 zakje ≈ {v} g; '+WORK
 else:return None
 if proxy:
  note=(note+'; ' if note else '')+f'Prijsproxy: {family} voor {name}; samenstelling kan afwijken'
  assumed=True
 if name and 'zoutarm' in name and family in ('groentebouillon','kippenbouillon','runderbouillon','sojasaus','ketjap manis'):
  note=(note+'; ' if note else '')+'Prijsbasis reguliere variant; zoutarme variant kan in prijs en samenstelling afwijken. Volg de oorspronkelijke receptkeuze.'
  assumed=True;proxy=True
 if family in ('groentebouillon','kippenbouillon','runderbouillon') and u=='ml':
  value=value/500*10;u='g';assumed=True;note='Bereide bouillon: 10 g droog product per 500 ml; norm voor kostenraming, volg bereidingsadvies verpakking'
 # Optional plant alternatives are costed using dairy/mayonnaise, explicitly.
 if '[Plantaardige]' in label:
  note=(note+'; ' if note else '')+'Prijs van '+family+'; plantaardig alternatief kan duurder zijn';assumed=True
 return [dict(family=family,quantity=value,unit=u,norm=assumed,note=note,source=source,
              source_name=name,source_unit=unit,proxy=bool(proxy))]

def product_matches(family,product):
 text=product.get('n') or norm(product['name']);words=text.split()
 aliases=FAMILIES[family][0]
 # All substantive product words must be explained by this family or safe qualifiers.
 for alias in aliases:
  needed=norm(alias).split()
  if not all(w in words for w in needed):continue
  if all(w in needed or w in QUALIFIERS or w in BRANDS or re.fullmatch(r'\d+(?:g|gr|gram|kg|ml|l|st|stuks|x)?',w) for w in words):
   # Do not use frozen/canned/seasoned versions for raw fresh vegetables.
   if family in ('ui','rode ui','knoflook','tomaat','courgette','komkommer','wortel','paprika','aubergine','champignons','kastanjechampignons','sperziebonen'):
    if any(w in words for w in ('blik','gedroogd','gedroogde','diepvries','vriesvers','gemalen','poeder','gerookt','gerookte','gebakken','geroosterd')):continue
   if family in ('kipfilet','kippendijfilet','zalmfilet','kabeljauwfilet','heekfilet','doradefilet','varkenshaas'):
    if any(w in words for w in ('gerookt','gerookte','gegaard','gebraden','gebakken','geroosterd','marinade','gemarineerd','plak','plakjes','vleeswaren')):continue
   if family=='garnalen' and any(w in words for w in ('cocktail','gekookt','gekookte','hollandse','noorse')):continue
   if family=='kokosmelk' and 'light' in words:continue
   if family=='rode puntpaprika' and any(w in words for w in ('groen','groene','geel','gele')):continue
   if family=='witte kaas' and any(w in words for w in ('blokjes','kaasblokjes','brine','olie','glas')):continue
   if family=='verse lasagnebladen' and product['quantity']>300:continue
   if family in ('tijm','oregano','italiaanse kruiden','garam masala','ras el hanout','mexicaanse kruiden','kerriepoeder'):
    if product['unit']!='g' or product['quantity']>100:continue
   return True
 return False

def product_size(product,family,desired_unit):
 if product['unit']==desired_unit:return product['quantity'],False
 if product['unit']=='stuk' and desired_unit=='g' and FAMILIES[family][1]:
  return product['quantity']*FAMILIES[family][1],True
 if family in ('kookroom','melk','kokosmelk','mayonaise','mosterd','zure room','creme fraiche','volle yoghurt','passata') and {product['unit'],desired_unit}=={'g','ml'}:
  return product['quantity'],True # disclosed 1 g/ml approximation, not a generic rule
 if family=='balsamicocreme' and {product['unit'],desired_unit}=={'g','ml'}:
  return product['quantity']/1.3 if desired_unit=='ml' else product['quantity']*1.3,True
 return None,False

def active_action(d,today,cards):
 if d.get('personal_offer'):return False
 try:
  if not (date.fromisoformat(d['valid_from'])<=today<=date.fromisoformat(d['valid_until'])):return False
 except (KeyError,ValueError,TypeError):return False
 if d.get('valid_until_estimated'):return False
 if (d.get('card_required') or d.get('loyalty_program') or d.get('loyalty_price') is not None) and not cards:return False
 return True

def purchase(needed,size,price,action=None,today=None,cards=False):
 """Whole-pack cash and allocated consumption value, including optional advantage packs."""
 needed=round(float(needed),8);size=round(float(size),8)
 if not all(math.isfinite(v) for v in (needed,size,float(price))) or needed<0 or size<=0 or float(price)<=0:
  raise ValueError('Ongeldige rekenhoeveelheid, verpakkingsinhoud of prijs')
 n=int((Decimal(str(needed))/Decimal(str(size))).to_integral_value(rounding=ROUND_CEILING))
 price=Decimal(str(price));cash=n*price;used_action=None
 if n>0 and action and active_action(action,today,cards):
  original=action.get('original_price');promoprice=action.get('price')
  try:
   if original is None or not math.isfinite(float(original)) or float(original)<=0:raise ValueError()
   original=Decimal(str(original))
   k=action.get('multi_buy_quantity');bundle=action.get('multi_buy_price')
   if k is not None and bundle is not None:
    if isinstance(k,bool) or int(k)!=float(k) or int(k)<2:raise ValueError()
    k=int(k);bundle=Decimal(str(bundle))
    if not bundle.is_finite() or bundle<=0 or bundle>=k*original:raise ValueError()
    groups,rest=divmod(n,k);candidate=groups*bundle+rest*original;new_n=n
    if rest and bundle<=rest*original:candidate=groups*bundle+bundle;new_n=n+k-rest
   elif action.get('promotion_type') in ('percentage','fixed_price','discount','price_cut'):
    promoprice=Decimal(str(promoprice))
    if not promoprice.is_finite() or promoprice<=0 or promoprice>=original:raise ValueError()
    candidate=n*promoprice;new_n=n
   else:raise ValueError()
   limit=action.get('max_per_customer')
   if limit is not None and new_n>int(limit):raise ValueError()
   if candidate<=cash:
    cash=candidate;n=new_n;used_action=action
  except (ValueError,TypeError,ArithmeticError):pass
 used=Decimal(0) if n==0 else cash*Decimal(str(needed))/(n*Decimal(str(size)))
 return dict(packages=n,cash=float(cash),used=float(used),leftover=n*size-needed,action=used_action)

def estimate_recipe(recipe,catalog,store,deals=(),today=None,cards=False,scale=1):
 result={'eligible':False,'servings':2,'lines':[],'missing':[],'assumptions':[],'policy_version':VERSION,'cards_included':cards}
 if not recipe.get('table_repair') or not recipe.get('ingredients_2p'):
  result['missing']=[{'ingredient':'Brongegevens','reason':'Tweepersoonskolom doorstaat tabelcontrole nog niet'}];return result
 reqs=[];ingredient_labels=[]
 for ing in recipe['ingredients_2p']:
  converted=requirements(ing);label=ing['ingredient'];ingredient_labels.append(label)
  if not converted:
   result['missing'].append({'ingredient':label,'reason':'Geen onderbouwde norm of passende productgroep'});continue
  for req in converted:
   req=dict(req,ingredient=label)
   if req['norm']:
    if not req.get('fixed_quantity'):req['quantity']*=scale
    result['assumptions'].append({'ingredient':label,'note':req['note'] or WORK,'quantity':req['quantity'],'unit':req['unit'],'source':req['source']})
   reqs.append(req)
 # Aggregate the same ingredient/product family BEFORE applying package and promotion rules.
 groups=defaultdict(list)
 for r in reqs:groups[(r['family'],r['unit'])].append(r)
 action_products=[]
 for d in deals:
  if not active_action(d,today,cards):continue
  size,u=amount(d.get('quantity',''))
  if not size or not u:continue
  p={'name':d['name'],'n':norm(d['name']),'quantity':size,'unit':u,'amount':d['quantity'],
     'price':d.get('original_price'),'link':d.get('product_url'),'action':d,'price_source':'PrijsProfeet actiegegevens'}
  if isinstance(p['price'],(int,float)) and math.isfinite(p['price']) and p['price']>0:action_products.append(p)
 for (family,u),rows in groups.items():
  needed=sum(x['quantity'] for x in rows)
  if family=='water':
   result['lines'].append({'ingredients':[x['ingredient'] for x in rows],'family':'water','quantity':0,'unit':'ml','used_cost':0,'cash_cost':0,'product':'Leidingwater; water/energie buiten vergelijking','norm':False});continue
  choices=[]
  index=catalog.setdefault('_indicative_families',{})
  key=(store,family,len(catalog.get(store,[])))
  if key not in index:index[key]=[p for p in catalog.get(store,[]) if product_matches(family,p)]
  for p in index[key]+[p for p in action_products if product_matches(family,p)]:
   size,size_assumed=product_size(p,family,u)
   if not size:continue
   if size_assumed:size*=scale
   cost=purchase(needed,size,p['price'],p.get('action'),today,cards)
   # Consumption ranking optimizes consumption value; checkout remains visible.
   choices.append((cost['used'],cost['cash'],p,size,size_assumed,cost))
  if not choices:
   result['missing'].extend({'ingredient':x['ingredient'],'reason':'Geen passend geprijsd product bij '+store} for x in rows);continue
  _,_,p,size,size_assumed,cost=min(choices,key=lambda t:(t[0],t[1],t[2]['name']))
  labels=list(dict.fromkeys(x['ingredient'] for x in rows))
  result['lines'].append({'ingredients':labels,'family':family,'quantity':round(needed,4),'unit':u,'product':p['name'],
    'package_size':p['amount'],'package_price':p['price'],'packages':cost['packages'],'leftover':round(cost['leftover'],4),
    'price_source':p.get('price_source','Checkjebon'),
    'used_cost':money(cost['used']),'cash_cost':money(cost['cash']),'link':p.get('link'),'action':cost['action'],
    'norm':any(x['norm'] for x in rows) or size_assumed or bool(p.get('assumed_package_unit')),
    'price_proxy':any(x.get('proxy') for x in rows),
    '_used_unrounded':cost['used'],'_cash_unrounded':cost['cash'],
    '_product':p,'_size':size,
    'package_conversion':(p.get('package_assumption_note') or 'Bron zonder verpakkingsinhoud: prijs per stuk aangenomen; controleer in winkel' if p.get('assumed_package_unit') else 'Balsamicocrème: benadering 1,3 g/ml (werkaanname)' if size_assumed and family=='balsamicocreme' else 'Verpakkingsinhoud omgerekend met normstukgewicht of benadering 1 g/ml voor dit ingrediënt' if size_assumed else None)})
 # Different source families can select the same SKU (for example ordinary
 # olive oil and extra virgin oil). Buy its whole packages only once.
 merged={}
 for line in result['lines']:
  if line['family']=='water':merged[('water',)]=line;continue
  key=(line.get('link') or line['product'],line['package_size'],line['unit'])
  if key not in merged:merged[key]=line;continue
  old=merged[key];old['quantity']+=line['quantity'];old['ingredients']=list(dict.fromkeys(old['ingredients']+line['ingredients']));old['norm']=old['norm'] or line['norm']
  p=old['_product'];cost=purchase(old['quantity'],old['_size'],p['price'],p.get('action'),today,cards)
  old.update(packages=cost['packages'],leftover=round(cost['leftover'],4),used_cost=money(cost['used']),cash_cost=money(cost['cash']),action=cost['action'],_used_unrounded=cost['used'],_cash_unrounded=cost['cash'])
 result['lines']=list(merged.values())
 result['missing']=list({x['ingredient']:x for x in result['missing']}.values())
 result['total_ingredients']=len(ingredient_labels)
 result['covered_ingredients']=len(set(ingredient_labels)-{x['ingredient'] for x in result['missing']})
 result['eligible']=bool(ingredient_labels) and not result['missing']
 animal={'kipfilet','kippendijfilet','zalmfilet','kabeljauwfilet','heekfilet','doradefilet','varkenshaas',
         'warmgerookte zalmsnippers','spekreepjes','ontbijtspek','achterham','rundergehakt','varkensgehakt',
         'kippenbouillon','runderbouillon','vissaus','garnalen','pangasiusfilet','half om half gehakt','gehaktballetjes'}
 result['vegetarian_ingredients']=result['eligible'] and not any(x['family'] in animal for x in result['lines'])
 if result['eligible']:
  result['used_total_eur']=money(sum(x.get('_used_unrounded',0) for x in result['lines']))
  result['per_person_eur']=money(result['used_total_eur']/2)
  result['whole_packages_eur']=money(sum(x.get('_cash_unrounded',0) for x in result['lines']))
  result['actions_applied']=sum(bool(x.get('action')) for x in result['lines'])
  baseline=sum(x['quantity']/x['_size']*x['_product']['price'] for x in result['lines'] if x.get('_product'))
  result['used_savings_same_products_eur']=money(max(0,baseline-sum(x.get('_used_unrounded',0) for x in result['lines'])))
 # Partial totals never enter a ranking.
 for x in result['lines']:
  for key in ('_used_unrounded','_cash_unrounded','_product','_size'):x.pop(key,None)
 return result

def estimate_with_sensitivity(recipe,catalog,store,deals,today,cards=False):
 result=estimate_recipe(recipe,catalog,store,deals,today,cards)
 if result['eligible']:
  low=estimate_recipe(recipe,catalog,store,deals,today,cards,.75)
  high=estimate_recipe(recipe,catalog,store,deals,today,cards,1.25)
  values=[x['used_total_eur'] for x in (result,low,high) if x.get('eligible')]
  result['norm_scenario_low_eur']=min(values)
  result['norm_scenario_high_eur']=max(values)
  result['scenario_note']='Normhoeveelheden -25% / +25%; scenario, geen statistisch betrouwbaarheidsinterval. Bronhoeveelheden in g/ml blijven gelijk.'
 return result
