'use strict';
// Regression checks for recipe/offer matching.
// Run: node hellofresh/offer-matching.test.js
const assert = require('node:assert/strict');
const RecipeLogic = require('./recipe-logic.js');

const compatible = [
 ['Aardappelen (g)', 'Jumbo Aardappelen Kruimig/ Stamppot 600 g'],
 ['Aardappelen (g)', 'AH Vastkokende aardappelen'],
 ['Krieltjes (g)', 'AH Mini krieltjes'],
 ['Kikkererwten (g)', 'Hak Kikkererwten 380 g'],
 ['Mais (g)', 'Bonduelle Crispy maïs 2 mini\'s'],
 ['Tofu (g)', 'Vivera Stevige Tofu 280 g'],
 ['Spinazie (g)', 'AH Spinazie kleinverpakking'],
 ['Kipfilet (stuk(s))', 'AH Scharrel kipfilet 2 stuks'],
 ['Garnalen (g)', 'AH Roerbakgarnalen naturel'],
];

const incompatible = [
 ['Kipfilet (stuk(s))', 'Jumbo Scharrel Kipfilet 120 g'],
 ['Kipfilet (stuk(s))', 'Knorr Trattoria kipfilet romana'],
 ['Wortel (stuk(s))', 'Olvarit Wortel 4m+'],
 ['Wortel (stuk(s))', 'De Kleine Keuken Knijpmix mango wortel & haver 6m+'],
 ['Spinazie (g)', 'AH Terra Pureersoep broccoli spinazie'],
 ['Spinazie (g)', 'Vivera Vegetarische Spinazie Kaas Filet 2 Stuks 200 g'],
 ['[Plantaardige] roomboter (el)', 'Jumbo Bakkers Krakelingen met Roomboter 200 g'],
 ['Paprika (stuk(s))', 'Maza Hoemoes Paprika & Oregano'],
 ['Spinazie (g)', 'AH Borrelbrood feta spinazie'],
 ['Kikkererwten (g)', 'Unox Kikkererwten tomatensoep'],
 ['Kikkererwten (g)', 'Hak Kikkererwten & Lupine Mix 225 g'],
 ['Garnalen (g)', 'AH Garnalen knoflookmarinade'],
 ['Garnalen (g)', 'AH Roerbak zalm pangasius garnalen zeezout'],
 ['Garnalen (g)', 'Jumbo Salade Garnalen Cocktail 125 g'],
 ['Gember (g)', 'Klene Puur gember'],
 ['Gember (g)', 'Kesbeke Roots Vers gesneden gember sinaasappel'],
 ['Zalmfilet (stuk(s))', 'Fish Tales Atlantische gerookte zalm'],
 ['Ui (stuk(s))', 'Jumbo Gesneden Peen en Ui Hutspot 500 g'],
 ['Broccoli (g)', 'AH Bloemkool broccoli kleinverpakking'],
 ['Roomboter (g)', 'Becel Met roomboter smeerbaar'],
 ['Paprika (g)', 'DORITOS pure paprika'],
 ['Tomaat (stuk(s))', 'Unox Smaakfavoriet Soep In Zak Klassieke Tomaten'],
 ['Spaghetti (g)', 'Jumbo Pasta Pomodoro Verspakket 4 Personen'],
 ['Tonijn in water', 'Fish Tales Skipjack tonijn in olijfolie'],
];

for (const [ingredient, product] of compatible) {
 assert.equal(RecipeLogic.relevantOfferProduct(ingredient, product), true,
  'Valid single ingredient should match: ' + ingredient + ' / ' + product);
}
for (const [ingredient, product] of incompatible) {
 assert.equal(RecipeLogic.relevantOfferProduct(ingredient, product), false,
  'Non-equivalent product must not match: ' + ingredient + ' / ' + product);
}

