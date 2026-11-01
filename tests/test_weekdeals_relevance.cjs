const {test}=require('node:test');
const assert=require('node:assert/strict');
const L=require('../hellofresh/weekdeals-relevance.js');
const NOW=new Date('2026-11-01T12:00:00Z');
const source=(overrides={})=>({
 schema_version:1,source_url:'https://dasphhs.github.io/specialedeals/weekdeals/',
 updated_at_utc:'2026-11-01T11:11:44+00:00',as_of_date:'2026-11-01',
 coverage:{full_promotional_feed:true},stores:{AH:{deals:[]},Jumbo:{deals:[]},Lidl:{deals:[]}},...overrides
});
const offer=(name,category,extras={})=>({product_id:name,name,category,price:1.49,
 valid_from:'2026-10-30',valid_until:'2026-11-04',quantity:'250 g',product_url:'https://www.ah.nl/producten/product/123',...extras});
const recipe=(id,title,ingredients)=>({id,source:'HelloFresh',title_extracted:title,
 ingredients_2p:ingredients.map(ingredient=>({ingredient}))});

test('rejects dated/incomplete feeds and never silently treats old products as current',()=>{
 const r=[recipe('1','Aardappelen',['Aardappelen (g)'])];
 assert.equal(L.build(r,source({as_of_date:'2026-10-29'}),NOW).status,'unavailable');
 assert.equal(L.build(r,source({coverage:{full_promotional_feed:false}}),NOW).status,'unavailable');
 assert.equal(L.build(r,source({updated_at_utc:'2026-10-28T10:00:00Z'}),NOW).status,'unavailable');
 assert.equal(L.build(r,source({source_url:'https://evil.test/weekdeals/'}),NOW).status,'unavailable');
});

test('matched ingredients count distinct recipes from HelloFresh and Plated',()=>{
 const recipes=[
  recipe('1','Aardappelen met kikkererwten',['Aardappelen (g)','Aardappelen (g)','Kikkererwten (blik)']),
  recipe('2','Salade aardappelen',['Aardappelen (g)','Ui (stuk(s))']),
  {...recipe('3','Plated aardappel',['Aardappelen (g)']),source:'Plated'}
 ];
 const feed=source({stores:{
  AH:{deals:[offer('AH Kruimige aardappelen','groente-fruit'),offer('Bonduelle Kikkererwten','soepen-conserven-sauzen')]},
  Jumbo:{deals:[]},Lidl:{deals:[]}
 }});
 const result=L.build(recipes,feed,NOW);
 assert.equal(result.status,'ok');
 assert.equal(result.recipe_count,3);
 assert.equal(result.families.find(f=>f.id==='aardappel').recipe_count,3);
 assert.equal(result.families.find(f=>f.id==='kikkererwten').recipe_count,1);
 assert.deepEqual(result.byRecipe['1'].sort(),['aardappel','kikkererwten']);
 assert.ok(result.byRecipe['3'].includes('aardappel'),'Plated also receives a related deal category');
});

test('rejects chips, soup, wraps, ready meals, combinations and untrusted links',()=>{
 const f=L.ingredientFamily('Broccoli (g)');
 assert.ok(f);
 assert.equal(L.isCandidate(f,offer('Knorr Maaltijdmix broccoli ovenschotel','pasta-rijst-wereldkeuken')),false);
 assert.equal(L.isCandidate(f,offer('AH Bloemkool broccoli kleinverpakking','groente-fruit')),false);
 assert.equal(L.isCandidate(f,offer('AH Broccoliroosjes','groente-fruit')),true);
 const paprika=L.ingredientFamily('Paprika (stuk(s))');
 assert.equal(L.isCandidate(paprika,offer('AH Bakaardappeltjes paprika en knoflook','groente-fruit')),false);
 const tomato=L.ingredientFamily('Tomaat (g)');
 assert.equal(L.isCandidate(tomato,offer('Knorr Tomaten wraps','groente-fruit')),false);
 const lentil=L.ingredientFamily('Linzen (g)');
 assert.equal(L.isCandidate(lentil,offer('AH Terra Pureersoep pompoen linzen','soepen-conserven-sauzen')),false);
 assert.equal(L.safeProductUrl('https://ah.nl.evil.test/x'),null);
 assert.equal(L.safeProductUrl('javascript:alert(1)'),null);
 assert.equal(L.safeProductUrl('https://www.ah.nl/producten/product/123'),'https://www.ah.nl/producten/product/123');
});

test('only valid period offers; no historical discount or unsupported bundle savings',()=>{
 const recipes=[recipe('1','Spinazie',['Spinazie (g)'])];
 const feed=source({stores:{AH:{deals:[
  offer('AH Spinazie kleinverpakking','groente-fruit',{original_price:1.99,loyalty_warning:true,multi_buy_quantity:3}),
  offer('AH Spinazie','groente-fruit',{valid_until:'2026-10-28'}),
  offer('AH Spinazie pastasaus','soepen-conserven-sauzen',{price:0.88}),
  offer('AH Spinazie','groente-fruit',{personal_offer:true})
 ]},Jumbo:{deals:[]},Lidl:{deals:[]}}});
 const result=L.build(recipes,feed,NOW);
 assert.equal(result.families.length,1);
 const card=result.families[0];
 assert.equal(card.offers.length,1);
 assert.equal(card.offers[0].loyalty,true);
 assert.equal(card.offers[0].multi_buy,3);
 assert.equal(card.offers[0].original_price,1.99);
 assert.equal('savings' in card.offers[0],false);
 assert.equal('total_recipe_price' in card.offers[0],false);
});
