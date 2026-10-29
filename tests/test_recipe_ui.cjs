const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const data=p=>JSON.parse(read(p));

async function open(t,priceOverride){
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
 assert.equal(d.querySelector('#sort').value,'cheap');
 assert.equal(d.querySelector('#status').value,'yes');
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
 const firstId=()=>d.querySelector('.card button[data-id]').dataset.id;
 assert.equal(firstId(),templates[1].recipe_id);
 const cards=d.querySelector('#card-promotions');cards.checked=true;cards.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(firstId(),templates[0].recipe_id);
 assert.match(d.querySelector('.card .money').textContent,/AH/);
 cards.checked=false;cards.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(firstId(),templates[1].recipe_id);
});
