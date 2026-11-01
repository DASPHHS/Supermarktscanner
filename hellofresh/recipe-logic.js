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
function estimateFor(p,cards=false,today=dayFormat.format(new Date())){
 const valid=e=>e && (e.lines||[]).every(line=>!line.action||activeOffer(line.action,today));
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
function originalPdfUrl(path){
 if(typeof path!=='string'||! /^(?:previews|plated-previews)\/[a-zA-Z0-9_-]+\.pdf$/.test(path))return null;
 return 'https://raw.githubusercontent.com/DASPHHS/Supermarktscanner/main/hellofresh/'+path;
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
const api={norm,offerMatches,activeOffer,coverage,verified,completePrice,protein,estimatePrice,estimateFor,selectRecord,rankingPrice,originalPdfUrl};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else root.RecipeLogic=api;
})(typeof globalThis!=='undefined'?globalThis:this);
