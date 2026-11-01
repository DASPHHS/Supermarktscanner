/* Fast, dependency-free search across source titles and ingredient labels.
   A missing OCR ingredient never becomes an invented ingredient. */
(function(root){
'use strict';
const norm=v=>String(v??'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim();
const alias={
 kip:['chicken'],chicken:['kip'],zalm:['salmon'],salmon:['zalm'],
 vis:['fish'],fish:['vis'],garnalen:['shrimp'],shrimp:['garnalen'],
 paprika:['bell pepper','peppers'],courgette:['zucchini'],zucchini:['courgette'],
 aardappel:['potato','potatoes','aardappelen'],aardappelen:['aardappel','potato','potatoes'],
 potato:['aardappel','aardappelen'],potatoes:['aardappel','aardappelen'],
 ui:['onion','onions','uien'],uien:['ui','onion','onions'],onion:['ui','uien'],
 tomaat:['tomato','tomaten','tomatoes'],tomaten:['tomaat','tomato','tomatoes'],
 spinach:['spinazie'],spinazie:['spinach'],broccoli:['broccoli'],
 wortel:['carrot','carrots'],wortels:['carrot','carrots'],carrot:['wortel','wortels'],
 kaas:['cheese'],cheese:['kaas'],champignons:['mushroom','mushrooms'],
 mushroom:['champignon','champignons'],mushrooms:['champignon','champignons'],
 gehakt:['ground beef','minced beef','mince'],beef:['rund','rundvlees','runder'],
 kikkererwten:['chickpeas','chickpea'],chickpeas:['kikkererwten'],
 linzen:['lentils'],lentils:['linzen'],aubergine:['eggplant'],eggplant:['aubergine'],
 ei:['eggs','egg','eieren'],eieren:['eggs','egg','ei'],eggs:['eieren','ei'],
 knoflook:['garlic'],garlic:['knoflook'],komkommer:['cucumber'],cucumber:['komkommer'],
 bloemkool:['cauliflower'],cauliflower:['bloemkool'],pompoen:['pumpkin','squash'],
 pumpkin:['pompoen'],rijst:['rice'],rice:['rijst'],bonen:['beans'],beans:['bonen']
};
function searchable(s){return ' '+norm(s)+' ';}
function uniqNames(items){
 if(!Array.isArray(items))return [];
 return [...new Set(items.map(v=>String(typeof v==='string'?v:v?.name??v?.ingredient??'').trim()).filter(Boolean))];
}
function makeIndex(recipes, ingredientsFor){
 const index=new Map();
 for(const r of recipes||[]){
  if(!r?.id)continue;
  const names=uniqNames(typeof ingredientsFor==='function'?ingredientsFor(r):r.ingredients);
  const title=String(r.displayTitle||r.title_extracted||r.title||'');
  const titleCorpus=searchable(title+' '+(r.title_extracted||''));
  const ingredientsCorpus=searchable(names.join(' '));
  index.set(String(r.id),{title:titleCorpus,ingredients:ingredientsCorpus,ingredientCount:names.length,names});
 }
 return index;
}
function findMatches(query,indexItem,ingredientOnly=false){
 if(!indexItem)return false;
 const terms=norm(query).split(' ').filter(Boolean);
 if(!terms.length)return true;
 const corpus=ingredientOnly?indexItem.ingredients:indexItem.title+indexItem.ingredients;
 return terms.every(term=>{
  const synonyms=[term,...(alias[term]||[])];
  return synonyms.some(value=>corpus.includes(' '+value+' ')||
    // Strict prefix only for long words (singular/plural), never short strings such as 'ui'.
    (value.length>=5&&corpus.split(' ').some(word=>word.startsWith(value)&&word.length-value.length<=4)));
 });
}
function stats(recipes,index){
 const list=Array.isArray(recipes)?recipes:[];
 const all=list.length,ingredient=list.filter(r=>(index?.get(String(r.id))?.ingredientCount||0)>0).length;
 return {total:all,ingredientSearchable:ingredient,titleOnly:all-ingredient,
  helloFresh:list.filter(r=>r.source==='HelloFresh').length,
  plated:list.filter(r=>r.source==='Plated').length};
}
const api={norm,makeIndex,findMatches,stats,uniqNames};
if(typeof module==='object'&&module.exports)module.exports=api;
else root.RecipeSearch=api;
})(typeof globalThis!=='undefined'?globalThis:this);
