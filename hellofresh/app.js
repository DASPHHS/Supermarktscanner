/* HelloFresh Receptenstudio: independent data loads, visible failure states */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const eur=n=>new Intl.NumberFormat('nl-NL',{style:'currency',currency:'EUR'}).format(n);
const state={recipes:[],extra:[],prices:new Map(),deals:{},dealsMeta:{},offerCache:new Map(),ingredientDealCache:new Map(),storeCache:new Map(),priceDate:null,previews:{},estimates:{},health:{},previewsProgress:{},quality:{},nlCatalog:{},hfreshMatches:{},hfreshLocal:{},source:'HelloFresh',store:'Voordeligste',cards:false,basis:'cash',selectedId:null,kind:'alle',only:'all',sort:'offers',top:false,shown:36,loading:true};
const kinds={'alle':'Alles','vega':'Vega','kip':'Kip','vis':'Vis','vlees':'Vlees','onbekend':'Controleren'};
function ingredients(r){return Array.isArray(r.ingredients_4p)?r.ingredients_4p:[]}
function dutch(r){return r.source==='Plated' ? state.nlCatalog[r.source_identity||r.id.replace(/^plated-release-/,'')]||null : null}
function displayTitle(r){return dutch(r)?.title_nl||r.title_extracted}
function hfreshLink(r){
 return HFreshLinks.linkFor(r,state.hfreshMatches,state.hfreshLocal);
}
function refreshHFreshStatus(){
 const el=$('hfresh-status');if(!el)return;
 const local=Object.keys(HFreshLinks.cleanManual(state.hfreshLocal)).length;
 const automatic=Object.keys(state.hfreshMatches).length;
 el.textContent=automatic+' automatische titelverwijzingen · '+local+
  ' handmatig in deze browser. Geen van deze koppelingen verifieert porties, ingrediënten of prijzen.';
}
function hfreshDetail(r){
 if(r.source!=='HelloFresh')return '';
 const ext=hfreshLink(r),local=HFreshLinks.safeUrl(state.hfreshLocal[String(r.id)])||'';
 const source=ext?.origin==='manual'?'Handmatig gekoppeld in deze browser':'Automatisch gekoppeld op titel';
 return '<section class="norm-section" id="hfresh-detail"><h3>HFresh-receptenkoppeling</h3>'+
 (ext?'<p><a class="hfresh-visit" href="'+esc(ext.url)+'" target="_blank" rel="noopener noreferrer">Open de gekoppelde HFresh-receptpagina</a>'+
 (Number.isInteger(ext.total_time)?' · '+ext.total_time+' min volgens HFresh':'')+'</p><p class="sub">'+source+'. Dezelfde titel garandeert niet dezelfde receptvariant. Vergelijk ingrediënten en bijgerechten met de originele PDF.</p>'+(ext.headline?'<p class="sub">HFresh-ondertitel: '+esc(ext.headline)+'</p>':''):
 '<p class="sub">Voor dit recept is nog geen HFresh-pagina gekoppeld. Dit verandert niets aan de prijsberekening.</p>')+
 '<p><a class="hfresh-search" href="'+esc(HFreshLinks.searchUrl(displayTitle(r)))+'" target="_blank" rel="noopener noreferrer">Zoek dit recept direct in HFresh</a></p>'+
 '<label for="hfresh-recipe-title">Zoektekst</label><input id="hfresh-recipe-title" class="field" readonly value="'+esc(displayTitle(r))+'">'+
 '<div class="hfresh-actions"><button id="hfresh-copy" type="button" class="action">Kopieer recepttitel</button></div>'+ 
 '<label for="hfresh-link-input">Plak hier de URL van de gevonden HFresh-receptpagina</label>'+
 '<input id="hfresh-link-input" class="field" type="url" autocomplete="off" placeholder="https://hfresh.info/nl-NL/recipes/receptnaam-123" value="'+esc(local)+'">'+
 '<div class="hfresh-actions"><button id="hfresh-save" type="button" class="action">Bewaar lokale koppeling</button>'+
 (local?'<button id="hfresh-remove" type="button" class="action">Verwijder lokale koppeling</button>':'')+'</div>'+
 '<p class="sub" id="hfresh-link-message" role="status">Alleen links op het domein hfresh.info met een Nederlandse receptpagina zijn toegestaan. Lokale koppelingen zijn geen verificatie.</p>'+
 '</section>';
}
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
// Cache per-ingredient checks across recipes; store optimization never calls priceRecord.
function matchesForIngredient(ingredient,shop){
 const key=shop+'|'+norm(ingredient)+'|'+state.cards+'|'+todayNL();
 if(state.ingredientDealCache.has(key))return state.ingredientDealCache.get(key);
 const available=(state.deals[shop]?.deals||[]).filter(d=>
  RecipeLogic.activeOffer(d,todayNL())&&d.personal_offer!==true&&
  (d.card_required!==true||state.cards)&&relatedIngredient(ingredient,d.name));
 state.ingredientDealCache.set(key,available);
 return available;
}
function storeOption(r,shop){
 const key=String(r.id)+'|'+shop+'|'+state.cards+'|'+state.basis;
 if(state.storeCache.has(key))return state.storeCache.get(key);
 const record=state.prices.get(shop+':'+r.id)||null;
 const baseline=RecipeLogic.estimateFor(record,state.cards);
 const modeled=RecipeLogic.estimateWithOfferAlternatives(baseline,[],{
  store:shop,cards:state.cards,today:todayNL(),
  matches:ingredient=>matchesForIngredient(ingredient,shop)
 });
 const result={record,shop,estimate:modeled.estimate,
  price:RecipeLogic.rankingPrice(modeled.estimate,state.basis),
  changes:modeled.changes,savings:modeled.totalSavings};
 state.storeCache.set(key,result);
 return result;
}
function selectedStoreOption(r){
 if(state.store!=='Voordeligste')return storeOption(r,state.store);
 const options=['AH','Jumbo','Lidl'].map(shop=>storeOption(r,shop));
 const valid=options.filter(x=>x.price!==null);
 if(valid.length)return valid.sort((a,b)=>a.price-b.price||a.shop.localeCompare(b.shop,'nl'))[0];
 return options.sort((a,b)=>(b.estimate?.covered_ingredients||0)-(a.estimate?.covered_ingredients||0))[0];
}
function priceRecord(r){return selectedStoreOption(r).record}
function estimateRecord(r){return selectedStoreOption(r).estimate}
function resetOfferCaches(){
 state.offerCache.clear();state.ingredientDealCache.clear();state.storeCache.clear();
}
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
 const key=String(r.id)+'|'+scope+'|'+todayNL()+'|'+state.cards;
 if(state.offerCache.has(key))return state.offerCache.get(key);
 const names=[...new Set(displayIngredients(r).map(i=>i.name).filter(Boolean))],list=[],seen=new Set();
 for(const shop of ['AH','Jumbo','Lidl']){
  if(scope!=='Voordeligste'&&scope!=='Alle'&&shop!==scope)continue;
  for(const ingredient of names){
   for(const d of matchesForIngredient(ingredient,shop)){
    const id=shop+'|'+(d.product_id||d.name);
    if(seen.has(id))continue;
    seen.add(id);list.push({shop,ingredient,deal:d});
   }
  }
 }
 const selectedShop=priceRecord(r)?.store||'';
 list.sort((a,b)=>(b.shop===selectedShop)-(a.shop===selectedShop)||
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
 const applied=offerWords(r),price=completePrice(r),selected=selectedStoreOption(r);
 const otherLeads=candidateOffers(r),sameShop=otherLeads.filter(x=>x.shop===selected.shop);
 const first=sameShop[0];
 const scenario=selected.changes.length>0;
 if(!applied.length&&!sameShop.length)
  return '<div class="card-offers-empty">'+
   (otherLeads.length?'Andere supermarkt: '+otherLeads.length+' mogelijke acties, niet in deze kassabon.':'Geen passende doorgerekende actie in deze winkel.')+'</div>';
 let html='<div class="recipe-offers compact-offers"><strong class="offer-heading">Aanbiedingen bij dit gerecht</strong>';
 if(scenario)html+='<div class="offer-applied">'+selected.changes.length+
  (selected.changes.length===1?' actie-alternatief doorgerekend':' actie-alternatieven doorgerekend')+
  ' · geschat kassabonverschil '+eur(selected.savings)+
  ' (niet onafhankelijk gecontroleerd)</div>'+
  selected.changes.slice(0,1).map(x=>'<div class="offer-match-line"><b>'+esc(x.ingredients.join(' / '))+
   '</b> → '+esc(x.to)+'<small>'+esc(x.store)+' · '+x.packages+
   ' verpakking(en) · samen '+eur(x.offerCash)+' i.p.v. '+eur(x.regularCash)+'</small></div>').join('');
 else if(applied.length)html+='<div class="offer-applied">'+applied.length+' bestaande actie(s) meegerekend in prijsraming</div>';
 if(first)html+='<div class="offer-match-line"><span class="offer-status">Mogelijke actie · niet meegerekend</span>'+
   '<b>'+esc(first.ingredient)+'</b> → '+esc(first.deal.name)+
   '<small>'+esc(first.shop)+' · '+esc(offerPriceLabel(first.deal))+' · t/m '+esc(first.deal.valid_until)+'</small></div>';
 if(otherLeads.length>sameShop.length)html+='<div class="offer-extra">'+
  (otherLeads.length-sameShop.length)+' aanvullende productacties in andere winkels (niet in dit bedrag).</div>';
 if(price===null)html+='<small class="offer-warning">Geen volledige kassabonraming; geen besparing geclaimd.</small>';
 return html+'</div>';
}
function detailOfferBlock(r){
 const applied=offerWords(r),candidates=candidateOffers(r,'Alle'),scenario=selectedStoreOption(r);
 let html='<section class="detail-offers"><h3>Acties en productkeuzes</h3><p class="sub">De scanner toont alleen vergelijkbare losse ingrediënten als actieoptie. Deze aanbiedingen zijn niet automatisch doorgerekend. Winkelprijzen, verpakkingen en voorwaarden kunnen verschillen.</p>';
 if(scenario.changes.length){html+='<h4>Doorgerekend alternatief voor gekozen winkel ('+esc(scenario.shop)+')</h4><p class="sub">Indicatief scenario, niet handmatig geverifieerd. Het lagere kassabedrag kan ook door een kleinere verpakking komen, niet alleen door de actie.</p><div class="deals">'+scenario.changes.map(x=>'<div class="deal"><b>'+esc(x.ingredients.join(' / '))+'</b><div>'+esc(x.from)+' → '+esc(x.to)+'</div><small>'+x.packages+' verpakking(en) · oorspronkelijk '+eur(x.regularCash)+' · alternatief '+eur(x.offerCash)+' · verschil '+eur(x.saving)+'</small></div>').join('')+'</div>'}
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
 const optA=selectedStoreOption(a),optB=selectedStoreOption(b);
 const appliedA=optA.price!==null&&offerWords(a).length>0;
 const appliedB=optB.price!==null&&offerWords(b).length>0;
 const tierA=RecipeLogic.offerRankingTier(optA.price!==null,appliedA,false);
 const tierB=RecipeLogic.offerRankingTier(optB.price!==null,appliedB,false);
 if(tierA!==tierB)return tierA-tierB;
 if(optA.price!==null&&optB.price!==null&&optA.price!==optB.price)return optA.price-optB.price;
 return displayTitle(a).localeCompare(displayTitle(b),'nl');
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
function render(){if(!$('cards'))return;const q=norm($('q').value),d=$('dish').value,status=$('status').value;const full=all(),linkFilter=$('hfresh-link-filter')?.value||'all';let rows=full.filter(r=>(linkFilter==='all'||(r.source==='HelloFresh'&&(linkFilter==='linked')===Boolean(hfreshLink(r))))&&(state.source==='Alle'||r.source===state.source)&& (state.kind==='alle'||protein(r)===state.kind)&&(!d||dish(r)===d)&&norm(searchableText(r)).includes(q)&&(!status||(status==='yes'?completePrice(r)!==null:completePrice(r)===null))&&(!$('offers-only')?.checked||(completePrice(r)!==null&&offerWords(r).length>0)));
const order=$('sort').value;$('sort').querySelector('[value=cheap]').textContent=state.basis==='cash'?'Laagste kassabon eerst':'Laagste verbruikskosten eerst';rows.sort((a,b)=>{if(order==='cheap')return (completePrice(a)===null)-(completePrice(b)===null)||(rankingPrice(a)??Infinity)-(rankingPrice(b)??Infinity)||displayTitle(a).localeCompare(displayTitle(b),'nl');if(order==='leastmissing')return ((priceCoverage(a).unknown?Infinity:priceCoverage(a).missing)-(priceCoverage(b).unknown?Infinity:priceCoverage(b).missing))||a.title_extracted.localeCompare(b.title_extracted,'nl');if(order==='offers')return offerSort(a,b);if(order==='matches')return incomplete(b)-incomplete(a)||a.title_extracted.localeCompare(b.title_extracted,'nl');return a.title_extracted.localeCompare(b.title_extracted,'nl')});
if(state.top)rows=rows.filter(r=>completePrice(r)!==null).sort((a,b)=>rankingPrice(a)-rankingPrice(b)).slice(0,10);
const scope=full.filter(r=>state.source==='Alle'||r.source===state.source),covered=scope.filter(r=>completePrice(r)!==null).length,offersCount=rows.filter(r=>completePrice(r)!==null&&offerWords(r).length>0).length;$('count').textContent=rows.length+' getoond · '+offersCount+' met doorgerekende actie · '+covered+' van '+scope.length+' met volledige raming · '+(state.store==='Voordeligste'?'laagste beschikbare raming per recept':state.store)+(state.basis==='cash'?' · kassabon gekozen producten':' · verbruikskosten')+(state.top?' · top 10':order==='offers'?' · doorgerekende actie-alternatieven → laagste kassabon':'');
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
 '<div class="minor">'+esc(displayIngredients(r).slice(0,3).map(i=>i.name).join(' · ')||'Ingrediëntencontrole vereist')+'</div>'+ (hfreshLink(r)?'<p class="sub">Ook in onafhankelijke HFresh-databank</p>':'')+
 '<div class="main-cost '+priceClass+'"><strong>'+costLabel+'</strong><small>'+esc(costInfo)+'</small>'+(est?.scenario_offer?'<small>Met doorgerekend actiescenario · indicatief kassabonverschil '+eur(selectedStoreOption(r).savings)+'</small>':'')+'</div>'+
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
  const option=storeOption(r,store),estimate=option.estimate,cost=RecipeLogic.estimatePrice(estimate);
  return '<tr><th>'+store+'</th><td>'+(cost!==null?'≈ '+eur(cost):'Onvolledig')+'</td><td>'+(cost!==null?eur(estimate.whole_packages_eur):'—')+'</td><td>'+(cost!==null?(option.changes.length?option.changes.length+' actie-alternatieven (scenario)':(estimate.actions_applied||0)+' acties toegepast'):estimate?.missing?.length?'Ontbrekende prijscomponenten':'Geen raming beschikbaar')+'</td></tr>';
 }).join('');
 const total=v!==null?'<div class="estimate"><strong>Geschatte kassabon: '+eur(e.whole_packages_eur)+' voor 2 personen</strong><p>Hele verpakkingen, zonder eigen voorraad. Alleen gebruikte hoeveelheden: <b>'+eur(v)+' voor 2 porties ('+eur(v/2)+' p.p.)</b>. Resterende inhoud kan je later gebruiken. Dit is geen gegarandeerde filiaalprijs.</p></div>'+(Number.isFinite(e.norm_scenario_low_eur)?'<p class="sub">Normscenario: '+eur(e.norm_scenario_low_eur)+' tot '+eur(e.norm_scenario_high_eur)+' voor twee porties bij −25% / +25% normhoeveelheden. Dit is een gevoeligheidsberekening, geen gegarandeerde prijsmarge.</p>':'')+(e.scenario_offer?'<p class="offer-indicator">Actiescenario: '+selectedStoreOption(r).changes.length+' alternatief product(en) verwerkt, indicatief kassabonverschil '+eur(selectedStoreOption(r).savings)+' ten opzichte van de reguliere gekozen producten. Mogelijk deels door andere verpakkingsgrootte; geen gegarandeerde korting.</p>':e.actions_applied?'<p class="offer-indicator">'+e.actions_applied+' eerder toegepaste actie(s) volgens de prijssnapshot. Controleer de details en voorwaarden.</p>':'<p class="sub">Geen aantoonbare actie verwerkt in deze kassabon. Mogelijke alternatieven bij andere winkels zijn geen bewijs van lagere receptkosten.</p>'):'<p class="notice"><b>Nog geen volledige prijsraming.</b> Ontbrekende componenten krijgen geen nulprijs en dit recept komt niet in de prijsranglijst.</p>';
 const missing=(e?.missing||[]);
 const gaps=missing.length?'<h3>Nog ontbrekend</h3><ul>'+missing.map(m=>'<li><b>'+esc(m.ingredient)+'</b>: '+esc(m.reason)+'</li>').join('')+'</ul>':!e?'<p class="notice">Voor dit recept is nog geen ramingsrecord beschikbaar.</p>':'';
 const lines=e?.lines||[];
 const lineTable=lines.length?'<h3>Productkeuzes en kosten</h3><div class="price-table-wrap"><table class="price-table"><thead><tr><th>Ingrediënt en rekenhoeveelheid</th><th>Gekozen product</th><th>Verbruik</th><th>Hele verpakkingen</th></tr></thead><tbody>'+lines.map(x=>{
  const link=url(x.link),a=x.action;
  return '<tr><td>'+esc(x.ingredients.join(' / '))+'<small>'+(x.norm?'≈ ':'')+fmt(x.quantity)+' '+esc(x.unit)+'</small></td><td>'+(link?'<a href="'+link+'" target="_blank" rel="noopener">'+esc(x.product)+'</a>':esc(x.product))+(x.package_size?'<small>'+esc(x.package_size)+' · '+eur(x.package_price)+'</small>':'')+(x.package_conversion?'<small class="assumption-note">'+esc(x.package_conversion)+'</small>':'')+(x.price_proxy?'<small class="assumption-note">Prijsproxy; zie aannames</small>':'')+(a?'<small class="offer-indicator">'+(x.scenario_offer?'Indicatief productalternatief · ':'')+esc(a.discount||'Actie')+' · '+(a.multi_buy_quantity&&Number.isFinite(a.multi_buy_price)?esc(a.multi_buy_quantity)+' voor '+eur(a.multi_buy_price):Number.isFinite(a.price)?eur(a.price):'Prijs onbekend')+' · t/m '+esc(a.valid_until)+(a.card_required?' · klantenkaart nodig':'')+'</small>':'')+'</td><td>'+eur(x.used_cost)+'</td><td>'+eur(x.cash_cost)+(Number.isFinite(x.packages)?'<small>'+x.packages+' verpakking(en) · '+fmt(x.leftover)+' '+esc(x.unit)+' over</small>':'')+'</td></tr>';
 }).join('')+'</tbody></table></div><p class="sub">Regelbedragen zijn afgerond; de totaalraming wordt berekend uit onafgeronde kosten.</p>':'';
 const assumptions=(e?.assumptions||[]);
 const normRows=assumptions.map(a=>'<li><b>'+esc(a.ingredient)+'</b> → ≈ '+fmt(a.quantity)+' '+esc(a.unit)+'. '+esc(a.note)+(url(a.source)?' <a href="'+url(a.source)+'" target="_blank" rel="noopener">Bron normgewicht</a>':'')+'</li>').join('');
 const packNotes=lines.filter(x=>x.package_conversion).map(x=>'<li><b>'+esc(x.product)+'</b>: '+esc(x.package_conversion)+'</li>').join('');
 const norms='<section class="norm-section"><h3>Zichtbare normgewichten en aannames</h3>'+(normRows||packNotes?'<ul>'+normRows+packNotes+'</ul>':'<p>Geen normregel beschikbaar voor deze onvolledige raming.</p>')+'<p class="sub">Werkaannames zijn geen gemeten HelloFresh-verpakkingsgewichten. De productkeuzes en bronhoeveelheden blijven zichtbaar. Prijsproxy’s zijn kostenbenaderingen; de oorspronkelijke receptkeuze blijft leidend.</p></section>';
 const comparisonList=displayIngredients(r).map(i=>(String(i.quantity||'').trim()+' '+String(i.name||'').replace(/\([^)]*\)/g,'')).trim()).filter(Boolean);
 const checkjebonLink=comparisonList.length?'https://www.checkjebon.nl/#'+encodeURIComponent(comparisonList.join('\n')):null;
 const outsidePriceCheck=checkjebonLink?'<section class="norm-section"><h3>Externe controle: Checkjebon</h3><p><a href="'+esc(checkjebonLink)+'" target="_blank" rel="noopener noreferrer">Vergelijk de ingrediëntenlijst bij AH en Jumbo in Checkjebon</a></p><p class="sub">Checkjebon gebruikt eigen producten en fuzzy matching. Controleer de juiste varianten en hoeveelheden; overgenomen prijzen zijn niet gevalideerd in deze receptprijs. Lidl wordt niet ondersteund door Checkjebon.</p></section>':'';
 const portions=r.ingredients_2p?2:4;
 const external=hfreshDetail(r);
 $('dialog').innerHTML='<button type="button" class="close" id="close" aria-label="Sluit recept">×</button><div class="meta">'+esc(r.source||'HelloFresh')+' · '+esc(protein(r))+'</div><h2>'+esc(displayTitle(r))+'</h2><p class="quality-label">Indicatieve prijsraming · twee personen · '+esc(shop)+'</p>'+total+outsidePriceCheck+external+'<h3>Vergelijk de winkels</h3><div class="price-table-wrap"><table class="price-table"><thead><tr><th>Winkel</th><th>Verbruik, 2 porties</th><th>Gekozen verpakkingen</th><th>Status</th></tr></thead><tbody>'+comparison+'</tbody></table></div><p class="sub">Elke raming gebruikt producten uit één winkel. Het kassabedrag hoort bij de getoonde productkeuzes; er is geen voorraad verondersteld. Voordeelpakken verlagen de verbruikskosten alleen als je de rest ook gebruikt. Kaartacties: '+(state.cards?'ingeschakeld':'uitgeschakeld')+'.</p>'+detailOfferBlock(r)+gaps+lineTable+norms+'<h3>Bronhoeveelheden ('+portions+' porties)</h3><ul>'+displayIngredients(r).map(i=>'<li>'+esc(i.quantity)+' '+esc(i.name)+'</li>').join('')+'</ul>'+(!r.table_repair?'<p class="notice">Deze bronkolom doorstaat de automatische tabelcontrole nog niet. Er wordt geen totaalraming van gemaakt.</p>':'<p class="sub">Herstelde bronkolom; de oorspronkelijke kaart blijft leidend. Een prijsraming is geen handmatig gecertificeerde receptprijs.</p>')+src+'<p class="sub">Prijsnormen: '+esc(e?.policy_version||'nog niet beschikbaar')+'. Water, energie, bezorging en reiskosten vallen buiten deze vergelijking. Filiaalprijzen kunnen afwijken.</p>';
 $('modal').classList.add('open');
 $('close').onclick=()=>{$('modal').classList.remove('open');state.selectedId=null;};
 if(r.source==='HelloFresh'){
  $('hfresh-copy')?.addEventListener('click',async()=>{
   const title=displayTitle(r),message=$('hfresh-link-message');
   try{
    if(!navigator.clipboard?.writeText)throw Error('Niet beschikbaar');
    await navigator.clipboard.writeText(title);
    message.textContent='Recepttitel gekopieerd. Plak hem in het zoekveld van HFresh.';
   }catch(_){const input=$('hfresh-recipe-title');input.focus();input.select();message.textContent='Selecteer en kopieer de gemarkeerde titel met Ctrl+C of Cmd+C.';}
  });
  $('hfresh-save')?.addEventListener('click',()=>{
   const input=$('hfresh-link-input'),message=$('hfresh-link-message');
   const url=HFreshLinks.safeUrl(input?.value);
   if(!url){message.textContent='Ongeldige HFresh-receptlink. Gebruik een volledige HTTPS-link van hfresh.info/nl-NL/recipes/...';return;}
   const next={...state.hfreshLocal,[String(r.id)]:url};
   try{localStorage.setItem('hfresh-local-links-v1',JSON.stringify(HFreshLinks.exportManual(next).recipe_links));}
   catch(_){message.textContent='Opslaan in deze browser is geblokkeerd. Controleer privacy-instellingen of opslagruimte.';return;}
   state.hfreshLocal=HFreshLinks.cleanManual(next);refreshHFreshStatus();render();details(String(r.id));
  });
  $('hfresh-remove')?.addEventListener('click',()=>{
   const next={...state.hfreshLocal};delete next[String(r.id)];
   try{localStorage.setItem('hfresh-local-links-v1',JSON.stringify(HFreshLinks.exportManual(next).recipe_links));}
   catch(_){$('hfresh-link-message').textContent='Verwijderen kon niet worden opgeslagen.';return;}
   state.hfreshLocal=HFreshLinks.cleanManual(next);refreshHFreshStatus();render();details(String(r.id));
  });
 }
}
function parseCSV(s){const rows=[],record=[];let cell='',quoted=false;for(let i=0;i<s.length;i++){let c=s[i];if(c==='"'){if(quoted&&s[i+1]==='"'){cell+='"';i++}else quoted=!quoted}else if(c===';'&&!quoted){record.push(cell);cell=''}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&s[i+1]==='\n')i++;record.push(cell);if(record.some(x=>x.trim()))rows.push(record.splice(0));cell=''}else cell+=c}record.push(cell);if(record.some(x=>x.trim()))rows.push(record);const head=(rows.shift()||[]).map(x=>x.trim().replace(/^\uFEFF/,''));return rows.map(r=>Object.fromEntries(head.map((h,i)=>[h,r[i]||''])))}
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error(url+': HTTP '+r.status);return r.json()}
function once(id,event,fn){$(id)?.addEventListener(event,fn)}
function init(){refreshHealth();setInterval(refreshHealth,5*60*1000);try{state.hfreshLocal=HFreshLinks.cleanManual(JSON.parse(localStorage.getItem('hfresh-local-links-v1')||'{}'))}catch(_){state.hfreshLocal={}};refreshHFreshStatus();try{state.estimates=JSON.parse(localStorage.getItem('hf-local-price-estimates')||'{}')}catch(e){state.estimates={}};once('q','input',()=>{state.shown=36;render()});for(const id of ['dish','sort','status','source','cost-basis','offers-only','hfresh-link-filter'])once(id,'change',()=>{state.shown=36;if(id==='source')state.source=$('source').value;if(id==='cost-basis')state.basis=$('cost-basis').value;render()});once('more','click',()=>{state.shown+=36;render()});once('top','click',()=>{state.top=!state.top;render()});once('modal','click',e=>{if(e.target===$('modal'))$('modal').classList.remove('open')});document.addEventListener('keydown',e=>{if(e.key==='Escape')$('modal').classList.remove('open')});
once('card-promotions','change',()=>{state.cards=$('card-promotions').checked;resetOfferCaches();render();if($('modal').classList.contains('open')&&state.selectedId)details(state.selectedId)});
once('hfresh-import','change',async e=>{
 const message=$('hfresh-import-status');
 try{
  const file=e.target.files?.[0];if(!file)return;
  const payload=JSON.parse(await file.text());
  if(payload.schema_version!==1||!payload.recipe_links||typeof payload.recipe_links!=='object')
   throw Error('Gebruik een geëxporteerd HFresh-koppelingenbestand.');
  if(!state.recipes.some(r=>r.source==='HelloFresh'))throw Error('Receptenindex is nog niet geladen.');
  const allowed=new Set(state.recipes.filter(r=>r.source==='HelloFresh').map(r=>String(r.id)));
  const incoming=HFreshLinks.cleanManual(payload.recipe_links);
  const accepted=Object.entries(incoming).filter(([id])=>allowed.has(id));
  if(!accepted.length)throw Error('Geen geldige koppelingen voor jouw recepten gevonden.');
  const next={...state.hfreshLocal,...Object.fromEntries(accepted)};
  localStorage.setItem('hfresh-local-links-v1',JSON.stringify(HFreshLinks.exportManual(next).recipe_links));
  state.hfreshLocal=HFreshLinks.cleanManual(next);
  message.textContent=accepted.length+' lokale HFresh-verwijzingen ingelezen. De prijsramingen blijven ongewijzigd.';
  refreshHFreshStatus();render();
 }catch(err){message.textContent='Import niet uitgevoerd: '+err.message;}
 e.target.value='';
});
once('hfresh-export','click',()=>{
 const data=JSON.stringify(HFreshLinks.exportManual(state.hfreshLocal),null,2)+'\n';
 const blob=new Blob([data],{type:'application/json'});
 const url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download='hfresh-receptenkoppelingen.json';document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
});
once('file','change',async e=>{try{const rows=parseCSV(await e.target.files[0].text());if(!rows.length||!('titel_automatisch' in rows[0]))throw Error('CSV niet herkend');state.extra=rows.map((r,i)=>({id:'local-'+i,title_extracted:r.titel_automatisch,source:'HelloFresh',source_file:r.bron,source_page_ingredients:r.paginas,ingredients_4p:[]})).filter(r=>r.title_extracted);$('import-status').textContent=state.extra.length+' extra bronrecords geladen in deze browser.';dishOptions();render()}catch(err){$('import-status').textContent='Import mislukt: '+err.message}});
once('clear','click',()=>{state.extra=[];$('file').value='';$('import-status').textContent='Lokale import gewist';dishOptions();render()});options();dishOptions();render();
json('../recipes_extracted.json').then(d=>{if(!Array.isArray(d.recipes)||!d.recipes.length)throw Error('Geen recepten in bron');state.recipes=state.recipes.filter(x=>x.source==='Plated').concat(d.recipes.map(r=>({...r,source:'HelloFresh'})));state.loading=false;dishOptions();refreshHFreshStatus();render()}).catch(err=>{state.loading=false;$('count').textContent='Receptendatabase niet geladen: '+err.message;render()});
function refreshOriginals(){Promise.allSettled([json('./preview_manifest.json'),json('./plated_preview_manifest.json')]).then(res=>{let previews={};for(const item of res){if(item.status==='fulfilled')Object.assign(previews,item.value.recipes||{})}state.previews=previews;render()})}refreshOriginals();
setInterval(refreshOriginals,5*60*1000);
function refreshPrices(){return json('../recipe_prices.json').then(d=>{const at=new Date(d.fetched_at_utc);if(Date.now()-at.getTime()>=0&&Date.now()-at.getTime()<3*86400000){state.priceDate=at;state.prices=new Map((d.results||[]).map(r=>[r.store+':'+r.recipe_id,r]));resetOfferCaches()}else{state.priceDate=null;state.prices.clear();resetOfferCaches()}render()}).catch(()=>{if(state.priceDate&&Date.now()-state.priceDate.getTime()>=3*86400000){state.priceDate=null;state.prices.clear();resetOfferCaches()}render()})}
refreshPrices();setInterval(refreshPrices,10*60*1000);
json('./hfresh_matches.json').then(d=>{
 if(d.schema_version!==1||!d.recipe_links||typeof d.recipe_links!=='object')throw Error('Ongeldige bronverwijzingen');
 state.hfreshMatches=HFreshLinks.safeSnapshot(d);
 refreshHFreshStatus();render();
}).catch(()=>{state.hfreshMatches={};refreshHFreshStatus();render()});
json('../plated_nl_catalog.json').then(d=>{state.nlCatalog=Object.fromEntries((d.recipes||[]).map(x=>[x.source_identity||x.id,x]));render()}).catch(()=>{});
function refreshDeals(){
 return json('../weekdeals_hellofresh.json').then(d=>{
  const age=Date.now()-new Date(d.updated_at_utc).getTime();
  const good=d.schema_version===1&&d.coverage?.full_promotional_feed===true&&age>=0&&age<48*3600000&&
   ['AH','Jumbo','Lidl'].every(k=>Array.isArray(d.stores?.[k]?.deals));
  if(!good)throw Error('Weekdeals-feed onvolledig of verouderd');
  state.deals=d.stores;
  state.dealsMeta={source:d.source,updated_at_utc:d.updated_at_utc,coverage:d.coverage};
  resetOfferCaches();render();
 }).catch(()=>json('../market_deals.json').then(d=>{
   const age=Date.now()-new Date(d.updated_at_utc).getTime();
   state.deals=age>=0&&age<48*3600000?d.stores||{}:{};
   state.dealsMeta={source:'Beperkte PrijsProfeet-terugvalbron',updated_at_utc:d.updated_at_utc,coverage:{food_category_filtered:false}};
   resetOfferCaches();render();
 }).catch(()=>{state.deals={};state.dealsMeta={source:'Geen actuele acties beschikbaar'};resetOfferCaches();render()}));
}
refreshDeals();
function refreshPlated(){json('../plated_release_review_queue.json').then(d=>{const records=(d.recipes||[]).map((r,i)=>({...r,source:'Plated',id:'plated-release-'+(r.source_identity||i)}));state.recipes=state.recipes.filter(x=>x.source!=='Plated').concat(records);const el=$('plated-summary');if(el)el.textContent=records.length+' Plated-receptkaarten uit Marc\'s archief beschikbaar (voorlopige OCR, niet prijsgeldig).';dishOptions();render()}).catch(()=>{const el=$('plated-summary');if(el)el.textContent='Plated-import is nog niet bereikbaar. HelloFresh blijft beschikbaar.'})}
refreshPlated();
setInterval(refreshPlated,5*60*1000);
setInterval(refreshDeals,10*60*1000);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
