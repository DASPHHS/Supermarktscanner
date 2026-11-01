/* HFresh links are supplemental navigation only; never pricing or validation input. */
(function(root){
'use strict';
const LINK_PATTERN=/^\/nl-NL\/recipes\/[a-z0-9-]+-[0-9]+\/?$/;
function safeUrl(raw){
 if(typeof raw!=='string'||raw.length>400)return null;
 try{
  const u=new URL(raw.trim());
  if(u.protocol!=='https:'||!['hfresh.info','www.hfresh.info'].includes(u.hostname)||
     u.username||u.password||u.port||u.search||u.hash||!LINK_PATTERN.test(u.pathname))return null;
  return u.origin+u.pathname;
 }catch(_){return null;}
}
function safeId(id){return /^[A-Za-z0-9_-]{1,100}$/.test(String(id||''));}
function cleanManual(input){
 const out=Object.create(null);
 if(!input||typeof input!=='object'||Array.isArray(input))return out;
 for(const [id,value] of Object.entries(input).slice(0,3000)){
  if(!safeId(id))continue;
  const url=safeUrl(typeof value==='string'?value:value?.url);
  if(url)out[id]=url;
 }
 return out;
}
function safeSnapshot(input){
 const out=Object.create(null);
 if(!input||input.schema_version!==1||!input.recipe_links||
    typeof input.recipe_links!=='object'||Array.isArray(input.recipe_links))return out;
 for(const [id,link] of Object.entries(input.recipe_links).slice(0,3000)){
  if(!safeId(id)||!link||typeof link!=='object'||link.match!=='exact_title_only')continue;
  const url=safeUrl(link.url);
  if(!url)continue;
  out[id]={url,match:'exact_title_only',title:String(link.title||'').slice(0,160),
    total_time:Number.isInteger(link.total_time)&&link.total_time>0&&link.total_time<=600?link.total_time:null};
 }
 return out;
}
function linkFor(recipe,snapshot,manual){
 if(!recipe||recipe.source!=='HelloFresh'||!safeId(recipe.id))return null;
 const id=String(recipe.id);
 const hand=safeUrl(manual?.[id]);
 if(hand)return {url:hand,origin:'manual',total_time:null};
 const linked=snapshot?.[id];
 const url=linked?.match==='exact_title_only'?safeUrl(linked.url):null;
 return url?{url,origin:'api',total_time:linked.total_time}:null;
}
function exportManual(manual){
 return {schema_version:1,source:'HFresh handmatige links',
         note:'Alleen URL-verwijzingen; geen receptprijzen of gevalideerde hoeveelheden.',
         recipe_links:{...cleanManual(manual)}};
}
const api={safeUrl,cleanManual,safeSnapshot,linkFor,exportManual};
if(typeof module==='object'&&module.exports)module.exports=api;
root.HFreshLinks=api;
})(typeof globalThis!=='undefined'?globalThis:this);
