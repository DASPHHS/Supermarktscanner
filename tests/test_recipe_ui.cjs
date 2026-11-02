const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const data=p=>JSON.parse(read(p));

async function open(t,priceOverride,hfreshOverride,weekdealsOverride){
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
  if(weekdealsOverride&&relative==='weekdeals_hellofresh.json')return {ok:true,json:async()=>structuredClone(weekdealsOverride)};
  const p=path.join(root,relative);
  return fs.existsSync(p)?{ok:true,json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))}:{ok:false,status:404};
 };
 w.eval(read('hellofresh/hfresh-links.js'));w.eval(read('hellofresh/recipe-logic.js'));w.eval(read('hellofresh/recipe-search.js'));w.eval(read('hellofresh/official-recipes.js'));w.eval(read('hellofresh/weekdeals-relevance.js'));w.eval(read('hellofresh/app.js'));
 await new Promise(resolve=>setImmediate(resolve));
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(errors,[],'application loads without runtime errors');
 return w;
}

test('real snapshot opens with priced recipes, visible norms and all three stores',async t=>{
 const w=await open(t),d=w.document;
 const ids=[...d.querySelectorAll('[id]')].map(x=>x.id);
 assert.equal(new Set(ids).size,ids.length,'no duplicate IDs between cards and card checkbox');
 assert.equal(d.querySelector('#source').value,'Alle');
 assert.match(d.querySelector('#library-index-status').textContent,/recepten.*HelloFresh.*Plated/);
 assert.equal(d.querySelector('#sort').value,'offers');
 assert.equal(d.querySelector('#status').value,'');
 assert.ok(Number(d.querySelector('#priced').textContent)>0,'show usable indicative prices, not a zero-only catalog');
 const first=d.querySelector('.card');assert.match(first.querySelector('.main-cost').textContent,/≈/);
 first.querySelector('button[data-id]').click();
 assert.ok(d.querySelector('#modal').classList.contains('open'));
 assert.match(d.querySelector('#dialog').textContent,/Zichtbare normgewichten en aannames/);
 assert.match(d.querySelector('#dialog').textContent,/Geschatte kassabon/);
 for(const s of ['AH','Jumbo','Lidl'])assert.match(d.querySelector('#dialog').textContent,new RegExp(s));
 assert.ok(d.querySelector('.norm-section li'));
 d.querySelector('#close').click();
 d.querySelector('#top').click();
 const expected=Math.min(10,Number(d.querySelector('#priced').textContent));
 assert.equal(d.querySelectorAll('.card').length,expected);
 assert.ok([...d.querySelectorAll('.card .main-cost')].every(x=>x.textContent.includes('≈')));
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
 assert.match(d.querySelector('.card .main-cost').textContent,/AH/);
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
 assert.match(first.querySelector('.main-cost').textContent,/4,00/);
 assert.match(first.querySelector('.main-cost').textContent,/Hele verpakkingen.*Jumbo.*1,50/);
 assert.match(d.querySelector('#sort').selectedOptions[0].textContent,/kassabon/);
 first.querySelector('button').click();
 assert.match(d.querySelector('#dialog').textContent,/twee personen · Jumbo/);
 const pdf=d.querySelector('.pdf-download');if(pdf)assert.match(pdf.href,/raw.githubusercontent.com/);
});

