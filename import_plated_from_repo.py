"""Resumable PDF import from files already tracked in the repository.

Outputs a separate *unverified* review queue. Never assumes OCR text is correct
or makes a recipe eligible for price calculations.
"""
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from drive_plated_sync import inspect, title_key

def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def run(folder, batch=20, root=Path(".")):
    root=Path(root)
    folder=Path(folder)
    statefile=root/"plated_local_state.json"
    queuefile=root/"plated_local_review_queue.json"
    progressfile=root/"plated_local_progress.json"
    state=read_json(statefile, {"processed":{},"failures":{}})
    queue=read_json(queuefile, {"metadata":{},"recipes":[]})
    indexed={r["source_path"]:r for r in queue.get("recipes",[]) if r.get("source_path")}
    candidates=sorted((p for p in folder.rglob("*") if p.is_file() and p.suffix.lower()==".pdf"),
                      key=lambda p:(p.name.lower().startswith("dupe_"),p.name.casefold()))
    by_title={}
    for pdf in candidates:
        key=title_key(pdf.name)
        by_title.setdefault(key,[]).append(pdf)
    imported=0; attempted=0; exact_duplicates=0; errors=[]
    hashes={r.get("content_sha256") for r in indexed.values()}
    for key, group in sorted(by_title.items()):
        pdf=group[0]
        rel=pdf.as_posix()
        rawhash=hashlib.sha256(pdf.read_bytes()).hexdigest()
        if state["processed"].get(rel)==rawhash:continue
        if attempted>=batch:break
        attempted+=1
        if rawhash in hashes:
            state["processed"][rel]=rawhash
            exact_duplicates+=1
            continue
        try:
            record=inspect(pdf,pdf.name,hashlib.sha256(rel.encode()).hexdigest())
            record["source_path"]=rel
            record["duplicate_title_candidates"]=[p.as_posix() for p in group[1:]]
            # Keep raw PDF source private; don't link to the public GitHub Pages site.
            record["pricing_eligible"]=False
            record["quality"]="needs_manual_verification"
            indexed[rel]=record
            state["processed"][rel]=rawhash
            state["failures"].pop(rel,None)
            hashes.add(rawhash)
            imported+=1
        except Exception as exc:
            msg=f"{rel}: {type(exc).__name__}: {str(exc)[:180]}"
            state["failures"][rel]=msg
            errors.append(msg)
    queue["recipes"]=sorted(indexed.values(),key=lambda x:x["title_extracted"].casefold())
    now=datetime.now(timezone.utc).isoformat()
    queue["metadata"]={"source":"Plated","updated_at":now,"count":len(queue["recipes"]),
                       "status":"review_required_no_automatic_price_approval"}
    progress={"updated_at":now,"pdf_files":len(candidates),"title_groups":len(by_title),
              "possible_title_duplicates":len(candidates)-len(by_title),
              "attempted_this_run":attempted,"imported_this_run":imported,
              "exact_duplicates_skipped":exact_duplicates,
              "pending_review":len(queue["recipes"]),"pricing_eligible":0,
              "failures_this_run":errors[:20],"configured_folder":folder.as_posix()}
    for path,value in [(statefile,state),(queuefile,queue),(progressfile,progress)]:
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(progress,ensure_ascii=False))
    return progress

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--folder",default="plated_pdfs")
    ap.add_argument("--batch",type=int,default=20)
    args=ap.parse_args()
    if not 1<=args.batch<=50:ap.error("batch must be in range 1..50")
    run(args.folder,args.batch)
