/* Shared, DOM-free rules for recipe cards and regression tests. */
(function(root){
'use strict';
const dayFormat=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Amsterdam'});
const norm=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const units=/\((?:g|ml|el|tl|[^()]+\([^()]+\))\)/g;
const blocked=new Set('saus soep maaltijd maaltijden pizza dip chips wrap quiche poeder smaak puree snack burger gevuld gekruid kruidenmix salade hummus hoemoes geroosterd gebakken vegetarisch vegetarische vegan plantaardig plantaardige chocolade surprise snoep gedroogd gedroogde zongedroogd zongedroogde granulaat'.split(' '));
const qualifiers=new Set('ah jumbo lidl albert heijn biologisch biologische bio verse vers extra vierge mild milde naturel ongezouten gezouten gesneden heel hele kruimig vastkokend vastkokende fijne fijn grof grove zoutarm zoutarme g gr gram kg ml milliliter liter l stuk stuks st'.split(' '));
function offerMatches(ingredient,product){
 const target=norm(String(ingredient).replace(units,'').replace(/\*/g,'' )).split(' ').filter(Boolean);
 const words=norm(product).split(' ');
 return target.length>0 && target.every(w=>words.includes(w)) && !words.some(w=>blocked.has(w)&&!target.includes(w)) && words.every(w=>target.includes(w)||qualifiers.has(w)||/^\d+(?:g|gr|gram|kg|ml|l|st|stuks|x)?$/.test(w));
}
// Conservative product-to-recipe compatibility: false positives are more harmful than missing leads.
// This is not a guarantee of an equivalent SKU: it only controls candidate display/ranking.
function relevantOfferProduct(ingredient,product){
 const i=norm(String(ingredient||'').replace(/\([^)]*\)/g,'').replace(/\*/g,''));
 const p=norm(product);
 if(!i||!p)return false;
 // Prepared dishes, baby food, snacks, toiletries and drinks are not single cooking ingredients.
 const disallowed=/\b(olvarit|organix|ella|nestle|kleine keuken|knijpfruit|baby|smoothie|groentesmoothie|groentesap|vruchtensap|fruitjes|fruitsap|versgeperst|limonade|snoep|chips|drop|koek|koeken|krakelingen|spritsen|cake|cakejes|poffertjes|wraps|wrap|pinsa|pizza|quiche|verspakket|maaltijd|ovenschotel|soep|pureersoep|saus|pastasaus|salade|salademix|saladekit|broodbeleg|beleg|hummus|hoemoes|pesto|chutney|kant en klaar|knabbels|sticks|puffs|snack|diner|kipshoarma|rijst rondjes|botermix|kruidenboter|spreads|dip|boter|kruidenmix)\b/;
 if(disallowed.test(p))return false;
 // Explicitly reject compound names that do not have word boundaries around the food form.
 // Examples: 'tomatensoep', 'knoflookmarinade', 'borrelbrood', 'kipfilet Toscana'.
 if(/(soep|salade|marinade|borrelbrood|knijpfruit|smoothie|snoep|chips|snack|puffs|sticks|kantklaar|pastasaus|maaltijd|verspakket|kruidenboter|ovenschotel|pinsa|quiche)/.test(p))return false;
 if(/\b(unox|knorr|olvarit|organix|nestle|ella|ch(i|e)o|doritos|lays|lay s|vivera vegetarische)\b/.test(p))return false;
 if(/\b(spinazie kaas filet|zalm pangasius garnalen|vegetarische spinazie)\b/.test(p))return false;
 // Mixtures are not interchangeable with a single ingredient; recipes may need the pure food.
 if(/\b(mix|melange|combinatie|cocktail|kruiden|met|en)\b/.test(p)&&!/\b(tonijn in (olijf)?olie|tonijn in water)\b/.test(p))return false;
 // Different preparation, preservation or flavours may change the recipe.
 if(/\b(gerookt|gerookte|gegrild|gemarineerd|marinade|knoflook|chili|pittig|gekarameliseerd)\b/.test(p)&&!/\b(gerookt|gerookte|gegrild|gemarineerd|knoflook|chili|pittig|gekarameliseerd)\b/.test(i))return false;
 // Whitelist of food categories readily identifiable in the current source feed.
 if(/\bkrieltjes\b/.test(i))return /\bkrieltjes\b/.test(p)&&!/\b(stamppot|puree)\b/.test(p);
 if(/\baardappelen\b/.test(i))return /\baardappelen\b/.test(p)&&!/\b(krieltjes|bakaardappeltjes)\b/.test(p);
 if(/\bkikkererwten\b/.test(i))return /\bkikkererwten\b/.test(p);
 if(/\bmais\b/.test(i))return /\bmais\b/.test(p)&&!/\b(tarwe|puffs)\b/.test(p);
 if(/\btofu\b/.test(i))return /\btofu\b/.test(p);
 if(/\bspinazie\b/.test(i))return /\bspinazie\b/.test(p)&&!/\b(kleinverpakking broccoli|broccoli)\b/.test(p);
 if(/\bkipfilet\b/.test(i)){
  if(!/\bkipfilet\b/.test(p))return false;
  // Pre-sliced 100-120g kipfilet is sandwich meat, not raw chicken for cooking.
  if(/\b(100|110|115|120|125|150)\s*(g|gr|gram)\b/.test(p))return false;
  return /\b(stuks|stuk|filet)\b/.test(p)||/\bkipfilet\b/.test(p)&&!/\b(scharrel)\b/.test(p);
 }
 if(/\b(roerbakgarnalen|garnalen)\b/.test(i))return /\b(roerbakgarnalen|garnalen)\b/.test(p);
 if(/\btonijn\b/.test(i)){
  if(/\b(tonijnfilet|verse tonijn)\b/.test(i))return false;
  if(/\bwater\b/.test(i))return /\btonijn\b/.test(p)&&/\bwater\b/.test(p);
  if(/\b(olijfolie|olie)\b/.test(i))return /\btonijn\b/.test(p)&&/\b(olijfolie|olie)\b/.test(p);
  return /\btonijn\b/.test(p);
 }
 // Unlisted ingredients require an exact, simple packaged-product name.
 const prepWords=new Set(['verse','vers','biologische','biologisch','bio','kleine','klein','rood','rode','groen','groene','wit','witte']);
 const target=i.split(' ').filter(w=>!prepWords.has(w)&&!['g','gram','ml','stuk','stuks'].includes(w));
 if(!target.length)return false;
 const brands=new Set(['ah','jumbo','hak','bonduelle','vivera','rodolfi','fish','tales','excellent']);
 const formats=new Set(['verse','vers','bio','biologisch','biologische','kleinverpakking','stuks','stuk','g','gr','gram','kg','ml','l','milliliter','liter','pak','pack','mini','origineel','original','naturel']);
 const words=p.split(' ').filter(w=>!brands.has(w));
 return target.every(w=>words.includes(w))&&words.every(w=>target.includes(w)||formats.has(w)||/^\d+(?:g|gr|gram|kg|ml|l|stuks?)?$/.test(w));
}
function activeOffer(d,today){return typeof d.valid_from==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d.valid_from)&&typeof d.valid_until==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d.valid_until)&&d.valid_from<=today&&d.valid_until>=today;}
function coverage(total,p){
 const matched=p?(p.matches||[]).length:0;
 const explicit=p?(p.missing||[]).length:0;
 const knownTotal=Math.max(total||0,matched+explicit);
 return {matched,missing:Math.max(explicit,knownTotal-matched),total:knownTotal,available:!!p,unknown:knownTotal===0};
}
function verified(r){return r.quality==='verified'&&r.pricing_eligible===true&&r.ingredients_verified===true&&r.quantities_verified===true&&r.servings_verified===true&&r.servings===4;}
function completePrice(r,p){
 if(!verified(r)||!p?.complete||p.recipe_review_required===true||p.missing?.length)return null;
 const value=p.used_cost_eur??p.used_cost_4p_eur;
 return Number.isFinite(value)&&value>=0?value:null;
}
function estimatePrice(e){
 return e?.eligible===true&&Array.isArray(e.missing)&&e.missing.length===0&&e.total_ingredients>0&&e.covered_ingredients===e.total_ingredients&&Number.isFinite(e.used_total_eur)&&e.used_total_eur>=0?e.used_total_eur:null;
}
function validActionLine(line,today=dayFormat.format(new Date()),cards=false){
 if(!line||!line.action||!activeOffer(line.action,today)||line.action.personal_offer===true)return false;
 if(line.action.card_required===true&&!cards)return false;
 // A multi-buy requires enough actual packs at checkout. Otherwise a discounted unit price is misleading.
 const minimum=Number(line.action.multi_buy_quantity);
 if(Number.isFinite(minimum)&&minimum>1){
  if(!Number.isFinite(Number(line.packages))||Number(line.packages)<minimum)return false;
  if(!Number.isFinite(Number(line.action.multi_buy_price))||Number(line.action.multi_buy_price)<=0)return false;
 }
 if(Number.isFinite(Number(line.action.max_per_customer))&&Number(line.action.max_per_customer)>0&&Number(line.packages)>Number(line.action.max_per_customer))return false;
 if(!Array.isArray(line.ingredients)||typeof line.product!=='string')return false;
 // Both the actual chosen SKU and its action name must represent the recipe ingredient.
 return line.ingredients.some(i=>relevantOfferProduct(i,line.product)
  &&(typeof line.action.name!=='string'||relevantOfferProduct(i,line.action.name)));
}
function appliedActionLines(estimate,cards=false,today=dayFormat.format(new Date())){
 if(estimatePrice(estimate)===null)return [];
 return (estimate.lines||[]).filter(line=>validActionLine(line,today,cards));
}
function estimateFor(p,cards=false,today=dayFormat.format(new Date())){
 const valid=e=>e&&(e.lines||[]).every(line=>!line.action||validActionLine(line,today,cards));
 if(cards&&valid(p?.estimate_with_cards))return p.estimate_with_cards;
 return valid(p?.estimate)?p.estimate:null;
}
function rankingPrice(e,basis='used'){
 if(estimatePrice(e)===null)return null;
 if(basis!=='cash')return e.used_total_eur;
 return Number.isFinite(e.whole_packages_eur)&&e.whole_packages_eur>=0?e.whole_packages_eur:null;
}
function selectRecord(records,cards=false,basis='used'){
 const present=records.filter(Boolean);
 const price=p=>rankingPrice(estimateFor(p,cards),basis);
 const priced=present.filter(p=>price(p)!==null);
 return priced.length?priced.sort((a,b)=>price(a)-price(b)||a.store.localeCompare(b.store))[0]:present.sort((a,b)=>(estimateFor(b,cards)?.covered_ingredients||0)-(estimateFor(a,cards)?.covered_ingredients||0))[0];
}
// Conservative what-if checkout: compare comparable loose-food SKU alternatives from a
// current, product-level promotion feed. Not an independently confirmed shelf price.
function offerPackageAmount(raw){
 if(typeof raw!=='string')return null;
 const m=raw.trim().toLowerCase().replace(',','.').match(/^(\d+(?:\.\d+)?)\s*(kg|g|gr|gram|ml|l|liter|milliliter)$/);
 if(!m)return null;
 let n=Number(m[1]);if(!Number.isFinite(n)||n<=0)return null;
 return {amount:n*(m[2]==='kg'||m[2]==='l'||m[2]==='liter'?1000:1),
  unit:['ml','l','liter','milliliter'].includes(m[2])?'ml':'g'};
}
function offerRankingTier(complete,applied,matchingStoreCandidate){
 // A lead at another store is NOT a saving on the chosen store's checkout.
 if(!complete)return 3;
 if(applied)return 0;
 if(matchingStoreCandidate)return 1;
 return 2;
}
function estimateWithOfferAlternatives(estimate,shopDeals=[],opts={}){
 if(estimatePrice(estimate)===null||!Number.isFinite(estimate.whole_packages_eur))
  return {estimate,changes:[],totalSavings:0};
 const today=opts.today||dayFormat.format(new Date());
 const cards=opts.cards===true;
 const matches=typeof opts.matches==='function'?opts.matches:null;
 let changes=[],cashDelta=0,usedDelta=0;
 const lines=estimate.lines.map(line=>{
  if(line.action||line.price_proxy||!Array.isArray(line.ingredients)||!line.ingredients.length||
    !Number.isFinite(line.quantity)||line.quantity<=0||!['g','ml'].includes(line.unit)||
    !Number.isFinite(line.cash_cost)||!Number.isFinite(line.used_cost)||!Number.isFinite(line.packages))return line;
  const candidates=matches?line.ingredients.flatMap(i=>matches(i)):
   shopDeals.filter(d=>line.ingredients.some(i=>relevantOfferProduct(i,d.name)));
  let winner=null;
  for(const d of candidates){
   if(!activeOffer(d,today)||d.personal_offer===true||d.loyalty_warning===true||
      d.card_required===true&&!cards)continue;
   if(!Number.isFinite(d.price)||d.price<=0||
      !Number.isFinite(d.original_price)||d.original_price<=d.price)continue;
   // The compact feed lacks a reliable total amount payable for multi-buy deals.
   if(Number.isFinite(d.multi_buy_quantity)&&d.multi_buy_quantity>1)continue;
   if(!['percentage','fixed_amount','fixed_price',null,''].includes(d.promotion_type||null))continue;
   if(!line.ingredients.some(i=>relevantOfferProduct(i,d.name)))continue;
   const size=offerPackageAmount(d.quantity);
   if(!size||size.unit!==line.unit)continue;
   const packs=Math.ceil((line.quantity-1e-9)/size.amount);
   if(!Number.isSafeInteger(packs)||packs<=0||packs>30)continue;
   const cash=Number((packs*d.price).toFixed(4));
   const use=Number((line.quantity/size.amount*d.price).toFixed(4));
   const saving=line.cash_cost-cash;
   if(saving<=0.01||!Number.isFinite(use)||use<0)continue;
   if(!winner||cash<winner.cash-0.0001)
    winner={deal:d,cash,use,packs,amount:size.amount,saving};
  }
  if(!winner)return line;
  const d=winner.deal;
  cashDelta+=winner.cash-line.cash_cost;
  usedDelta+=winner.use-line.used_cost;
  changes.push({
   ingredients:line.ingredients.slice(),from:line.product,to:d.name,store:opts.store||null,
   regularCash:line.cash_cost,offerCash:winner.cash,saving:winner.saving,
   quantity:line.quantity,unit:line.unit,packages:winner.packs,packageSize:d.quantity,
   deal:d
  });
  return {...line,product:d.name,link:d.product_url||null,package_size:d.quantity,
   package_price:d.price,packages:winner.packs,cash_cost:winner.cash,used_cost:winner.use,
   leftover:Math.max(0,winner.packs*winner.amount-line.quantity),
   price_source:'Weekdeals actiescenario (indicatief)',
   action:{...d,name:d.name},scenario_offer:true,price_proxy:false};
 });
 if(!changes.length)return {estimate,changes:[],totalSavings:0};
 const whole=Math.max(0,Number((estimate.whole_packages_eur+cashDelta).toFixed(2)));
 const used=Math.max(0,Number((estimate.used_total_eur+usedDelta).toFixed(2)));
 const optimized={...estimate,lines,whole_packages_eur:whole,used_total_eur:used,
  per_person_eur:Number((used/2).toFixed(2)),scenario_offer:true,
  scenario_original_whole_eur:estimate.whole_packages_eur,
  scenario_savings_eur:Number((estimate.whole_packages_eur-whole).toFixed(2)),
  actions_applied:(estimate.actions_applied||0)+changes.length};
 return {estimate:optimized,changes,totalSavings:optimized.scenario_savings_eur};
}
function originalPdfUrl(path){
 if(typeof path!=='string'||! /^(?:previews|plated-previews)\/[a-zA-Z0-9_-]+\.pdf$/.test(path))return null;
 return 'https://raw.githubusercontent.com/DASPHHS/Supermarktscanner/main/hellofresh/'+path;
}
// Ingredient hints are discovery aids, not calculated nutritional claims.
function mealHints(recipe){
 if(!recipe?.table_repair||recipe.image_only_archive)return [];
 const items=recipe.ingredients_2p?.length?recipe.ingredients_2p:recipe.ingredients_4p;
 if(!Array.isArray(items)||items.length<2||items.some(i=>!i?.ingredient))return [];
 const names=norm(items.filter(i=>!/bouillon|stock|broth/i.test(i.ingredient)).map(i=>i.ingredient.replace(/\([^)]*\)/g,' ')).join(' '));
 const hints=[];
 if(/\b(kip\w*|kalkoen\w*|zalm\w*|vis\w*|garnal\w*|tonijn|gehakt\w*|rund\w*|biefstuk|varken\w*|tofu|tempeh|kikkererwten|linzen|bonen|ei|eieren)\b/.test(names))hints.push('protein');
 if(!/\b(aardappel\w*|krieltjes|rijst|risotto|pasta|spaghetti|orzo|noedel\w*|couscous|bulgur|quinoa|brood\w*|wrap\w*|tortilla\w*|naan|bloem|meel|mais|polenta|gnocchi|lasagne|linzen|bonen|kikkererwten)\b/.test(names))hints.push('low_starch');
 return hints;
}
function protein(title,labels=[]){
 const classify=t=>{
  if(/\b(vegetarisch|vegetarische|vega|veggie|plantaardig|plantaardige|vegan|tofu|tempeh|falafel)\b/.test(t))return 'vega';
  if(/\b(kip\w*|kalkoen\w*|chicken|turkey)\b/.test(t))return 'kip';
  if(/\b(zalm\w*|tonijn|garnal\w*|heek\w*|kabeljauw\w*|vis\w*|forel|makreel|tilapia|pangasius\w*|schelvis|shrimp|salmon|koolvis)\b/.test(t))return 'vis';
  if(/\b(gehakt\w*|rund\w*|varken\w*|spek\w*|worst\w*|biefstuk|chorizo|hamburger\w*|schnitzel|lams\w*|saucijs|rookworst|ribeye|beef|pork|ham|bacon|burger\w*)\b/.test(t))return 'vlees';
  return null;
 };
 // Main protein in the title takes precedence over chicken stock in a beef dish.
 return classify(norm(title))||classify(norm(labels.filter(x=>!/(bouillon|stock|broth)/i.test(x)).join(' ')))||'onbekend';
}
const api={norm,offerMatches,relevantOfferProduct,validActionLine,appliedActionLines,activeOffer,coverage,verified,completePrice,protein,mealHints,estimatePrice,estimateFor,selectRecord,rankingPrice,offerPackageAmount,offerRankingTier,estimateWithOfferAlternatives,originalPdfUrl};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else root.RecipeLogic=api;
})(typeof globalThis!=='undefined'?globalThis:this);
