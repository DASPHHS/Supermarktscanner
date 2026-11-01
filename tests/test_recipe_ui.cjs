const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const data=p=>JSON.parse(read(p));

async function open(t,priceOverride,hfreshOverride){
 const errors=[];
 const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(e.type!=='css-parsing')errors.push(e.message)});
 const dom=new JSDOM(read('hellofresh/index.html'),{url:'https://example.test/Supermarktscanner/hellofresh/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
 t.after(()=>dom.window.close());
 await new Promise(resolve=>dom.window.addEventListener('load',resolve,{once:true}));
 const w=dom.window;
 w.addEventListener('error',e=>errors.push(e.message));
 w.fetch=async raw=>{
  const u=new URL(raw,w.location.href),relative=u.pathname.replace(/^\/Supermarktscanner\//,'');
  if(priceOverride&&relative==='recipe_prices.json')return {ok:true,json:async()=>structuredClone(priceOverride)};
  if(hfreshOverride&&relative==='hellofresh/hfresh_matches.json')return {ok:true,json:async()=>structuredClone(hfreshOverride)};
  const p=path.join(root,relative);
  return fs.existsSync(p)?{ok:true,json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))}:{ok:false,status:404};
 };
 w.eval(read('hellofresh/recipe-logic.js'));w.eval(read('hellofresh/app.js'));
 await new Promise(resolve=>setImmediate(resolve));
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(errors,[],'application loads without runtime errors');
 return w;
}

test('real snapshot opens with priced recipes, visible norms and all three stores',async t=>{
 const w=await open(t),d=w.document;
 const ids=[...d.querySelectorAll('[id]')].map(x=>x.id);
 assert.equal(new Set(ids).size,ids.length,'no duplicate IDs between cards and card checkbox');
 assert.equal(d.querySelector('#source').value,'HelloFresh');
 assert.equal(d.querySelector('#sort').value,'offers');
 assert.equal(d.querySelector('#status').value,'');
 assert.ok(Number(d.querySelector('#priced').textContent)>0,'show usable indicative prices, not a zero-only catalog');
 const first=d.querySelector('.card');assert.match(first.querySelector('.money').textContent,/≈/);
 first.querySelector('button[data-id]').click();
 assert.ok(d.querySelector('#modal').classList.contains('open'));
 assert.match(d.querySelector('#dialog').textContent,/Zichtbare normgewichten en aannames/);
 assert.match(d.querySelector('#dialog').textContent,/Af te rekenen/);
 for(const s of ['AH','Jumbo','Lidl'])assert.match(d.querySelector('#dialog').textContent,new RegExp(s));
 assert.ok(d.querySelector('.norm-section li'));
 d.querySelector('#close').click();
 d.querySelector('#top').click();
 const expected=Math.min(10,Number(d.querySelector('#priced').textContent));
 assert.equal(d.querySelectorAll('.card').length,expected);
 assert.ok([...d.querySelectorAll('.card .money')].every(x=>x.textContent.includes('≈')));
});

test('card option actually changes the best store and recipe order in the UI',async t=>{
 const source=data('recipe_prices.json');
 const templates=[];
 for(const row of source.results){if(row.estimate?.eligible&&!templates.some(x=>x.recipe_id===row.recipe_id))templates.push(row);if(templates.length===2)break;}
 assert.equal(templates.length,2,'fixture requires two fully estimated source recipes');
 const change=(template,store,base,card)=>({...template,store,
  estimate:{...template.estimate,used_total_eur:base,per_person_eur:base/2},
  estimate_with_cards:{...template.estimate,used_total_eur:card,per_person_eur:card/2,cards_included:true}});
 const fixture={...source,fetched_at_utc:new Date().toISOString(),results:[
  change(templates[0],'AH',10,2),change(templates[0],'Jumbo',7,7),change(templates[1],'AH',6,6)]};
 const w=await open(t,fixture),d=w.document;
 const basis=d.querySelector('#cost-basis');basis.value='used';basis.dispatchEvent(new w.Event('change',{bubbles:true}));
 const sort=d.querySelector('#sort');sort.value='cheap';sort.dispatchEvent(new w.Event('change',{bubbles:true}));
 const firstId=()=>d.querySelector('.card button[data-id]').dataset.id;
 assert.equal(firstId(),templates[1].recipe_id);
 const cards=d.querySelector('#card-promotions');cards.checked=true;cards.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(firstId(),templates[0].recipe_id);
 assert.match(d.querySelector('.card .money').textContent,/AH/);
 cards.checked=false;cards.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(firstId(),templates[1].recipe_id);
});