test('HFresh links can be connected, removed, imported and filtered without pricing mutations',async t=>{
 const recipe=data('recipes_extracted.json').recipes.find(r=>r.id&&r.title_extracted);
 assert.ok(recipe);
 const fixture={schema_version:1,recipe_links:{
  [recipe.id]:{match:'exact_title_only',url:'https://hfresh.info/nl-NL/recipes/example-123',total_time:35,headline:'Met andere groente'}
 }};
 const w=await open(t,undefined,fixture),d=w.document;
 const q=d.querySelector('#q');q.value=recipe.title_extracted;
 q.dispatchEvent(new w.Event('input',{bubbles:true}));
 const button=[...d.querySelectorAll('button[data-id]')].find(b=>b.dataset.id===String(recipe.id));
 assert.ok(button,'original recipe is searchable');
 const initialPrice=button.closest('.card').querySelector('.main-cost').textContent;
 assert.equal(button.closest('.card').querySelector('.hfresh-quick a').href,'https://www.hellofresh.nl/recipes');
 assert.ok([...button.closest('.card').querySelectorAll('.hfresh-quick a')].some(a=>a.href==='https://hfresh.info/nl-NL/recipes/example-123'));
 button.click();
 assert.equal(d.querySelector('.official-visit').href,'https://www.hellofresh.nl/recipes');
 assert.equal(d.querySelector('.hfresh-search').href,'https://hfresh.info/nl-NL?search='+encodeURIComponent(recipe.title_extracted));
 assert.equal(d.querySelector('.hfresh-visit').href,'https://hfresh.info/nl-NL/recipes/example-123');
 assert.match(d.querySelector('#dialog').textContent,/Dezelfde titel garandeert niet dezelfde receptvariant/);
 assert.match(d.querySelector('#dialog').textContent,/HFresh-ondertitel: Met andere groente/);
 const bad=d.querySelector('#hfresh-link-input');bad.value='https://hfresh.info.evil.test/nl-NL/recipes/x-9';
 d.querySelector('#hfresh-save').click();
 assert.match(d.querySelector('#hfresh-link-message').textContent,/Ongeldige/);
 assert.equal(w.localStorage.getItem('hfresh-local-links-v1'),null);
 const manual='https://hfresh.info/nl-NL/recipes/mijn-versie-654';
 d.querySelector('#hfresh-link-input').value=manual;
 d.querySelector('#hfresh-save').click();
 assert.equal(d.querySelector('.hfresh-visit').href,manual);
 assert.equal(JSON.parse(w.localStorage.getItem('hfresh-local-links-v1'))[recipe.id],manual);
 assert.match(d.querySelector('#hfresh-status').textContent,/1 automatische titelverwijzingen · 1 handmatig/);
 assert.equal(button.closest('.card').querySelector('.main-cost').textContent,initialPrice);
 const linkFilter=d.querySelector('#hfresh-link-filter');
 linkFilter.value='linked';linkFilter.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.ok([...d.querySelectorAll('.card')].some(x=>x.querySelector('[data-id]')?.dataset.id===String(recipe.id)));
 linkFilter.value='unlinked';linkFilter.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.ok(![...d.querySelectorAll('.card')].some(x=>x.querySelector('[data-id]')?.dataset.id===String(recipe.id)));
 linkFilter.value='all';linkFilter.dispatchEvent(new w.Event('change',{bubbles:true}));
 d.querySelector('#hfresh-remove').click();
 assert.equal(d.querySelector('.hfresh-visit').href,'https://hfresh.info/nl-NL/recipes/example-123','automatic link remains after local override removed');
 assert.equal(JSON.parse(w.localStorage.getItem('hfresh-local-links-v1'))[recipe.id],undefined);
 const fileInput=d.querySelector('#hfresh-import');
 Object.defineProperty(fileInput,'files',{configurable:true,value:[{text:async()=>JSON.stringify({schema_version:1,recipe_links:{
   [recipe.id]:manual,'not-our-id':'https://hfresh.info/nl-NL/recipes/another-555',
 }})}]});
 fileInput.dispatchEvent(new w.Event('change',{bubbles:true}));
 await new Promise(resolve=>setImmediate(resolve));
 assert.match(d.querySelector('#hfresh-import-status').textContent,/1 lokale/);
 assert.equal(JSON.parse(w.localStorage.getItem('hfresh-local-links-v1'))[recipe.id],manual);
 assert.equal(d.querySelector('#hfresh-status').textContent.includes('1 handmatig'),true);
 assert.equal(button.closest('.card').querySelector('.main-cost').textContent,initialPrice);
});

test('relevant Weekdeals panel filters real ingredient candidates and does not change prices',async t=>{
 const recipes=data('recipes_extracted.json').recipes;
 const match=recipes.find(r=>r.id&&r.title_extracted&&
   (r.ingredients_2p||r.ingredients_4p||[]).some(i=>/\baardappelen\b/i.test(i.ingredient||'')));
 assert.ok(match,'fixture requires at least one HelloFresh potato recipe');
 const today=new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Amsterdam'});
 const end=new Date(Date.now()+86400000).toLocaleDateString('sv-SE',{timeZone:'Europe/Amsterdam'});
 const f={schema_version:1,source_url:'https://dasphhs.github.io/specialedeals/weekdeals/',
  updated_at_utc:new Date(Date.now()-60000).toISOString(),as_of_date:today,
  coverage:{full_promotional_feed:true},stores:{
   AH:{deals:[{name:'AH Vastkokende aardappelen',product_id:'potato-1',price:1.99,category:'groente-fruit',
     quantity:'1 kg',valid_from:today,valid_until:end,product_url:'https://www.ah.nl/producten/product/123'},
    {name:'AH Bakaardappeltjes paprika en knoflook',product_id:'false-1',price:0.5,category:'groente-fruit',
     valid_from:today,valid_until:end}]},
   Jumbo:{deals:[]},Lidl:{deals:[]}}};
 const w=await open(t,undefined,undefined,f),d=w.document;
 assert.match(d.querySelector('#deal-relevance-status').textContent,/ingrediëntgroepen met mogelijke acties/);
 assert.ok(d.querySelector('.relevance-card'),'candidate cards render');
 assert.ok(d.querySelector('#deal-category-cards .deal-category-card'),'compact category cards render');
 assert.ok(d.querySelector('#deal-category-cards').textContent.includes('Groente & aardappelen'));
 assert.ok(d.querySelector('button[data-relevance-category="groente"]'));
 d.querySelector('button[data-relevance-category="groente"]').click();
 assert.match(d.querySelector('#count').textContent,/aanbiedingen: Groente & aardappelen/);
 d.querySelector('#deal-relevance-clear').click();
 assert.ok(d.querySelector('.relevance-card').textContent.includes('Aardappelen'));
 assert.ok(!d.querySelector('#deal-relevance-cards').textContent.includes('Bakaardappeltjes'));
 const first=d.querySelector('.card .main-cost').textContent;
 const family=[...d.querySelectorAll('button[data-relevance-family]')].find(x=>x.dataset.relevanceFamily==='aardappel');
 assert.ok(family,'potato ingredient has a recipe-navigation action');
 family.click();
 assert.match(d.querySelector('#count').textContent,/filter: Aardappelen/);
 assert.ok([...d.querySelectorAll('.card button[data-id]')].some(b=>b.dataset.id===String(match.id)));
 d.querySelector('#deal-relevance-clear').click();
 assert.ok(!d.querySelector('#count').textContent.includes('filter:'));
 assert.equal(d.querySelector('.card .main-cost').textContent,first,'price unchanged');
 const store=d.querySelector('#deal-relevance-store');store.value='Lidl';store.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.match(d.querySelector('#deal-relevance-cards').textContent,/Geen mogelijke ingrediëntacties/);
});

