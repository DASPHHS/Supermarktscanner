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
console.log('Recipe offer matching: ' + (compatible.length + incompatible.length) + ' checks passed.');
