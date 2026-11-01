/* HelloFresh Receptenstudio: independent data loads, visible failure states */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const eur=n=>new Intl.NumberFormat('nl-NL',{style:'currency',currency:'EUR'}).format(n);
const state={recipes:[],extra:[],prices:new Map(),deals:{},dealsMeta:{},offerCache:new Map(),priceDate:null,previews:{},estimates:{},health:{},previewsProgress:{},quality:{},nlCatalog:{},source:'HelloFresh',store:'Voordeligste',cards:false,basis:'cash',selectedId:null,kind:'alle',only:'all',sort:'offers',top:false,shown:36,loading:true};
const kinds={'alle':'Alles','vega':'Vega','kip':'Kip','vis':'Vis','vlees':'Vlees','onbekend':'Controleren'};
function ingredients(r){return Array.isArray(r.ingredients_4p)?r.ingredients_4p:[]}
function dutch(r){return r.source==='Plated' ? state.nlCatalog[r.source_identity||r.id.replace(/^plated-release-/,'')]||null : null}
function displayTitle(r){return dutch(r)?.title_nl||r.title_extracted}
function translatedIngredients(r){const nl=dutch(r);return nl?.ingredients_nl?.length?nl.ingredients_nl:null}
function displayIngredients(r){const nl=translatedIngredients(r);return nl?nl.map(i=>({name:i.name_nl,quantity:i.quantity_display_nl,original:i.original_name,confidence:i.translation_status,conversion:i.conversion_status})):(r.ingredients_2p||ingredients(r)).map(i=>({name:i.ingredient,quantity:r.ingredients_2p?i.quantity_2p_source:i.quantity_4p_source,original:i.ingredient,confidence:'source'}))}
function searchableText(r){return [r.title_extracted,displayTitle(r),...ingredients(r).map(i=>i.ingredient),...displayIngredients(r).map(i=>i.name+' '+(dutch(r)?.ingredients_nl||[]).map(x=>x.canonical_nl||'').join(' '))].join(' ')}