test('complete library searches both collections and supports ingredient-only queries',async t=>{
 const w=await open(t),d=w.document;
 assert.equal(d.querySelector('#source').value,'Alle');
 const text=d.querySelector('#library-index-status').textContent;
 assert.match(text,/\d+ recepten \(\d+ HelloFresh, \d+ Plated\)/);
 const total=Number(text.match(/^(\d+) recepten/)[1]);
 assert.ok(total>=700,'both collections are visible, rather than 225 HelloFresh only');
 const source=d.querySelector('#source');
 const q=d.querySelector('#q');
 source.value='Plated';source.dispatchEvent(new w.Event('change',{bubbles:true}));
 q.value='Chicken';q.dispatchEvent(new w.Event('input',{bubbles:true}));
 assert.ok(d.querySelectorAll('.card').length>0,'Plated records are searchable');
 const mode=d.querySelector('#search-mode');
 mode.value='ingredients';mode.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.ok(d.querySelector('#count').textContent.includes('getoond'),'ingredient-only filter responds');
 q.value='';q.dispatchEvent(new w.Event('input',{bubbles:true}));
 source.value='Alle';source.dispatchEvent(new w.Event('change',{bubbles:true}));
 const chip=d.querySelector('[data-ingredient-shortcut="spinazie"]');
 chip.click();
 assert.equal(d.querySelector('#q').value,'spinazie');
 assert.equal(mode.value,'ingredients');
 assert.ok(d.querySelectorAll('.card').length>0,'common ingredient shortcut yields matches');
});

test('official HelloFresh candidates are clearly unverified; source audit is optional on first publication',async t=>{
 const w=await open(t),d=w.document;
 assert.ok(d.querySelector('#source-audit-status'),'source audit status visible');
 const search=d.querySelector('#q');
 assert.ok(search,'existing recipe search remains accessible');
 const article=d.querySelector('.card button[data-id]');
 assert.ok(article);article.click();
 assert.match(d.querySelector('#dialog').textContent,/Controle van recept en ingrediënten/);
 assert.ok(d.querySelector('#dialog a[href$="source-audit.html"]'),'full audit list linked');
 assert.match(d.querySelector('#dialog').textContent,/broncontroleverslag.*ontbreekt|automatisch gecontroleerd|handmatige/i);
});

test('image-only HelloFresh source records are searchable but cannot claim a checkout price',async t=>{
 const w=await open(t),d=w.document;
 assert.match(d.querySelector('#scan-index-status').textContent,/60 voorlopige extra beeldkaartrecepten/);
 const count=Number(d.querySelector('#library-index-status').textContent.match(/^(\d+) recepten/)[1]);
 assert.ok(count>=740,'image-only import adds new discoverable recipes without deleting originals');
 const q=d.querySelector('#q');q.value='Zuurkoolpannetje';q.dispatchEvent(new w.Event('input',{bubbles:true}));
 const hits=[...d.querySelectorAll('.card')];
 assert.ok(hits.some(x=>x.textContent.includes('Zuurkoolpannetje')),'original scanned title searchable');
 const b=hits.find(x=>x.textContent.includes('Zuurkoolpannetje')).querySelector('button[data-id]');
 assert.ok(b);b.click();
 assert.match(d.querySelector('#dialog').textContent,/Extra beeldkaart uit jouw archief/);
 assert.match(d.querySelector('#dialog').textContent,/geen betrouwbare portiehoeveelheden/i);
 assert.match(d.querySelector('#dialog').textContent,/geen winkelprijs berekend/i);
 assert.ok(!d.querySelector('#dialog').textContent.includes('Handmatig bevestigd in de bronregistratie'));
});
