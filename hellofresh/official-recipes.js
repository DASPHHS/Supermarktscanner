/* Navigation to official HelloFresh recipes only. A title match is NOT source validation. */
(function(root){
'use strict';
function norm(v){
 return String(v??'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'')
  .toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
}
function safeUrl(raw){
 if(typeof raw!=='string'||raw.length>400)return null;
 try{
  const u=new URL(raw);
  if(u.protocol!=='https:'||u.hostname!=='www.hellofresh.nl'||u.port||
   u.username||u.password||u.search||u.hash||!/^(?:\/recipes\/[a-z0-9-]+-[a-f0-9]{24})\/?$/.test(u.pathname))
    return null;
  return u.href;
 }catch(_){return null;}
}
function safeCatalog(catalog){
 const result=Object.create(null);
 if(catalog?.schema_version!==1||!catalog.candidates||typeof catalog.candidates!=='object')return result;
 for(const [title,candidates] of Object.entries(catalog.candidates).slice(0,2000)){
  if(typeof title!=='string'||!title.trim()||!Array.isArray(candidates))continue;
  const matches=[];
  for(const entry of candidates.slice(0,12)){
   const url=safeUrl(entry?.url);
   if(url&&!matches.some(x=>x.url===url)){
    matches.push({url,title:String(entry.title||title).slice(0,160),
      subtitle:String(entry.subtitle||'').slice(0,180),status:'variant_unconfirmed'});
   }
  }
  if(matches.length)result[norm(title)]=matches;
 }
 return result;
}
function candidatesFor(recipe,catalog){
 if(recipe?.source!=='HelloFresh')return [];
 const title=norm(recipe.title_extracted);
 return (catalog?.[title]||[]).map(x=>({...x}));
}
const api={norm,safeUrl,safeCatalog,candidatesFor};
if(typeof module==='object'&&module.exports)module.exports=api;
else root.OfficialRecipeSource=api;
})(typeof globalThis!=='undefined'?globalThis:this);
