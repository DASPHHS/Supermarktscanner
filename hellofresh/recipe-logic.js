/* Shared, DOM-free rules for recipe cards and regression tests. */
(function(root){
'use strict';
const norm=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const units=/\((?:g|ml|el|tl|[^()]+\([^()]+\))\)/g;
const blocked=new Set('saus soep maaltijd maaltijden pizza dip chips wrap quiche poeder smaak puree snack burger gevuld gekruid kruidenmix salade hummus hoemoes geroosterd gebakken vegetarisch vegetarische vegan plantaardig plantaardige'.split(' '));
function offerMatches(ingredient,product){
 const target=norm(String(ingredient).replace(units,'').replace(/\*/g,'' )).split(' ').filter(Boolean);
 const words=norm(product).split(' ');
 return target.length>0 && target.every(w=>words.includes(w)) && !words.some(w=>blocked.has(w)&&!target.includes(w));
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
const api={norm,offerMatches,activeOffer,coverage,verified,completePrice,protein};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
else root.RecipeLogic=api;
})(typeof globalThis!=='undefined'?globalThis:this);
