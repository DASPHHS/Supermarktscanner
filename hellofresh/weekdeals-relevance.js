/* Conservative HelloFresh ingredient ↔ published Weekdeals *candidate* discovery.
   It never changes basket prices, validates savings, or certifies substitutions. */
(function(root){
'use strict';
const normalize=s=>String(s??'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const FAMILY_DEFS=[
 ['aardappel','Aardappelen',/\baardappelen?\b/,/\baardappelen?\b/,['groente-fruit']],
 ['zoete-aardappel','Zoete aardappel',/\bzoete aardappelen?\b/,/\bzoete aardappelen?\b/,['groente-fruit']],
 ['broccoli','Broccoli',/\bbroccoli\b/,/\bbroccoli(roosjes)?\b/,['groente-fruit']],
 ['champignon','Champignons',/\bchampignons?\b/,/\bchampignons?\b/,['groente-fruit']],
 ['spinazie','Spinazie',/\bspinazie\b/,/\bspinazie\b/,['groente-fruit','diepvries']],
 ['paprika','Paprika',/\bpaprika(s)?\b/,/\bpaprika(s)?\b/,['groente-fruit']],
 ['courgette','Courgette',/\bcourgette(s)?\b/,/\bcourgette(s)?\b/,['groente-fruit']],
 ['ui','Uien',/\b(uien|ui)\b/,/\b(uien|ui)\b/,['groente-fruit']],
 ['knoflook','Knoflook',/\bknoflook(teen|tenen)?\b/,/\bknoflook\b/,['groente-fruit']],
 ['wortel','Wortels',/\b(wortel(s|tjes)?|bospeen|peen)\b/,/\b(wortel(s|tjes)?|bospeen|peen)\b/,['groente-fruit']],
 ['komkommer','Komkommer',/\bkomkommers?\b/,/\bkomkommers?\b/,['groente-fruit']],
 ['citroen','Citroen',/\bcitroenen?\b/,/\bcitroenen?\b/,['groente-fruit']],
 ['tomaat','Verse tomaten',/\b(tomaat|tomaten|cherrytomaten|kerstomaten)\b/,/\b(tomaten|tomaat|cherrytomaten|kerstomaten)\b/,['groente-fruit']],
 ['tomatenblokjes','Tomatenblokjes',/\btomatenblokjes\b/,/\btomatenblokjes\b/,['soepen-conserven-sauzen']],
 ['tomatenpuree','Tomatenpuree',/\btomatenpuree\b/,/\btomatenpuree\b/,['soepen-conserven-sauzen']],
 ['kikkererwten','Kikkererwten',/\bkikkererwten\b/,/\bkikkererwten\b/,['soepen-conserven-sauzen']],
 ['linzen','Linzen',/\blinzen\b/,/\blinzen\b/,['soepen-conserven-sauzen']],
 ['kokosmelk','Kokosmelk',/\bkokosmelk\b/,/\bkokosmelk\b/,['soepen-conserven-sauzen','pasta-rijst-wereldkeuken']],
 ['mozzarella','Mozzarella',/\bmozzarella\b/,/\bmozzarella\b/,['kaas']],
 ['feta','Feta',/\bfeta\b/,/\bfeta\b/,['kaas']],
 ['geraspte-kaas','Geraspte kaas',/\bgeraspte kaas\b/,/\bgeraspte kaas\b/,['kaas']],
 ['kipfilet','Kipfilet',/\bkipfilet\b/,/\bkipfilet\b/,['vlees']],
 ['rundergehakt','Rundergehakt',/\brundergehakt\b/,/\brundergehakt\b/,['vlees']],
 ['zalmfilet','Zalmfilet',/\b(zalmfilet|verse zalm)\b/,/\b(zalmfilet|verse zalm)\b/,['vis']],
 ['eieren','Eieren',/\b(ei|eieren)\b/,/\b(eieren|eieren maat|scharreleieren)\b/,['zuivel-eieren']],
 ['rijst','Rijst',/\b(basmatirijst|jasmijnrijst|witte rijst|rijst)\b/,/\b(basmatirijst|jasmijnrijst|witte rijst)\b/,['pasta-rijst-wereldkeuken']],
 ['penne','Penne',/\bpenne\b/,/\bpenne\b/,['pasta-rijst-wereldkeuken']],
 ['spaghetti','Spaghetti',/\bspaghetti\b/,/\bspaghetti\b/,['pasta-rijst-wereldkeuken']]
];
const FAMILIES=FAMILY_DEFS.map(([id,label,ingredient,product,categories])=>({id,label,ingredient,product,categories}));
const BLOCKED=/\b(salade|salademix|saladekit|saus|maaltijdmix|ovenmix|mix|soep|soepmix|cup a soup|pesto|spread|dip|smoothie|sap|chips|snack|wrap|pizza|quiche|lasagne|ovenschotel|stamppot|burger|gehaktballetjes|schnitzel|dressing|hummus|roerbakgroente|rauwkost|maaltijd|rolletjes|vleeswaren|beleg|sandwich|kruidenmix|gemarineerd|gerookt|gerookte|gegrild)\b/;
const BLOCKED_TEXT=/(tomatensoep|champignonsaus|pastasaus|knoflooksaus|broccolisoep|pizzasaus|kruidenboter|kipfiletrolletjes|vegetarische kip|plantaardige kip|tomatenketchup|groentesap|groentesmoothie)/;
const STATE_WORDS=/\b(gedroogd|gedroogde|zongedroogd|zongedroogde|gevriesdroogd|gekonfijt|geroosterd|geroosterde|gekruid|gekruide|gekarameliseerd|gekarameliseerde)\b/;
const CATEGORY_EXTRAS={
 broccoli:/\b(bloemkool|broccoli met|broccoli en)\b/,
 champignon:/\b(roerbak|paddenstoelenmix)\b/,
 paprika:/\b(rauwkost|groentesap|bakaardappel)\b/,
 tomaat:/\b(gedroogde|gedroogd|tomatenpulp|tomatenpuree|gepelde|tomatenblokjes)\b/,
 ui:/\b(uitjes|uienringen|gebakken|gebakken ui|frituur|zoetzure)\b/,
 kipfilet:/\b(kipfilethaasjes|kipfiletrolletjes|gepaneerd|scharrel kipfilet beleg)\b/,
 zalmfilet:/\b(zalmsalade|zalmspread|tonijn|visburger|blik)\b/,
 mozzarella:/\b(geraspt|mezzelune|ravioli)\b/,
 eieren:/\b(chocolade|paas|gevuld|mayonaise)\b/,
 rijst:/\b(rijstpudding|rijstwafel|rijstcracker|rijstdrink)\b/
};
const SPECIAL_INGREDIENTS={
 'zoete-aardappel':/\bzoete aardappelen?\b/,
 aardappel:/\baardappelen?\b/
};
function ingredientFamily(ingredient){
 const name=normalize(ingredient);
 if(!name||/\b(bouillon|zelf toevoegen|naar smaak|optioneel|water)\b/.test(name))return null;
 // Keep similar ingredient types separate (sweet/regular potatoes, canned/fresh tomato).
 if(SPECIAL_INGREDIENTS['zoete-aardappel'].test(name))return FAMILIES.find(x=>x.id==='zoete-aardappel');
 if(/\btomatenpuree\b/.test(name))return FAMILIES.find(x=>x.id==='tomatenpuree');
 if(/\btomatenblokjes\b/.test(name))return FAMILIES.find(x=>x.id==='tomatenblokjes');
 if(/\bgeraspte kaas\b/.test(name))return FAMILIES.find(x=>x.id==='geraspte-kaas');
 for(const family of FAMILIES){
  if(family.id==='zoete-aardappel'||family.id==='tomatenpuree'||family.id==='tomatenblokjes'||family.id==='geraspte-kaas')continue;
  if(family.ingredient.test(name))return family;
 }
 return null;
}
function isCandidate(family,deal){
 if(!family||!deal||typeof deal.name!=='string'||typeof deal.category!=='string')return false;
 if(!family.categories.includes(deal.category))return false;
 const name=normalize(deal.name);
 if(!family.product.test(name)||BLOCKED.test(name)||BLOCKED_TEXT.test(name)||STATE_WORDS.test(name))return false;
 if(CATEGORY_EXTRAS[family.id]?.test(name))return false;
 if(family.id==='aardappel'&&/\bzoete\b/.test(name))return false;
 if(family.id==='tomaat'&&/\b(soep|blik|conserven)\b/.test(name))return false;
 if(family.id==='kipfilet'&&/\b(vegetarisch|vegan|plantaardig|kipfilet beleg)\b/.test(name))return false;
 if(family.id==='zalmfilet'&&/\b(gerookt|gerookte|in olie|in water)\b/.test(name))return false;
 if(family.id==='spinazie'&&/\b(roomkaas|a la creme)\b/.test(name))return false;
 return true;
}
function safeProductUrl(raw){
 if(typeof raw!=='string'||raw.length>600)return null;
 try{
  const u=new URL(raw);
  if(u.protocol!=='https:'||u.username||u.password||u.port)return null;
  const host=u.hostname.toLowerCase();
  if(!['ah.nl','jumbo.com','lidl.nl','prijsprofeet.nl'].some(x=>host===x||host.endsWith('.'+x)))return null;
  return u.href;
 }catch(_){return null;}
}
function dayInAmsterdam(now){
 return new Date(now).toLocaleDateString('sv-SE',{timeZone:'Europe/Amsterdam'});
}
function validateFeed(feed,now=new Date()){
 if(!feed||feed.schema_version!==1||feed.coverage?.full_promotional_feed!==true||
  feed.source_url!=='https://dasphhs.github.io/specialedeals/weekdeals/'||
  !['AH','Jumbo','Lidl'].every(s=>Array.isArray(feed.stores?.[s]?.deals)))return false;
 const parsed=new Date(feed.updated_at_utc),date=new Date(now);
 const age=date.getTime()-parsed.getTime();
 return Number.isFinite(age)&&age>=0&&age<48*3600000&&feed.as_of_date===dayInAmsterdam(date);
}
function build(recipes,feed,now=new Date()){
 if(!validateFeed(feed,now))return {status:'unavailable',families:[],byRecipe:{},reason:'Geen actuele volledige Weekdeals-bron'};
 if(!Array.isArray(recipes))return {status:'unavailable',families:[],byRecipe:{},reason:'Receptenindex ontbreekt'};
 const byRecipe=Object.create(null),byFamily=new Map();
 for(const family of FAMILIES)byFamily.set(family.id,{id:family.id,label:family.label,recipes:[],offers:[]});
 let indexed=0;
 for(const recipe of recipes){
  if(!recipe||recipe.source!=='HelloFresh'||!recipe.id||!recipe.title_extracted)continue;
  indexed++;
  const ingredients=Array.isArray(recipe.ingredients_2p)&&recipe.ingredients_2p.length?recipe.ingredients_2p:
   Array.isArray(recipe.ingredients_4p)?recipe.ingredients_4p:[];
  const used=new Set();
  for(const row of ingredients){
   const family=ingredientFamily(row?.ingredient);
   if(family&&!used.has(family.id)){
    used.add(family.id);
    const group=byFamily.get(family.id);
    group.recipes.push({id:String(recipe.id),title:String(recipe.title_extracted).slice(0,140)});
   }
  }
  byRecipe[String(recipe.id)]=[...used];
 }
 const today=dayInAmsterdam(now);
 for(const [store,collection] of Object.entries(feed.stores)){
  if(!['AH','Jumbo','Lidl'].includes(store))continue;
  for(const offer of collection.deals){
   if(!offer||typeof offer.name!=='string'||!Number.isFinite(offer.price)||offer.price<=0||
      offer.price>200||!Number.isFinite(Date.parse(offer.valid_from))||
      !Number.isFinite(Date.parse(offer.valid_until))||offer.valid_from>today||offer.valid_until<today)continue;
   if(offer.personal_offer===true)continue;
   for(const family of FAMILIES){
    const group=byFamily.get(family.id);
    if(!group.recipes.length||!isCandidate(family,offer))continue;
    const id=String(offer.product_id||store+'|'+offer.name+'|'+offer.quantity);
    if(group.offers.some(x=>x.store===store&&x.id===id))continue;
    group.offers.push({
     id,store,name:String(offer.name).slice(0,140),price:offer.price,
     original_price:Number.isFinite(offer.original_price)&&offer.original_price>offer.price?offer.original_price:null,
     quantity:typeof offer.quantity==='string'?offer.quantity.slice(0,60):null,
     valid_until:offer.valid_until,
     url:safeProductUrl(offer.product_url),
     multi_buy:Number.isInteger(offer.multi_buy_quantity)&&offer.multi_buy_quantity>1?offer.multi_buy_quantity:null,
     loyalty:offer.loyalty_warning===true||offer.card_required===true,
     category:offer.category
    });
   }
  }
 }
 const families=[...byFamily.values()].filter(x=>x.recipes.length&&x.offers.length).map(group=>{
  group.offers.sort((a,b)=>a.store.localeCompare(b.store,'nl')||a.name.localeCompare(b.name,'nl'));
  return {id:group.id,label:group.label,recipe_count:group.recipes.length,
   offer_count:group.offers.length,recipes:group.recipes.slice(0,5),offers:group.offers.slice(0,60)};
 }).sort((a,b)=>b.recipe_count-a.recipe_count||b.offer_count-a.offer_count||a.label.localeCompare(b.label,'nl'));
 return {status:'ok',families,byRecipe,updated_at_utc:feed.updated_at_utc,as_of_date:feed.as_of_date,
  recipe_count:indexed,ingredient_count:families.length,offer_count:families.reduce((n,x)=>n+x.offer_count,0),
  source_url:feed.source_url};
}
const api={normalize,ingredientFamily,isCandidate,validateFeed,safeProductUrl,build,dayInAmsterdam};
if(typeof module==='object'&&module.exports)module.exports=api;
else root.WeekdealsRelevance=api;
})(typeof globalThis!=='undefined'?globalThis:this);
