const {test}=require('node:test');
const assert=require('node:assert/strict');
const O=require('../hellofresh/official-recipes.js');

test('official links never allow fake HelloFresh domains or unexpected routes',()=>{
 const good='https://www.hellofresh.nl/recipes/schnitzel-met-knoflook-gemberrijst-6311cb3128a4b6cde308087a';
 assert.equal(O.safeUrl(good),good);
 for(const url of [
  'http://www.hellofresh.nl/recipes/foo-6311cb3128a4b6cde308087a',
  'https://www.hellofresh.nl.evil.test/recipes/foo-6311cb3128a4b6cde308087a',
  'https://www.hellofresh.nl/recipes',
  'https://www.hellofresh.nl/recipes/foo',
  'https://www.hellofresh.nl/recipes/foo-6311cb3128a4b6cde308087a?key=x',
  'https://admin@www.hellofresh.nl/recipes/foo-6311cb3128a4b6cde308087a'
 ])assert.equal(O.safeUrl(url),null,url);
});
test('same title may link to multiple *unverified* variants, never to Plated',()=>{
 const input={schema_version:1,candidates:{'Schnitzel met knoflook-gemberrijst':[
 {url:'https://www.hellofresh.nl/recipes/versie-a-6311cb3128a4b6cde308087a',subtitle:'met spitskool'},
 {url:'https://www.hellofresh.nl/recipes/versie-b-65f991ba473c4f42771d07c0',subtitle:'met wittekool'}
 ]}};
 const catalog=O.safeCatalog(input);
 const matches=O.candidatesFor({source:'HelloFresh',title_extracted:'SCHNITZEL MET KNOFLOOK-GEMBERRIJST'},catalog);
 assert.equal(matches.length,2);
 assert.ok(matches.every(x=>x.status==='variant_unconfirmed'));
 assert.deepEqual(O.candidatesFor({source:'Plated',title_extracted:'Schnitzel met knoflook-gemberrijst'},catalog),[]);
});