test('cash comparison changes the displayed basket, selected store and recipe order',async t=>{
 const source=data('recipe_prices.json'),templates=[];
 for(const row of source.results){if(row.estimate?.eligible&&!templates.some(x=>x.recipe_id===row.recipe_id))templates.push(row);if(templates.length===2)break;}
 const row=(template,store,used,cash)=>({...template,store,estimate_with_cards:undefined,estimate:{...template.estimate,lines:[],used_total_eur:used,whole_packages_eur:cash,per_person_eur:used/2}});
 const fixture={...source,fetched_at_utc:new Date().toISOString(),results:[row(templates[0],'AH',2,30),row(templates[0],'Jumbo',3,4),row(templates[1],'AH',1,10)]};
 const w=await open(t,fixture),d=w.document;
 const basis=d.querySelector('#cost-basis');basis.value='used';basis.dispatchEvent(new w.Event('change',{bubbles:true}));
 const sort=d.querySelector('#sort');sort.value='cheap';sort.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(d.querySelector('.card button[data-id]').dataset.id,templates[1].recipe_id);
 basis.value='cash';basis.dispatchEvent(new w.Event('change',{bubbles:true}));
 const first=d.querySelector('.card');assert.equal(first.querySelector('button').dataset.id,templates[0].recipe_id);
 assert.match(first.querySelector('.money').textContent,/4,00/);
 assert.match(first.querySelector('.money').textContent,/hele verpakkingen.*Jumbo.*1,50/);
 assert.match(d.querySelector('#sort').selectedOptions[0].textContent,/kassabon/);
 first.querySelector('button').click();
 assert.match(d.querySelector('#dialog').textContent,/twee personen · Jumbo/);
 const pdf=d.querySelector('.pdf-download');if(pdf)assert.match(pdf.href,/raw.githubusercontent.com/);
});

test('HFresh links are supplementary, exact-title-only and never substitute recipe prices',async t=>{
 const recipe=data('recipes_extracted.json').recipes.find(r=>r.id&&r.title_extracted);
 assert.ok(recipe);
 const fixture={schema_version:1,recipe_links:{
  [recipe.id]:{match:'exact_title_only',url:'https://hfresh.info/nl-NL/recipes/example-123',total_time:35}
 }};
 const w=await open(t,undefined,fixture),d=w.document;
 const q=d.querySelector('#q');q.value=recipe.title_extracted;
 q.dispatchEvent(new w.Event('input',{bubbles:true}));
 const button=[...d.querySelectorAll('button[data-id]')].find(b=>b.dataset.id===String(recipe.id));
 assert.ok(button,'original local recipe stays searchable');
 const priceText=button.closest('.card').querySelector('.main-cost').textContent;
 button.click();
 const ref=d.querySelector('#dialog a[href="https://hfresh.info/nl-NL/recipes/example-123"]');
 assert.ok(ref,'validated source link is visible for an exact title match');
 assert.match(d.querySelector('#dialog').textContent,/geen controle van dezelfde variant, hoeveelheden of prijzen/i);
 assert.equal(button.closest('.card').querySelector('.main-cost').textContent,priceText);
 assert.match(d.querySelector('#hfresh-status').textContent,/1 recepttitels gekoppeld/);
});
