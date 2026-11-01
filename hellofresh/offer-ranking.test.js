'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const RecipeLogic = require('./recipe-logic.js');

const code = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
const entry = "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();";
assert.ok(code.includes(entry), 'Frontend test access marker not found');
const testCode = code.replace(entry,
 'return {state,selectedStoreOption,storeOption,rankingPrice,offerSort,offerWords,resetOfferCaches};');
const app = new Function('RecipeLogic', 'return ' + testCode.slice(testCode.indexOf('(()=>')))(RecipeLogic);

const today = new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Amsterdam'});
const recipe = id => ({
 id,source:'HelloFresh',title_extracted:'Recept '+id,
 ingredients_2p:[{ingredient:'Aardappelen (g)',quantity_2p_source:'500 g'}],
 ingredients_4p:[{ingredient:'Aardappelen (g)',quantity_4p_source:'1 kg'}],
});
const estimate = (store,checkout) => ({
 recipe_id:'',store,servings:4,
 estimate:{
  eligible:true,total_ingredients:1,covered_ingredients:1,missing:[],
  whole_packages_eur:checkout,used_total_eur:checkout/2,
  lines:[{
   ingredients:['Aardappelen (g)'],family:'aardappelen',
   product:store+' aardappelen',quantity:500,unit:'g',
   package_size:'5 kg',package_price:checkout,packages:1,
   cash_cost:checkout,used_cost:checkout/2,leftover:4500,
   action:null,price_proxy:false,
  }]
 }
});
const offer=(store,name,price,originalPrice)=>({
 name,price,original_price:originalPrice,quantity:'1 kg',
 valid_from:today,valid_until:today,promotion_type:'percentage',
 product_url:'https://example.com/test',card_required:false,personal_offer:false,
});
const one=recipe('action'),two=recipe('noaction'),third=recipe('elsewhere');
const noAction=estimate('AH',2.50);
noAction.estimate.lines[0].ingredients=['Wortel (g)'];
app.state.prices=new Map([
 ['AH:action',estimate('AH',5.39)],
 ['Jumbo:action',estimate('Jumbo',4.90)],
 ['AH:noaction',noAction],
 ['AH:elsewhere',estimate('AH',4.20)]
]);
app.state.deals={
 AH:{deals:[offer('AH','AH Kruimige aardappelen',1.49,2.49)]},
 Jumbo:{deals:[offer('Jumbo','Jumbo Kruimige aardappelen',2.50,3.90)]},
 Lidl:{deals:[]}
};
let result=app.selectedStoreOption(one);
assert.equal(result.shop,'AH');
assert.equal(result.price,1.49);
assert.equal(result.savings,3.90);
assert.equal(app.offerWords(one).length,1);
assert.ok(app.offerSort(one,two)<0,'An applied action ranks first');
assert.equal(app.offerWords(two).length,0);

// Another retailer's action must not affect AH's checkout.
app.state.deals.AH.deals=[];
app.resetOfferCaches();
result=app.selectedStoreOption(third);
assert.equal(result.shop,'AH');
assert.equal(result.price,4.20);
assert.equal(result.savings,0);
assert.equal(app.offerWords(third).length,0);

// Recomputing a changed offers feed must remove the cached cheaper scenario.
result=app.selectedStoreOption(one);
assert.equal(result.shop,'Jumbo');
assert.equal(result.price,2.50);
app.state.deals.Jumbo.deals=[];
app.resetOfferCaches();
result=app.selectedStoreOption(one);
assert.equal(result.shop,'Jumbo');
assert.equal(result.price,4.90);
assert.equal(result.savings,0);

// With no complete pricing in a store, a promotion cannot yield a checkout.
const incomplete=recipe('unpriced');
app.state.prices.set('AH:unpriced',{
 store:'AH',estimate:{eligible:false,covered_ingredients:0,total_ingredients:1,
 missing:[{ingredient:'Aardappelen (g)'}],lines:[]}
});
app.resetOfferCaches();
assert.equal(app.rankingPrice(incomplete),null);
assert.equal(app.offerWords(incomplete).length,0);
assert.ok(app.offerSort(two,incomplete)<0,'Incomplete estimates sort last');
console.log('Frontend offer ranking: 17 invariants passed.');
