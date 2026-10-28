"""Merge independent GitHub Actions OCR batches after syncing latest main.

Preserve already imported recipes when another commit updates GitHub during OCR.
This is for *unverified review queues* only, never public approval or pricing.
"""
import argparse
import json
from pathlib import Path

NAMES=(
    "plated_drive_public_state.json","plated_drive_public_review_queue.json",
    "plated_drive_public_progress.json","plated_local_state.json",
    "plated_local_review_queue.json","plated_local_progress.json",
    "plated_release_state.json","plated_release_review_queue.json","plated_release_progress.json",
)
def read(path):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:return {}

def write(path,content):
    Path(path).write_text(json.dumps(content,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def merge_state(remote,local):
    result={**remote,**{k:v for k,v in local.items() if k not in ("completed","processed","errors","failure_counts","failures","duplicates")}}
    for key in ("completed","processed","duplicates"):
        result[key]={**remote.get(key,{}),**local.get(key,{})}
    for key in ("failure_counts",):
        values={**remote.get(key,{})}
        for k,v in local.get(key,{}).items():
            values[k]=max(values.get(k,0),v)
        result[key]=values
    for key in ("errors","failures"):
        errors={**remote.get(key,{}),**local.get(key,{})}
        for k in result.get("completed",{}):
            errors.pop(k,None)
        result[key]=errors
    return result

def merge_queue(remote,local):
    grouped={}
    for item in [*remote.get("recipes",[]),*local.get("recipes",[])]:
        key=item.get("source_identity") or item.get("source_path") or item.get("drive_identity_hash") or item.get("id")
        if not key:continue
        old=grouped.get(key,{})
        old_score=(old.get("extraction_version",0),len(old.get("ingredients_4p") or []),len(old.get("ingredient_candidates_original") or []))
        new_score=(item.get("extraction_version",0),len(item.get("ingredients_4p") or []),len(item.get("ingredient_candidates_original") or []))
        if new_score>=old_score:
            grouped[key]={**old,**item}
    recipes=sorted(grouped.values(),key=lambda r:r.get("title_extracted","").lower())
    for r in recipes:
        # A queue record can NEVER become approved automatically.
        r["pricing_eligible"]=False
    return {"metadata":{**remote.get("metadata",{}),**local.get("metadata",{}),"imported":len(recipes),
                         "count":len(recipes),"status":"manual_review_required"},
            "recipes":recipes}

def merge_progress(remote,local,public_count,local_count):
    result={**remote,**local}
    if public_count is not None:
        result["records_in_queue"]=public_count
        result["pricing_eligible"]=0
    if local_count is not None:
        result["pending_review"]=local_count
        result["pricing_eligible"]=0
    return result

def merge_files(source,destination=Path(".")):
    source=Path(source);destination=Path(destination)
    for name in NAMES:
        localpath=source/name
        if not localpath.exists():continue
        remote=read(destination/name)
        local=read(localpath)
        if name.endswith("_state.json"):merged=merge_state(remote,local)
        elif name.endswith("_review_queue.json"):merged=merge_queue(remote,local)
        else:
            p=read(destination/"plated_drive_public_review_queue.json")
            l=read(destination/"plated_local_review_queue.json")
            merged=merge_progress(remote,local,
                len(p.get("recipes",[])) if name.startswith("plated_drive") else None,
                len(l.get("recipes",[])) if name.startswith("plated_local") else None)
        write(destination/name,merged)
    # Progress must reflect merged review queues after they are written.
    for name,queue in (("plated_drive_public_progress.json","plated_drive_public_review_queue.json"),
                       ("plated_local_progress.json","plated_local_review_queue.json"),
                       ("plated_release_progress.json","plated_release_review_queue.json")):
        path=destination/name
        if path.exists():
            d=read(path);n=len(read(destination/queue).get("recipes",[]))
            d["records_in_queue" if "drive_public" in name else ("records_in_review" if "release" in name else "pending_review")]=n
            d["pricing_eligible"]=0
            write(path,d)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    args=ap.parse_args()
    merge_files(args.source)
