const {test}=require('node:test');
const assert=require('node:assert/strict');
const L=require('../hellofresh/recipe-logic.js');
test('ingredient words do not match processed food containing that word',()=>{
 for(const [a,b] of [['Paprika (stuk(s))',"Lay’s Paprika Chips 125 g"],['Knoflookteen (stuk(s))','Jumbo Champignons Knoflook 100 g'],['Tomaat (g)','Unox Tomaat Soep'],['Kipfilet (g)','Vivera Plantaardige Kipfilet 200 g']])assert.equal(L.offerMatches(a,b),false);
 assert.equal(L.offerMatches('Champignons (g)','Jumbo Champignons 250 g'),true);
 assert.equal(L.offerMatches('Ui (stuk(s))','Jumbo Filet Americain Ui 150 g'),false);
 assert.equal(L.offerMatches('Ui (stuk(s))','Jumbo Gesneden Peen en Ui Hutspot 500 g'),false);
});
test('no price snapshot does not imply no missing ingredients',()=>{
 assert.deepEqual(L.coverage(8,null),{matched:0,missing:8,total:8,available:false,unknown:false});
 assert.equal(L.coverage(0,null).unknown,true);
 assert.equal(L.coverage(9,{matches:[{},{}],missing:[{}]}).missing,7);
});
test('promotion must have complete and current dates',()=>{
 assert.equal(L.activeOffer({valid_from:'2026-10-21',valid_until:'2026-10-27'},'2026-10-29'),false);
 assert.equal(L.activeOffer({},'2026-10-29'),false);
 assert.equal(L.activeOffer({valid_from:'2026-10-28',valid_until:'2026-11-03'},'2026-10-29'),true);
});
test('quality label alone cannot approve recipe costs',()=>{
 assert.equal(L.completePrice({quality:'verified'},{complete:true,used_cost_4p_eur:4}),null);
 const r={quality:'verified',pricing_eligible:true,ingredients_verified:true,quantities_verified:true,servings_verified:true,servings:4};
 assert.equal(L.completePrice(r,{complete:true,used_cost_eur:4,servings:2,missing:[]}),4);
 assert.equal(L.completePrice(r,{complete:true,used_cost_eur:4,missing:[{}]}),null);
});
test('beef stays beef with chicken stock; unknown is not vegetarian',()=>{
 assert.equal(L.protein('Beef Bolognese',['kippenbouillon']),'vlees');
 assert.equal(L.protein('Onbekend gerecht',['ui']),'onbekend');
 assert.equal(L.protein('Vegetarische kipburger'),'vega');
 assert.equal(L.protein('Barbecue Chicken Barbecuekip'),'kip');
 assert.equal(L.protein('Beef Bolognese Bolognesesaus',['kippenbouillon']),'vlees');
});
test('only complete indicative costs can enter the price ranking',()=>{
 const e={eligible:true,missing:[],total_ingredients:1,covered_ingredients:1,used_total_eur:3};
 assert.equal(L.estimatePrice(e),3);
 assert.equal(L.estimatePrice({...e,eligible:false}),null);
 assert.equal(L.estimatePrice({...e,missing:[{}]}),null);
 assert.equal(L.estimatePrice({...e,covered_ingredients:0}),null);
 assert.equal(L.estimatePrice({...e,used_total_eur:NaN}),null);
});
test('store choice and order react to prices and card promotions',()=>{
 const e=n=>({eligible:true,missing:[],total_ingredients:1,covered_ingredients:1,used_total_eur:n});
 const a={store:'AH',estimate:e(4),estimate_with_cards:e(2)};
 const j={store:'Jumbo',estimate:e(3),estimate_with_cards:e(3)};
 assert.equal(L.selectRecord([a,j],false).store,'Jumbo');
 assert.equal(L.selectRecord([a,j],true).store,'AH');
 j.estimate.used_total_eur=5;
 assert.equal(L.selectRecord([a,j],false).store,'AH');
 assert.equal(L.selectRecord([a,{store:'Lidl',estimate:{eligible:false,missing:[{}]}}],false).store,'AH');
 assert.equal(L.estimateFor({estimate:e(3)},true).used_total_eur,3);
});
test('original PDFs remain downloadable outside the Pages size budget',()=>{
 assert.equal(L.originalPdfUrl('plated-previews/abc123-origineel.pdf'),'https://raw.githubusercontent.com/DASPHHS/Supermarktscanner/main/hellofresh/plated-previews/abc123-origineel.pdf');
 assert.equal(L.originalPdfUrl('previews/abc123-origineel.pdf'),'https://raw.githubusercontent.com/DASPHHS/Supermarktscanner/main/hellofresh/previews/abc123-origineel.pdf');
 for(const p of ['../secret.pdf','https://evil.test/a.pdf','previews/../../a.pdf',null])assert.equal(L.originalPdfUrl(p),null);
});
test('cash basis chooses the cheaper basket while consumed costs remain separate',()=>{
 const e=(used,cash)=>({eligible:true,missing:[],total_ingredients:1,covered_ingredients:1,used_total_eur:used,whole_packages_eur:cash});
 const a={store:'AH',estimate:e(2,30)},j={store:'Jumbo',estimate:e(3,4)};
 assert.equal(L.selectRecord([a,j],false,'used').store,'AH');
 assert.equal(L.selectRecord([a,j],false,'cash').store,'Jumbo');
 assert.equal(L.rankingPrice({...a.estimate,whole_packages_eur:NaN},'cash'),null);
});
test('expired action totals are removed; card mode can fall back to a current base estimate',()=>{
 const action={valid_from:'2026-10-26',valid_until:'2026-11-01'};
 const base={lines:[]},discounted={lines:[{action}]};
 assert.equal(L.estimateFor({estimate:discounted},false,'2026-11-02'),null);
 assert.equal(L.estimateFor({estimate:base,estimate_with_cards:discounted},true,'2026-11-02'),base);
 assert.equal(L.estimateFor({estimate:discounted},false,'2026-11-01'),discounted);
});
