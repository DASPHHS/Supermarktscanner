"""Quality gate for provenance, recipe coverage and safe supermarket readiness.

Does not assume OCR accuracy. Fails on structural corruption or falsely
approved pricing; reports incomplete content separately for manual review.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

def read(path,fallback):
 p=Path(path)
 return json.loads(p.read_text(encoding="utf8")) if p.exists() else fallback

def audit(root:Path):
 progress=read(root/"plated_release_progress.json",{})
 queue=read(root/"plated_release_review_queue.json",{}).get("recipes",[])
 nl=read(root/"plated_nl_catalog.json",{}).get("recipes",[])
 rescan=read(root/"plated_ingredient_rescan.json",{}).get("records",{})
 hf=read(root/"recipes_extracted.json",{}).get("recipes",[])
 hf_preview=read(root/"hellofresh/preview_manifest.json",{}).get("recipes",{})
 plated_preview=read(root/"hellofresh/plated_preview_manifest.json",{}).get("recipes",{})
 faults=[];warnings=[]
 ids=[r.get("source_identity") for r in queue]
 repeated=[k for k,v in Counter(ids).items() if k and v>1]
 if repeated:faults.append("Duplicate source identities in review queue: "+str(len(repeated)))
 if any(not k for k in ids):faults.append("Plated source identities missing")
 if any(r.get("pricing_eligible") is True for r in queue):
  faults.append("Unverified Plated OCR source incorrectly marked pricing eligible")
 if any(r.get("pricing_eligible") is True for r in nl):
  faults.append("Unverified Dutch translation incorrectly marked pricing eligible")
 if progress.get("completed_members",0)>progress.get("pdf_members",float("inf")):
  faults.append("PDF completed count exceeds archive member count")
 if progress.get("completed_members",0)<len(queue):
  faults.append("Review queue exceeds completed source count")
 completed=progress.get("completed_members",0)
 duplicates=progress.get("duplicates_total",0)
 if completed and duplicates and completed!=len(queue)+duplicates:
  warnings.append("Processed PDF count differs from review records plus duplicates")
 nd={r.get("source_identity"):r for r in nl}
 unresolved=[]
 unpriced=0;unknown_portions=0;unmapped=0
 for r in queue:
  key=r.get("source_identity")
  translated=nd.get(key)
  if not translated:
   unresolved.append({"source_identity":key,"problem":"missing_dutch_record"})
   continue
  if translated.get("servings_source") not in (2,4):
   unknown_portions+=1
  ing=translated.get("ingredients_nl",[])
  if not ing:
   unpriced+=1
   unresolved.append({"source_identity":key,"problem":"no_ingredient_candidates",
                      "rescan_status":rescan.get(key,{}).get("status","not_attempted")})
  else:
   unmapped+=sum(not x.get("canonical_nl") for x in ing)
   if any(x.get("quantity_basis")=="source_servings_not_verified" for x in ing):
    unresolved.append({"source_identity":key,"problem":"source_servings_unknown",
                       "ingredients":len(ing)})
 hids=[r.get("id") for r in hf]
 if len(hids)!=len(set(hids)):
  faults.append("Duplicate HelloFresh recipe IDs")
 for ref,preview in list(hf_preview.items())+list(plated_preview.items()):
  if not preview.get("front") or not preview.get("original_pdf"):
   warnings.append("Incomplete original-page preview for "+str(ref)[:120])
 report={
  "generated_at_utc":datetime.now(timezone.utc).isoformat(),
  "status":"FAIL" if faults else "PASS_WITH_MANUAL_REVIEW",
  "release_archive_pdfs":progress.get("pdf_members"),
  "release_completed":completed,
  "release_pending":progress.get("remaining_members"),
  "release_exact_duplicates":duplicates,
  "plated_recipes_in_review_queue":len(queue),
  "plated_recipes_with_nl_record":sum(k in nd for k in ids),
  "plated_recipes_without_ingredients":unpriced,
  "plated_recipes_with_unconfirmed_portions":unknown_portions,
  "plated_unmapped_ingredient_labels":unmapped,
  "plated_source_cards_with_original_pdf":len(plated_preview),
  "hellofresh_recipes_in_index":len(hf),
  "hellofresh_recipes_with_original_pdf":len(hf_preview),
  "verified_pricing_eligible_plated":0,
  "critical_faults":faults,
  "warnings":warnings[:30],
  "manual_review_queue_examples":unresolved[:50],
  "notes":["Automated pass does not establish accurate OCR content.",
           "Original PDF and ingredient/serving manual comparison required before pricing.",
           "A recipe with no ingredients or unknown portions cannot be price verified."]}
 return report

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=".")
 p.add_argument("--output",default="recipe_quality_audit.json")
 args=p.parse_args()
 result=audit(Path(args.root))
 Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print(json.dumps({k:v for k,v in result.items() if k not in ("manual_review_queue_examples","notes")},ensure_ascii=False))
 if result["critical_faults"]:
  raise SystemExit("Critical quality gate failed (see JSON audit)")
if __name__=="__main__":main()
