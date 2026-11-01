const {test}=require('node:test');
const assert=require('node:assert/strict');
const S=require('../hellofresh/recipe-search.js');
const rows=[
 {id:'hf-1',source:'HelloFresh',title_extracted:'Pasta met zalm'},
 {id:'pl-1',source:'Plated',title_extracted:'Chicken with spinach'},
 {id:'pl-2',source:'Plated',title_extracted:'Potatoes and beans'},
 {id:'pl-3',source:'Plated',title_extracted:'Unknown ingredients'}
];
const names={
 'hf-1':['Gerookte zalm','Spaghetti','Spinazie'],
 'pl-1':['Chicken breast','Spinach','Garlic'],
 'pl-2':['Potatoes','Carrots','Black beans'],
 'pl-3':[]
};
const idx=S.makeIndex(rows,r=>names[r.id]);
test('index keeps all recipes, counts missing ingredient extraction honestly',()=>{
 assert.deepEqual(S.stats(rows,idx),{total:4,ingredientSearchable:3,titleOnly:1,helloFresh:1,plated:3});
 assert.equal(idx.get('pl-3').ingredientCount,0);
});
test('ingredient search supports Dutch and English labels, accents and AND queries',()=>{
 assert.equal(S.findMatches('kip spinazie',idx.get('pl-1'),true),true);
 assert.equal(S.findMatches('aardappel wortel',idx.get('pl-2'),true),true);
 assert.equal(S.findMatches('zalm spaghetti',idx.get('hf-1'),true),true);
 assert.equal(S.findMatches('zalm aardappel',idx.get('hf-1'),true),false);
 assert.equal(S.findMatches('kip zalm',idx.get('pl-1'),true),false);
 assert.equal(S.findMatches('CHICKEN SPINACH',idx.get('pl-1'),true),true);
 assert.equal(S.findMatches('',idx.get('pl-3'),true),true);
});
test('title-only recipe remains findable by title but not invented ingredients',()=>{
 assert.equal(S.findMatches('unknown',idx.get('pl-3'),false),true);
 assert.equal(S.findMatches('unknown',idx.get('pl-3'),true),false);
 assert.equal(S.findMatches('spinazie',idx.get('pl-3'),true),false);
 assert.equal(S.findMatches('pasta',idx.get('hf-1'),true),false);
 assert.equal(S.findMatches('pasta',idx.get('hf-1'),false),true);
});
test('short term ui does not accidentally match unrelated words',()=>{
 const x=S.makeIndex([{id:'s',title_extracted:'Fruit',ingredients:['Fruitmix']}]);
 assert.equal(S.findMatches('ui',x.get('s'),false),false);
});
