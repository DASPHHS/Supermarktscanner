const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const d=JSON.parse(fs.readFileSync(path.join(__dirname,'../hellofresh/scanned_recipe_candidates.json'),'utf8'));
test('image-only archive fully accounted for: 61 pages, 60 unique recipe records',()=>{
 assert.equal(d.schema_version,1);
 assert.equal(d.source_pages_total,61);
 assert.equal(d.recipes.length,60);
 assert.equal(new Set(d.recipes.map(r=>r.id)).size,60);
 assert.equal(new Set(d.recipes.map(r=>r.title_extracted)).size,60);
 const pages=new Set(d.recipes.flatMap(r=>r.source_pages));
 assert.deepEqual([...pages].sort((a,b)=>a-b),Array.from({length:61},(_,i)=>i+1));
 const combined=d.recipes.find(r=>r.source_pages.includes(49));
 assert.deepEqual(combined.source_pages,[48,49],'page 49 is a continuation, not another recipe');
});
test('OCR text is never approved as a recipe, serving count or checkout price',()=>{
 for(const r of d.recipes){
  assert.equal(r.source,'HelloFresh');
  assert.equal(r.quality,'needs_manual_verification');
  assert.equal(r.image_only_archive,true);
  assert.equal(r.pricing_eligible,false);
  assert.equal(r.servings_verified,false);
  assert.equal(r.ingredients_verified,false);
  assert.equal(r.quantities_verified,false);
  assert.ok(r.title_extracted.length>5);
  for(const row of r.ingredients_4p){
   assert.ok(row.ingredient);
   assert.equal(row.quantity_4p_source,null);
   assert.equal(row.source,'ocr_icon_candidate_unverified');
  }
 }
});
