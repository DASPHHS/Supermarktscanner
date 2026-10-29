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
});