function protein(r){
 const title=r.title_extracted+' '+displayTitle(r);
 const labels=displayIngredients(r).map(i=>i.name);
 const kind=RecipeLogic.protein(title,labels);
 if(kind!=='onbekend')return kind;
 // Vegetarian compounds were mistakenly shown as 'onbekend' (e.g. veggiebowl, kikkererwtencurry).
 if(/\b(veggie\w*|vega\w*|kikkererwten\w*|vegetarisch\w*)\b/.test(norm(title))&&
   RecipeLogic.protein('',labels)==='onbekend')return 'vega';
 return estimateRecord(r)?.vegetarian_ingredients?'vega':kind;
}
function dish(r){let t=norm(displayTitle(r));if(/soep|ramen/.test(t))return 'Soep';if(/pasta|spaghetti|linguine|penne|tagliatelle|lasagne|orzo|orzotto|ravioli|gnocchi|macaroni|casarecce|fusilli|rigatoni/.test(t))return 'Pasta & orzo';if(/curry|dahl|daal|masala/.test(t))return 'Curry';if(/stamppot|hutspot|puree/.test(t))return 'Stamppot';if(/rijst|risotto|nasi|biryani|poke/.test(t))return 'Rijst & bowls';if(/noedel|bami|mie|udon|wok/.test(t))return 'Noedels & wok';if(/wrap|taco|tortilla|burrito|quesadilla|naan|platbrood|pizza/.test(t))return 'Wraps & pizza';if(/salade|couscous|bulgur|quinoa|bowl/.test(t))return 'Salade & granen';return 'Overige gerechten'}
function all(){const map=new Map();for(const r of state.recipes.concat(state.extra)){const key=(r.source||'HelloFresh')+'|'+norm(r.title_extracted);if(key&&!map.has(key))map.set(key,r)}return [...map.values()]}
function priceRecord(r){return state.store==='Voordeligste'?RecipeLogic.selectRecord(['AH','Jumbo','Lidl'].map(shop=>state.prices.get(shop+':'+r.id)),state.cards,state.basis):state.prices.get(state.store+':'+r.id)}
function estimateRecord(r){return RecipeLogic.estimateFor(priceRecord(r),state.cards)}
function completePrice(r){const e=estimateRecord(r);return RecipeLogic.rankingPrice(e,state.basis)===null?null:RecipeLogic.estimatePrice(e)}
function rankingPrice(r){return RecipeLogic.rankingPrice(estimateRecord(r),state.basis)}
function priceCoverage(r){const e=estimateRecord(r),total=Math.max(ingredients(r).length,displayIngredients(r).length,e?.total_ingredients||0);return e?{matched:e.covered_ingredients||0,missing:Math.max(e.missing.length,total-(e.covered_ingredients||0)),total,unknown:total===0,available:true,review:!r.table_repair}:{...RecipeLogic.coverage(total,null),review:true}}
function coverageText(r){const c=priceCoverage(r);return c.unknown?'Ingrediëntenlijst ontbreekt':c.matched+' / '+c.total+' ingrediënten gematcht · '+c.missing+' ontbrekend'+(!c.available?' · geen prijssnapshot':'')}
function pricedServings(r){return priceRecord(r)?.servings||4}
function estimatedCost(r){const p=priceRecord(r);if(!p||p.servings!==4)return null;const missing=p.missing||[];const base=Number(p.known_cost_eur)||0;let additional=0;for(const item of missing){const k=state.store+'|'+r.id+'|'+item.ingredient;const val=state.estimates[k];if(!Number.isFinite(val)||val<0)return null;additional+=val}return missing.length?base+additional:null}
function incomplete(r){return priceCoverage(r).matched}
function todayNL(){return new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Amsterdam'})}
function offerWords(r){return RecipeLogic.appliedActionLines(estimateRecord(r),state.cards).map(line=>line.action)}
// A product-name resemblance is only a lead, NEVER proof that the product fits or its promotion was priced.
function relatedIngredient(ingredient,product){
 return RecipeLogic.relevantOfferProduct(ingredient,product);
}
function possibleOffers(r,scope=state.store){
 const key=String(r.id)+'|'+scope+'|'+todayNL();
 if(state.offerCache.has(key))return state.offerCache.get(key);
 const names=[...new Set(displayIngredients(r).map(i=>i.name).filter(Boolean))],list=[],seen=new Set();
 for(const [shop,group] of Object.entries(state.deals||{})){
  if(scope!=='Voordeligste'&&scope!=='Alle'&&shop!==scope)continue;
  for(const d of group?.deals||[]){
   if(!RecipeLogic.activeOffer(d,todayNL())||d.personal_offer===true||d.card_required===true&&!state.cards)continue;
   const matching=names.find(name=>relatedIngredient(name,d.name));
   if(!matching)continue;
   const id=shop+'|'+(d.product_id||d.name);
   if(seen.has(id))continue;
   seen.add(id);list.push({shop,ingredient:matching,deal:d});
  }
 }
 const selectedStore=priceRecord(r)?.store||'';
 list.sort((a,b)=>(b.shop===selectedStore)-(a.shop===selectedStore)||
  a.shop.localeCompare(b.shop,'nl')||a.ingredient.localeCompare(b.ingredient,'nl'));
 state.offerCache.set(key,list);
 return list;
}
function offerPriceLabel(d){
 if(Number.isFinite(d.multi_buy_quantity)&&d.multi_buy_quantity>1){
  if(Number.isFinite(d.multi_buy_price))return d.multi_buy_quantity+' voor '+eur(d.multi_buy_price);
  return (Number.isFinite(d.price)?eur(d.price):'onbekend')+' p.st. bij '+d.multi_buy_quantity+' stuks (bundeltotaal niet bevestigd)';
 }
 return Number.isFinite(d.price)?eur(d.price)+' actieprijs':'Actieprijs onbekend';
}
function candidateOffers(r,scope=state.store){
 const applied=new Set(offerWords(r).map(a=>norm(a.name)));
 return possibleOffers(r,scope).filter(x=>!applied.has(norm(x.deal.name)));
}
function cardOfferBlock(r){
 const verified=offerWords(r),candidates=candidateOffers(r);
 const total=new Set(candidates.map(o=>norm(o.ingredient))).size;
 const hasPrice=completePrice(r)!==null;
 if(!verified.length&&!candidates.length)
  return '<div class="card-offers-empty">Geen passende actie voor losse ingrediënten gevonden</div>';
 let html='<div class="recipe-offers compact-offers"><strong class="offer-heading">Acties bij ingrediënten</strong>';
 if(verified.length)html+='<div class="offer-applied">'+verified.length+' actie(s) in deze raming verwerkt en op productnaam gecontroleerd</div>';
 if(candidates.length){
  const first=candidates[0],deal=first.deal,store=priceRecord(r)?.store;
  html+='<div class="offer-match-line"><span class="offer-status">Mogelijke productactie · niet verrekend</span><div><b>'+esc(first.ingredient)+'</b> → '+esc(deal.name)+'</div>'+
   '<small>'+esc(first.shop)+' · '+esc(offerPriceLabel(deal))+' · t/m '+esc(deal.valid_until)+(deal.loyalty_warning?' · leden-/appprijs controleren':'')+
   (store&&store!==first.shop?' · andere winkel dan de berekening':'')+'</small></div>';
  if(candidates.length>1)html+='<div class="offer-extra">+'+(candidates.length-1)+' andere productopties onder Prijs &amp; acties</div>';
 }
 if(!hasPrice)html+='<small class="offer-warning">Geen volledige kassabonraming: acties zijn niet doorgerekend.</small>';
 return html+'</div>';
}
function detailOfferBlock(r){
 const applied=offerWords(r),candidates=candidateOffers(r,'Alle');
 let html='<section class="detail-offers"><h3>Acties en productkeuzes</h3><p class="sub">De scanner toont alleen vergelijkbare losse ingrediënten als actieoptie. Deze aanbiedingen zijn niet automatisch doorgerekend. Winkelprijzen, verpakkingen en voorwaarden kunnen verschillen.</p>';
 if(applied.length){
  html+='<h4>In gekozen prijsraming verwerkt</h4><div class="deals">'+applied.map(x=>
   '<div class="deal"><b>'+esc(x.name||'Productactie')+'</b><small>'+esc(x.discount||'Actie')+' · t/m '+esc(x.valid_until||'onbekend')+'</small></div>'
  ).join('')+'</div>';
 }else html+='<p class="sub">Geen geldige, passend gematchte actie aantoonbaar verwerkt in de getoonde prijs.</p>';
 if(candidates.length){
  const selected=priceRecord(r)?.store||null;
  html+='<h4>Andere passende producten in de actiescan (nog niet verrekend)</h4><div class="deals">'+candidates.slice(0,12).map(o=>{
   const d=o.deal;const productLink=typeof d.product_url==='string'&&/^https:\/\//.test(d.product_url)?'<a target="_blank" rel="noopener noreferrer" href="'+esc(d.product_url)+'">Controleer het product</a>':'';
   return '<div class="deal"><b>'+esc(o.ingredient)+'</b><div>'+esc(d.name)+'</div>'+
    '<small>'+esc(o.shop)+' · '+esc(offerPriceLabel(d))+(Number.isFinite(d.original_price)?' · regulier '+eur(d.original_price):'')+(d.loyalty_warning?' · leden-/appprijs controleren':'')+
    ' · t/m '+esc(d.valid_until||'onbekend')+(selected&&o.shop!==selected?' · andere winkel':'')+'</small><div>'+productLink+'</div></div>';
  }).join('')+'</div>';
  if(candidates.length>12)html+='<p class="sub">+'+(candidates.length-12)+' andere opties niet getoond.</p>';
 }else html+='<p class="sub">Geen aanvullende passende productacties in de beperkte actiescan.</p>';
 return html+'</section>';
}
function offerSort(a,b){
 const aPrice=rankingPrice(a),bPrice=rankingPrice(b);
 // Never put a recipe without any full price above a fully priced recipe.
 const rank=r=>{
  const cost=rankingPrice(r),priced=cost!==null;
  const offers=possibleOffers(r),applied=offerWords(r).length>0,priceShop=priceRecord(r)?.store;
  if(priced&&applied)return 0;
  if(priced&&offers.some(x=>x.shop===priceShop))return 1;
  if(priced&&offers.length)return 2;
  if(priced)return 3;
  return offers.length?4:5;
 };
 const levelA=rank(a),levelB=rank(b);
 if(levelA!==levelB)return levelA-levelB;
 if(aPrice!==null&&bPrice!==null&&aPrice!==bPrice)return aPrice-bPrice;
 const aIngredients=new Set(possibleOffers(a).map(x=>norm(x.ingredient))).size;
 const bIngredients=new Set(possibleOffers(b).map(x=>norm(x.ingredient))).size;
 return bIngredients-aIngredients||displayTitle(a).localeCompare(displayTitle(b),'nl');
}
function options(){const kindBox=$('kinds'),storeBox=$('stores');if(!kindBox||!storeBox)return;kindBox.innerHTML=Object.entries(kinds).map(([v,n])=>'<button type="button" data-k="'+v+'" class="'+(v===state.kind?'active':'')+'">'+n+'</button>').join('');storeBox.innerHTML=['Voordeligste','Jumbo','AH','Lidl'].map(n=>'<button type="button" data-store="'+n+'" class="'+(n===state.store?'active':'')+'">'+(n==='Voordeligste'?'Beste raming':n)+'</button>').join('');kindBox.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{state.kind=b.dataset.k;state.shown=36;options();render()}));storeBox.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{state.store=b.dataset.store;options();render()}))}
function dishOptions(){const box=$('dish');const v=box.value;const allD=[...new Set(all().map(dish))].sort();box.innerHTML='<option value="">Alle gerechten</option>'+allD.map(d=>'<option>'+esc(d)+'</option>').join('');box.value=allD.includes(v)?v:''}
function updateBanners(){const scope=all().filter(r=>state.source==='Alle'||r.source===state.source),total=scope.length; $('total').textContent=total;$('priced').textContent=scope.filter(r=>completePrice(r)!==null).length;const f=$('feed');if(f&&state.priceDate){f.textContent='Schapprijssnapshot: '+state.priceDate.toLocaleDateString('nl-NL')+' · indicatieve ramingen voor twee personen.'}else if(f){f.textContent='Prijsfeed niet beschikbaar of verlopen. Recepten blijven zichtbaar.'}
const offers=$('offers-section');if(offers){
 const counts=Object.fromEntries(['AH','Jumbo','Lidl'].map(k=>
  [k,(state.deals[k]?.deals||[]).filter(d=>RecipeLogic.activeOffer(d,todayNL())).length]));
 const source=state.dealsMeta.source||'Geen actuele bron';
 const sourceDate=state.dealsMeta.updated_at_utc?new Date(state.dealsMeta.updated_at_utc).toLocaleString('nl-NL',{timeZone:'Europe/Amsterdam'}):'onbekend';
 const caveat=state.dealsMeta.coverage?.food_category_filtered?'Actieve producten uit voedselcategorieën; geen compleet supermarktassortiment.':'Terugvalbron: onvolledige aanbiedingsdekking of geen actuele bron.';
 offers.innerHTML='<h3>Weekdeals: AH, Jumbo en Lidl</h3><p class="sub"><b>AH '+counts.AH+' · Jumbo '+counts.Jumbo+' · Lidl '+counts.Lidl+'</b> productacties · '+esc(source)+' · gepubliceerd '+esc(sourceDate)+'.</p><p class="sub">'+esc(caveat)+' De scanner koppelt alleen vergelijkbare losse ingrediënten. Kortingen verlagen de receptprijs pas als een geschikt product, benodigde aantallen en de volledige kassabon zijn doorgerekend.</p>';
}
}

