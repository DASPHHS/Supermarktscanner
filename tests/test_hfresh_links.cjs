const {test}=require('node:test');
const assert=require('node:assert/strict');
const L=require('../hellofresh/hfresh-links.js');
test('validates HFresh recipe URLs and rejects lookalikes, tokens and other regions',()=>{
 const good='https://hfresh.info/nl-NL/recipes/biefstuk-met-groenten-12345';
 assert.equal(L.safeUrl(good),good);
 assert.equal(L.safeUrl('https://www.hfresh.info/nl-NL/recipes/groentesoep-123/'), 'https://www.hfresh.info/nl-NL/recipes/groentesoep-123/');
 for(const url of [
  'http://hfresh.info/nl-NL/recipes/x-12',
  'https://hfresh.info.evil.test/nl-NL/recipes/x-12',
  'https://person@hfresh.info/nl-NL/recipes/x-12',
  'https://hfresh.info:8888/nl-NL/recipes/x-12',
  'https://hfresh.info/nl-NL/recipes/x-12?token=secret',
  'https://hfresh.info/de-DE/recipes/x-12',
  'https://hfresh.info/nl-NL/shopping-list',
  'javascript:alert(1)',null
 ])assert.equal(L.safeUrl(url),null,String(url));
});
test('manual mapping overrides only supplemental automatic reference',()=>{
 const r={id:'recipe-a',source:'HelloFresh',title_extracted:'Soep'},
  automatic=L.safeSnapshot({schema_version:1,recipe_links:{'recipe-a':{
   match:'exact_title_only',url:'https://hfresh.info/nl-NL/recipes/soep-123',total_time:45
  },'bad-id':{match:'exact_title_only',url:'https://evil.com/nl-NL/recipes/x-1'}}}),
  manual=L.cleanManual({'recipe-a':'https://hfresh.info/nl-NL/recipes/soep-handmatig-789'});
 assert.equal(Object.keys(automatic).length,1);
 assert.equal(L.linkFor(r,automatic,manual).origin,'manual');
 assert.equal(L.linkFor(r,automatic,manual).url,manual['recipe-a']);
 assert.equal(L.linkFor(r,automatic,{}).origin,'api');
 assert.equal(L.linkFor({...r,source:'Plated'},automatic,manual),null);
});
test('export/import only contains validated links, not ingredients or prices',()=>{
 const unsafe={'abc':'https://hfresh.info/nl-NL/recipes/soep-3',
               'xyz':'https://evil.example/nl-NL/recipes/a-3','__proto__': 'https://hfresh.info/nl-NL/recipes/evil-1'};
 const json=L.exportManual(unsafe);
 assert.deepEqual(Object.keys(json.recipe_links),['abc']);
 assert.equal(json.schema_version,1);
 assert.equal(JSON.stringify(json).includes('price_eur'),false);
 assert.equal(L.linkFor({id:'missing',source:'HelloFresh'}, {}, json.recipe_links),null);
});

test('public HFresh search link pre-fills the recipe title without an API key',()=>{
 const url=L.searchUrl('Kipfilet in mosterdroomsaus & courgette');
 assert.equal(url,'https://hfresh.info/nl-NL?search=Kipfilet%20in%20mosterdroomsaus%20%26%20courgette');
 assert.equal(L.searchUrl(''),'https://hfresh.info/nl-NL');
});