const date = '2026-11-01';
const chickpeaAction = {
 name: 'Hak Kikkererwten 380 g',
 valid_from: '2026-10-28',
 valid_until: '2026-11-03',
};
const chickpeaLine = {
 ingredients: ['Kikkererwten (pak(ken))'],
 product: 'Hak Kikkererwten 380 g',
 action: chickpeaAction,
};
const wrongSpinachLine = {
 ingredients: ['Spinazie (g)'],
 product: 'Vivera Vegetarische Spinazie Kaas Filet 2 Stuks 200 g',
 action: {...chickpeaAction, name: 'Vivera Vegetarische Spinazie Kaas Filet 2 Stuks 200 g'},
};
const mismatchedNameLine = {
 ...chickpeaLine,
 action: {...chickpeaAction,name:'AH Scharrel Kipfilet 2 stuks'},
};
const staleLine = {...chickpeaLine,action:{...chickpeaAction,valid_until:'2026-10-31'}};
const estimate = lines => ({
 eligible:true,total_ingredients:lines.length,covered_ingredients:lines.length,
 missing:[],used_total_eur:5.40,whole_packages_eur:12.50,lines
});
assert.equal(RecipeLogic.validActionLine(chickpeaLine,date,false),true);
assert.equal(RecipeLogic.validActionLine(wrongSpinachLine,date,false),false);
assert.equal(RecipeLogic.validActionLine(mismatchedNameLine,date,false),false);
assert.equal(RecipeLogic.validActionLine(staleLine,date,false),false);
assert.equal(RecipeLogic.estimateFor({estimate:estimate([wrongSpinachLine])},false,date),null);
assert.equal(RecipeLogic.estimateFor({estimate:estimate([staleLine])},false,date),null);
assert.equal(RecipeLogic.appliedActionLines(estimate([chickpeaLine]),false,date).length,1);
assert.equal(RecipeLogic.appliedActionLines(estimate([wrongSpinachLine]),false,date).length,0);
assert.equal(RecipeLogic.appliedActionLines({...estimate([chickpeaLine]),missing:[{ingredient:'nog onbekend'}]},false,date).length,0);
const packAction={...chickpeaAction,multi_buy_quantity:2,multi_buy_price:1.49};
const onePack={...chickpeaLine,packages:1,action:packAction};
const twoPacks={...chickpeaLine,packages:2,action:packAction};
const noPackCount={...chickpeaLine,action:packAction};
assert.equal(RecipeLogic.validActionLine(onePack,date,false),false);
assert.equal(RecipeLogic.validActionLine(twoPacks,date,false),true);
assert.equal(RecipeLogic.validActionLine(noPackCount,date,false),false);
assert.equal(RecipeLogic.estimateFor({estimate:estimate([onePack])},false,date),null);
assert.equal(RecipeLogic.estimateFor({estimate:estimate([twoPacks])},false,date)!==null,true);

const baseEstimate={
 eligible:true,total_ingredients:1,covered_ingredients:1,missing:[],
 used_total_eur:0.54,whole_packages_eur:5.39,
 lines:[{ingredients:['Aardappelen (g)'],product:'AH Aardappelen iets kruimig',
 quantity:500,unit:'g',cash_cost:5.39,used_cost:0.54,packages:1,action:null}]
};
const alternative={
 name:'AH Kruimige aardappelen',quantity:'1 kg',price:1.49,original_price:2.49,
 promotion_type:'percentage',valid_from:'2026-10-28',valid_until:'2026-11-03'
};
const modeled=RecipeLogic.estimateWithOfferAlternatives(baseEstimate,[alternative],{store:'AH',today:date});
assert.equal(modeled.estimate.whole_packages_eur,1.49);
assert.equal(modeled.totalSavings,3.90);
assert.equal(modeled.changes[0].packages,1);
assert.equal(modeled.estimate.lines[0].scenario_offer,true);
const candidate=changes=>RecipeLogic.estimateWithOfferAlternatives(baseEstimate,[changes],{store:'AH',today:date}).changes.length;
assert.equal(candidate({...alternative,multi_buy_quantity:2,multi_buy_price:null}),0);
assert.equal(candidate({...alternative,name:'AH Pizza met aardappelen'}),0);
assert.equal(candidate({...alternative,quantity:'2 x 500 g'}),0);
assert.equal(candidate({...alternative,quantity:'1 liter'}),0);
assert.equal(candidate({...alternative,loyalty_warning:true}),0);
assert.equal(candidate({...alternative,original_price:null}),0);
assert.equal(candidate({...alternative,valid_until:'2026-10-31'}),0);
assert.equal(candidate({...alternative,price:6}),0);
assert.equal(candidate({...alternative,card_required:true}),0);
assert.equal(candidate({...alternative,price:0}),0);
assert.equal(RecipeLogic.estimateWithOfferAlternatives({...baseEstimate,eligible:false},[alternative],{today:date}).changes.length,0);
assert.equal(RecipeLogic.offerPackageAmount('600 GRAM').amount,600);
assert.equal(RecipeLogic.offerPackageAmount('0,5 kg').amount,500);
assert.equal(RecipeLogic.offerPackageAmount('1 liter').unit,'ml');
assert.equal(RecipeLogic.offerPackageAmount('2 x 500g'),null);
assert.equal(RecipeLogic.offerRankingTier(true,true,false),0);
assert.equal(RecipeLogic.offerRankingTier(true,false,true),1);
assert.equal(RecipeLogic.offerRankingTier(true,false,false),2);
assert.equal(RecipeLogic.offerRankingTier(false,true,true),3);
console.log('Recipe/offer checks: '+(compatible.length+incompatible.length+14+19)+' passed.');