function renderHealth(){
 const el=$('progress-content');if(!el)return;
 const h=state.health,q=state.quality||{}, hf=state.previewsProgress.hellofresh||{},pl=state.previewsProgress.plated||{};
 const completed=Number(h.completed_members)||0,total=Number(h.pdf_members)||533;
 const last=h.updated_at_utc?new Date(h.updated_at_utc):null;
 const hours=last?(Date.now()-last.getTime())/3600000:null;
 const status=hours===null?'Importstatus nog niet beschikbaar':hours>2?'Laatste Plated-import meer dan twee uur geleden · geplande verwerking controleren':'Recent verwerkt';
 const percent=total?Math.min(100,100*completed/total):0;
 el.innerHTML='<div class="process-grid"><div class="process-item"><small>Plated bron-PDF’s</small><strong>'+completed+' / '+total+'</strong><div class="meter"><div style="width:'+percent.toFixed(1)+'%"></div></div><small>'+esc(h.remaining_members??'—')+' nog te verwerken</small></div><div class="process-item"><small>Originele HelloFresh-kaarten</small><strong>'+esc(hf.rendered??Object.keys(state.previews).filter(x=>!x.startsWith('plated-release-')).length)+' / '+esc(hf.recipes_total??225)+'</strong><small>Met bronpagina’s en PDF-download</small></div><div class="process-item"><small>Originele Plated-kaarten</small><strong>'+esc(pl.rendered??Object.keys(state.previews).filter(x=>x.startsWith('plated-release-')).length)+'</strong><small>Met bronpagina’s en PDF-download</small></div><div class="process-item"><small>Handmatig geverifieerde recepten</small><strong>'+all().filter(RecipeLogic.verified).length+' bevestigd</strong><small>OCR is niet hetzelfde als handmatige controle</small></div></div><p class="progress-note '+(hours>2?'stale':'')+'">'+esc(status)+(last?' · Laatste opgeslagen Plated-import: '+last.toLocaleString('nl-NL'):'')+'</p><p class="progress-note">Kwaliteitsrapport: '+esc(q.status||'nog niet beschikbaar')+' · '+esc(q.plated_recipes_without_ingredients??'—')+' zonder ingrediënten · '+esc(q.plated_recipes_with_unconfirmed_portions??'—')+' porties niet bevestigd · '+esc(q.plated_unmapped_ingredient_labels??'—')+' ingrediënten niet gekoppeld. <a href="../recipe_quality_audit.json" target="_blank" rel="noopener">Rapport bekijken</a></p><p><a href="https://github.com/DASPHHS/Supermarktscanner/actions/workflows/plated-release-import.yml" target="_blank" rel="noopener">Bekijk importlogboek op GitHub</a></p>';
}
function refreshHealth(){
 Promise.allSettled([json('../plated_release_progress.json'),json('./preview_manifest.json'),json('./plated_preview_manifest.json'),json('../recipe_quality_audit.json')]).then(([a,b,c,d])=>{
 if(a.status==='fulfilled')state.health=a.value;
 if(b.status==='fulfilled')state.previewsProgress.hellofresh=b.value.metadata||{};
 if(c.status==='fulfilled')state.previewsProgress.plated=c.value.metadata||{};
 if(d.status==='fulfilled')state.quality=d.value;
 renderHealth();
 });
}
function render(){if(!$('cards'))return;const q=norm($('q').value),d=$('dish').value,status=$('status').value;const full=all();let rows=full.filter(r=>(state.source==='Alle'||r.source===state.source)&& (state.kind==='alle'||protein(r)===state.kind)&&(!d||dish(r)===d)&&norm(searchableText(r)).includes(q)&&(!status||(status==='yes'?completePrice(r)!==null:completePrice(r)===null))&&(!$('offers-only')?.checked||possibleOffers(r).length>0||offerWords(r).length>0));
const order=$('sort').value;$('sort').querySelector('[value=cheap]').textContent=state.basis==='cash'?'Laagste kassabon eerst':'Laagste verbruikskosten eerst';rows.sort((a,b)=>{if(order==='cheap')return (completePrice(a)===null)-(completePrice(b)===null)||(rankingPrice(a)??Infinity)-(rankingPrice(b)??Infinity)||displayTitle(a).localeCompare(displayTitle(b),'nl');if(order==='leastmissing')return ((priceCoverage(a).unknown?Infinity:priceCoverage(a).missing)-(priceCoverage(b).unknown?Infinity:priceCoverage(b).missing))||a.title_extracted.localeCompare(b.title_extracted,'nl');if(order==='offers')return offerSort(a,b);if(order==='matches')return incomplete(b)-incomplete(a)||a.title_extracted.localeCompare(b.title_extracted,'nl');return a.title_extracted.localeCompare(b.title_extracted,'nl')});
if(state.top)rows=rows.filter(r=>completePrice(r)!==null).sort((a,b)=>rankingPrice(a)-rankingPrice(b)).slice(0,10);
const scope=full.filter(r=>state.source==='Alle'||r.source===state.source),covered=scope.filter(r=>completePrice(r)!==null).length,offersCount=rows.filter(r=>offerWords(r).length||possibleOffers(r).length).length;$('count').textContent=rows.length+' getoond · '+offersCount+' met mogelijke of verrekende actie · '+covered+' van '+scope.length+' met volledige raming · '+(state.store==='Voordeligste'?'laagste beschikbare raming per recept':state.store)+(state.basis==='cash'?' · kassabon gekozen producten':' · verbruikskosten')+(state.top?' · top 10':order==='offers'?' · verrekende acties → passend bij winkel → mogelijke acties elders → laagste kassabon':'');
$('top').textContent=state.top?'Alle recepten':'Top 10 goedkoopste';updateBanners();
const emoji={vega:'🥬',kip:'🍗',vis:'🐟',vlees:'🥘',onbekend:'🍽️'};
$('cards').innerHTML=rows.slice(0,state.top?10:state.shown).map(r=>{
 const k=protein(r),v=completePrice(r),est=estimateRecord(r),shop=priceRecord(r)?.store||state.store;
 const costLabel=v===null?'Prijs nog onvolledig':state.basis==='cash'?'Kassabon ≈ '+eur(est.whole_packages_eur):'Verbruik ≈ '+eur(v/2)+' p.p.';
 const costInfo=v===null?coverageText(r):state.basis==='cash'?'Hele verpakkingen voor 2 · '+shop+' · verbruik '+eur(v/2)+' p.p.':'Per persoon · '+shop+' · 2 porties';
 const priceClass=v===null?'not-priced':'priced';
 const meta=esc(r.source||'HelloFresh')+' · '+esc(k)+' · '+esc(r.source_file||'');
 const art=state.previews[r.id]?.front?'<img class="real-card-preview" loading="lazy" alt="Originele bronkaart van '+esc(displayTitle(r))+'" src="'+esc(state.previews[r.id].front)+'">':'<span>'+emoji[k]+'</span>';
 return '<article class="card"><div class="art '+k+'">'+art+'<span class="tag">'+esc(dish(r))+'</span></div>'+
 '<div class="content"><div class="meta">'+meta+'</div><h3>'+esc(displayTitle(r))+'</h3>'+
 '<div class="minor">'+esc(displayIngredients(r).slice(0,3).map(i=>i.name).join(' · ')||'Ingrediëntencontrole vereist')+'</div>'+
 '<div class="main-cost '+priceClass+'"><strong>'+costLabel+'</strong><small>'+esc(costInfo)+'</small></div>'+
 cardOfferBlock(r)+
 '<div class="foot"><button type="button" class="action" data-id="'+esc(r.id)+'">Prijs &amp; acties bekijken →</button></div></div></article>';
}).join('')||(state.loading?'<div class="empty">Recepten ophalen…</div>':'<div class="empty">'+(state.top?'Voor deze filters zijn nog geen volledige prijsramingen beschikbaar.':'Geen recepten gevonden. Pas de zoekfilters aan.')+'</div>');
$('more').style.display=!state.top&&rows.length>state.shown?'block':'none';$('cards').querySelectorAll('button[data-id]').forEach(b=>b.addEventListener('click',()=>details(b.dataset.id)))}
function details(id){
 const r=all().find(x=>String(x.id)===id);if(!r)return;
 state.selectedId=r.id;
 const p=priceRecord(r),e=estimateRecord(r),v=completePrice(r),card=state.previews[r.id];
 const shop=p?.store||state.store;
 const originalPdf=RecipeLogic.originalPdfUrl(card?.original_pdf);
 const fmt=n=>new Intl.NumberFormat('nl-NL',{maximumFractionDigits:2}).format(n);
 const url=u=>typeof u==='string'&&/^https?:\/\//i.test(u)?esc(u):null;
 const src=card?'<section class="source-pages"><h3>Originele '+esc(r.source||'HelloFresh')+'-receptkaart</h3><p class="sub">Dit zijn afbeeldingen van de echte PDF-pagina’s, dus geen overgeschreven OCR-tekst. Klik voor groot formaat of sla de afbeelding op.</p>'+(originalPdf?'<p><a class="pdf-download" href="'+esc(originalPdf)+'" target="_blank" rel="noopener" download="'+esc(r.id+'-origineel.pdf')+'">⬇ Download originele receptkaart (PDF)</a></p>':'<p class="sub">Een aparte PDF-download wordt nog gegenereerd.</p>')+'<div class="source-images">'+['front','ingredients'].filter(k=>card[k]).map(k=>'<a href="'+esc(card[k])+'" target="_blank" rel="noopener" download="'+esc(r.id+'-'+k+'.webp')+'"><img loading="lazy" src="'+esc(card[k])+'" alt="Originele '+(k==='front'?'receptvoorzijde':'ingrediëntenpagina')+'"><span>Bekijk / download '+(k==='front'?'voorzijde':'ingrediëntenblad')+' ↗</span></a>').join('')+'</div></section>':
 '<section class="source-pages"><h3>Originele kaart</h3><p class="sub">De originele PDF-weergave is voor deze kaart nog niet gegenereerd. Bron: '+esc(r.source_file||'onbekend')+', voorzijde p. '+esc(r.source_page_front||'?')+', ingrediënten p. '+esc(r.source_page_ingredients||'?')+'.</p></section>';
 const comparison=['AH','Jumbo','Lidl'].map(store=>{
  const entry=state.prices.get(store+':'+r.id),estimate=RecipeLogic.estimateFor(entry,state.cards),cost=RecipeLogic.estimatePrice(estimate);
  return '<tr><th>'+store+'</th><td>'+(cost!==null?'≈ '+eur(cost):'Onvolledig')+'</td><td>'+(cost!==null?eur(estimate.whole_packages_eur):'—')+'</td><td>'+(cost!==null?(estimate.actions_applied||0)+' acties toegepast':estimate?.missing?.length?'Ontbrekende prijscomponenten':'Geen raming beschikbaar')+'</td></tr>';
 }).join('');
 const total=v!==null?'<div class="estimate"><strong>Geschatte kassabon: '+eur(e.whole_packages_eur)+' voor 2 personen</strong><p>Hele verpakkingen, zonder eigen voorraad. Alleen gebruikte hoeveelheden: <b>'+eur(v)+' voor 2 porties ('+eur(v/2)+' p.p.)</b>. Resterende inhoud kan je later gebruiken. Dit is geen gegarandeerde filiaalprijs.</p></div>'+(Number.isFinite(e.norm_scenario_low_eur)?'<p class="sub">Normscenario: '+eur(e.norm_scenario_low_eur)+' tot '+eur(e.norm_scenario_high_eur)+' voor twee porties bij −25% / +25% normhoeveelheden. Dit is een gevoeligheidsberekening, geen gegarandeerde prijsmarge.</p>':'')+(e.actions_applied?'<p class="offer-indicator">'+e.actions_applied+' actie(s) verrekend. Voordeel op het verbruik van de gekozen actieproducten: '+eur(e.used_savings_same_products_eur)+'. Extra verpakkingen en restanten staan hieronder.</p>':'<p class="sub">In deze prijsraming is geen aanbieding verrekend. Mogelijke productacties in deze of andere winkels staan verderop, maar zijn nog niet doorgerekend.</p>'):'<p class="notice"><b>Nog geen volledige prijsraming.</b> Ontbrekende componenten krijgen geen nulprijs en dit recept komt niet in de prijsranglijst.</p>';
 const missing=(e?.missing||[]);
 const gaps=missing.length?'<h3>Nog ontbrekend</h3><ul>'+missing.map(m=>'<li><b>'+esc(m.ingredient)+'</b>: '+esc(m.reason)+'</li>').join('')+'</ul>':!e?'<p class="notice">Voor dit recept is nog geen ramingsrecord beschikbaar.</p>':'';
 const lines=e?.lines||[];
 const lineTable=lines.length?'<h3>Productkeuzes en kosten</h3><div class="price-table-wrap"><table class="price-table"><thead><tr><th>Ingrediënt en rekenhoeveelheid</th><th>Gekozen product</th><th>Verbruik</th><th>Hele verpakkingen</th></tr></thead><tbody>'+lines.map(x=>{
  const link=url(x.link),a=x.action;
  return '<tr><td>'+esc(x.ingredients.join(' / '))+'<small>'+(x.norm?'≈ ':'')+fmt(x.quantity)+' '+esc(x.unit)+'</small></td><td>'+(link?'<a href="'+link+'" target="_blank" rel="noopener">'+esc(x.product)+'</a>':esc(x.product))+(x.package_size?'<small>'+esc(x.package_size)+' · '+eur(x.package_price)+'</small>':'')+(x.package_conversion?'<small class="assumption-note">'+esc(x.package_conversion)+'</small>':'')+(x.price_proxy?'<small class="assumption-note">Prijsproxy; zie aannames</small>':'')+(a?'<small class="offer-indicator">'+esc(a.discount||'Actie')+' · '+(a.multi_buy_quantity?esc(a.multi_buy_quantity)+' voor '+eur(a.multi_buy_price):eur(a.price))+' · t/m '+esc(a.valid_until)+(a.card_required?' · klantenkaart nodig':'')+'</small>':'')+'</td><td>'+eur(x.used_cost)+'</td><td>'+eur(x.cash_cost)+(Number.isFinite(x.packages)?'<small>'+x.packages+' verpakking(en) · '+fmt(x.leftover)+' '+esc(x.unit)+' over</small>':'')+'</td></tr>';
 }).join('')+'</tbody></table></div><p class="sub">Regelbedragen zijn afgerond; de totaalraming wordt berekend uit onafgeronde kosten.</p>':'';
 const assumptions=(e?.assumptions||[]);
 const normRows=assumptions.map(a=>'<li><b>'+esc(a.ingredient)+'</b> → ≈ '+fmt(a.quantity)+' '+esc(a.unit)+'. '+esc(a.note)+(url(a.source)?' <a href="'+url(a.source)+'" target="_blank" rel="noopener">Bron normgewicht</a>':'')+'</li>').join('');
 const packNotes=lines.filter(x=>x.package_conversion).map(x=>'<li><b>'+esc(x.product)+'</b>: '+esc(x.package_conversion)+'</li>').join('');
 const norms='<section class="norm-section"><h3>Zichtbare normgewichten en aannames</h3>'+(normRows||packNotes?'<ul>'+normRows+packNotes+'</ul>':'<p>Geen normregel beschikbaar voor deze onvolledige raming.</p>')+'<p class="sub">Werkaannames zijn geen gemeten HelloFresh-verpakkingsgewichten. De productkeuzes en bronhoeveelheden blijven zichtbaar. Prijsproxy’s zijn kostenbenaderingen; de oorspronkelijke receptkeuze blijft leidend.</p></section>';
 const comparisonList=displayIngredients(r).map(i=>(String(i.quantity||'').trim()+' '+String(i.name||'').replace(/\\([^)]*\\)/g,'')).trim()).filter(Boolean);
 const checkjebonLink=comparisonList.length?'https://www.checkjebon.nl/#'+encodeURIComponent(comparisonList.join('\\n')):null;
 const outsidePriceCheck=checkjebonLink?'<section class="norm-section"><h3>Externe controle: Checkjebon</h3><p><a href="'+esc(checkjebonLink)+'" target="_blank" rel="noopener noreferrer">Vergelijk de ingrediëntenlijst bij AH en Jumbo in Checkjebon</a></p><p class="sub">Checkjebon gebruikt eigen producten en fuzzy matching. Controleer de juiste varianten en hoeveelheden; overgenomen prijzen zijn niet gevalideerd in deze receptprijs. Lidl wordt niet ondersteund door Checkjebon.</p></section>':'';
 const portions=r.ingredients_2p?2:4;
 $('dialog').innerHTML='<button type="button" class="close" id="close" aria-label="Sluit recept">×</button><div class="meta">'+esc(r.source||'HelloFresh')+' · '+esc(protein(r))+'</div><h2>'+esc(displayTitle(r))+'</h2><p class="quality-label">Indicatieve prijsraming · twee personen · '+esc(shop)+'</p>'+total+outsidePriceCheck+'<h3>Vergelijk de winkels</h3><div class="price-table-wrap"><table class="price-table"><thead><tr><th>Winkel</th><th>Verbruik, 2 porties</th><th>Gekozen verpakkingen</th><th>Status</th></tr></thead><tbody>'+comparison+'</tbody></table></div><p class="sub">Elke raming gebruikt producten uit één winkel. Het kassabedrag hoort bij de getoonde productkeuzes; er is geen voorraad verondersteld. Voordeelpakken verlagen de verbruikskosten alleen als je de rest ook gebruikt. Kaartacties: '+(state.cards?'ingeschakeld':'uitgeschakeld')+'.</p>'+detailOfferBlock(r)+gaps+lineTable+norms+'<h3>Bronhoeveelheden ('+portions+' porties)</h3><ul>'+displayIngredients(r).map(i=>'<li>'+esc(i.quantity)+' '+esc(i.name)+'</li>').join('')+'</ul>'+(!r.table_repair?'<p class="notice">Deze bronkolom doorstaat de automatische tabelcontrole nog niet. Er wordt geen totaalraming van gemaakt.</p>':'<p class="sub">Herstelde bronkolom; de oorspronkelijke kaart blijft leidend. Een prijsraming is geen handmatig gecertificeerde receptprijs.</p>')+src+'<p class="sub">Prijsnormen: '+esc(e?.policy_version||'nog niet beschikbaar')+'. Water, energie, bezorging en reiskosten vallen buiten deze vergelijking. Filiaalprijzen kunnen afwijken.</p>';
 $('modal').classList.add('open');
 $('close').onclick=()=>{$('modal').classList.remove('open');state.selectedId=null;};
}
function parseCSV(s){const rows=[],record=[];let cell='',quoted=false;for(let i=0;i<s.length;i++){let c=s[i];if(c==='"'){if(quoted&&s[i+1]==='"'){cell+='"';i++}else quoted=!quoted}else if(c===';'&&!quoted){record.push(cell);cell=''}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&s[i+1]==='\n')i++;record.push(cell);if(record.some(x=>x.trim()))rows.push(record.splice(0));cell=''}else cell+=c}record.push(cell);if(record.some(x=>x.trim()))rows.push(record);const head=(rows.shift()||[]).map(x=>x.trim().replace(/^\uFEFF/,''));return rows.map(r=>Object.fromEntries(head.map((h,i)=>[h,r[i]||''])))}
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error(url+': HTTP '+r.status);return r.json()}
function once(id,event,fn){$(id)?.addEventListener(event,fn)}
function init(){refreshHealth();setInterval(refreshHealth,5*60*1000);try{state.estimates=JSON.parse(localStorage.getItem('hf-local-price-estimates')||'{}')}catch(e){state.estimates={}};once('q','input',()=>{state.shown=36;render()});for(const id of ['dish','sort','status','source','cost-basis','offers-only'])once(id,'change',()=>{state.shown=36;if(id==='source')state.source=$('source').value;if(id==='cost-basis')state.basis=$('cost-basis').value;render()});once('more','click',()=>{state.shown+=36;render()});once('top','click',()=>{state.top=!state.top;render()});once('modal','click',e=>{if(e.target===$('modal'))$('modal').classList.remove('open')});document.addEventListener('keydown',e=>{if(e.key==='Escape')$('modal').classList.remove('open')});
once('card-promotions','change',()=>{state.cards=$('card-promotions').checked;state.offerCache.clear();render();if($('modal').classList.contains('open')&&state.selectedId)details(state.selectedId)});
once('file','change',async e=>{try{const rows=parseCSV(await e.target.files[0].text());if(!rows.length||!('titel_automatisch' in rows[0]))throw Error('CSV niet herkend');state.extra=rows.map((r,i)=>({id:'local-'+i,title_extracted:r.titel_automatisch,source:'HelloFresh',source_file:r.bron,source_page_ingredients:r.paginas,ingredients_4p:[]})).filter(r=>r.title_extracted);$('import-status').textContent=state.extra.length+' extra bronrecords geladen in deze browser.';dishOptions();render()}catch(err){$('import-status').textContent='Import mislukt: '+err.message}});
once('clear','click',()=>{state.extra=[];$('file').value='';$('import-status').textContent='Lokale import gewist';dishOptions();render()});options();dishOptions();render();
json('../recipes_extracted.json').then(d=>{if(!Array.isArray(d.recipes)||!d.recipes.length)throw Error('Geen recepten in bron');state.recipes=state.recipes.filter(x=>x.source==='Plated').concat(d.recipes.map(r=>({...r,source:'HelloFresh'})));state.loading=false;dishOptions();render()}).catch(err=>{state.loading=false;$('count').textContent='Receptendatabase niet geladen: '+err.message;render()});
function refreshOriginals(){Promise.allSettled([json('./preview_manifest.json'),json('./plated_preview_manifest.json')]).then(res=>{let previews={};for(const item of res){if(item.status==='fulfilled')Object.assign(previews,item.value.recipes||{})}state.previews=previews;render()})}refreshOriginals();
setInterval(refreshOriginals,5*60*1000);
function refreshPrices(){return json('../recipe_prices.json').then(d=>{const at=new Date(d.fetched_at_utc);if(Date.now()-at.getTime()>=0&&Date.now()-at.getTime()<3*86400000){state.priceDate=at;state.prices=new Map((d.results||[]).map(r=>[r.store+':'+r.recipe_id,r]));state.offerCache.clear()}else{state.priceDate=null;state.prices.clear();state.offerCache.clear()}render()}).catch(()=>{if(state.priceDate&&Date.now()-state.priceDate.getTime()>=3*86400000){state.priceDate=null;state.prices.clear();state.offerCache.clear()}render()})}
refreshPrices();setInterval(refreshPrices,10*60*1000);
json('../plated_nl_catalog.json').then(d=>{state.nlCatalog=Object.fromEntries((d.recipes||[]).map(x=>[x.source_identity||x.id,x]));render()}).catch(()=>{});
function refreshDeals(){
 return json('../weekdeals_hellofresh.json').then(d=>{
  const age=Date.now()-new Date(d.updated_at_utc).getTime();
  const good=d.schema_version===1&&d.coverage?.full_promotional_feed===true&&age>=0&&age<48*3600000&&
   ['AH','Jumbo','Lidl'].every(k=>Array.isArray(d.stores?.[k]?.deals));
  if(!good)throw Error('Weekdeals-feed onvolledig of verouderd');
  state.deals=d.stores;
  state.dealsMeta={source:d.source,updated_at_utc:d.updated_at_utc,coverage:d.coverage};
  state.offerCache.clear();render();
 }).catch(()=>json('../market_deals.json').then(d=>{
   const age=Date.now()-new Date(d.updated_at_utc).getTime();
   state.deals=age>=0&&age<48*3600000?d.stores||{}:{};
   state.dealsMeta={source:'Beperkte PrijsProfeet-terugvalbron',updated_at_utc:d.updated_at_utc,coverage:{food_category_filtered:false}};
   state.offerCache.clear();render();
 }).catch(()=>{state.deals={};state.dealsMeta={source:'Geen actuele acties beschikbaar'};state.offerCache.clear();render()}));
}
refreshDeals();
function refreshPlated(){json('../plated_release_review_queue.json').then(d=>{const records=(d.recipes||[]).map((r,i)=>({...r,source:'Plated',id:'plated-release-'+(r.source_identity||i)}));state.recipes=state.recipes.filter(x=>x.source!=='Plated').concat(records);const el=$('plated-summary');if(el)el.textContent=records.length+' Plated-receptkaarten uit Marc\'s archief beschikbaar (voorlopige OCR, niet prijsgeldig).';dishOptions();render()}).catch(()=>{const el=$('plated-summary');if(el)el.textContent='Plated-import is nog niet bereikbaar. HelloFresh blijft beschikbaar.'})}
refreshPlated();
setInterval(refreshPlated,5*60*1000);
setInterval(refreshDeals,10*60*1000);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
