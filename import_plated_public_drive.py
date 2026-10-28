"""Import Plated PDFs listed in a public-link Drive manifest, without Drive credentials.

PDF bytes live only on the ephemeral GitHub Actions runner. OCR records are
unverified and never automatically eligible for pricing.
"""
import argparse, hashlib, json, re, tempfile
from datetime import datetime, timezone
from pathlib import Path
from drive_plated_sync import inspect, title_key, EXTRACTION_VERSION

def load(path, fallback):
    path=Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback

def fetch_public_pdf(file_id, destination):
    import gdown
    output=gdown.download(id=file_id, output=str(destination), quiet=True)
    if not output or not Path(output).exists() or Path(output).stat().st_size<500:
        raise RuntimeError("Public Google Drive download not accessible or empty")
    with Path(output).open("rb") as fh:
        if fh.read(4)!=b"%PDF":
            raise RuntimeError("Downloaded data is not a PDF")

def run(manifest_path="plated_drive_manifest.json", root=".", batch=12, fetcher=fetch_public_pdf, inspector=inspect):
    base=Path(root)
    manifest=load(manifest_path,{"files":[]})
    state_path=base/"plated_drive_public_state.json"
    queue_path=base/"plated_drive_public_review_queue.json"
    stats_path=base/"plated_drive_public_progress.json"
    state=load(state_path,{"completed":{},"failure_counts":{},"errors":{}})
    queue=load(queue_path,{"recipes":[]})
    records={r["source_identity"]:r for r in queue["recipes"] if r.get("source_identity")}
    hashes={r.get("content_sha256") for r in records.values()}
    groups={}
    for file in manifest["files"]:
        if not file["name"].lower().endswith(".pdf"):continue
        groups.setdefault(title_key(file["name"]),[]).append(file)
    # Process originals before duplicate-named copies.
    titles=sorted(groups)
    attempted=imported=exact_duplicates=0
    new_errors=[]
    for key in titles:
        choices=sorted(groups[key],key=lambda f:(f["name"].lower().startswith("dupe_"),f["name"].lower()))
        candidate=choices[0]
        identity=candidate["id"]
        if state["completed"].get(identity):
            old=records.get(identity)
            if old and old.get("extraction_version",0)>=EXTRACTION_VERSION:continue
        if state["failure_counts"].get(identity,0)>=3:continue
        if attempted>=batch:break
        attempted+=1
        try:
            with tempfile.TemporaryDirectory() as folder:
                target=Path(folder)/"input.pdf"
                fetcher(identity,target)
                digest=hashlib.sha256(target.read_bytes()).hexdigest()
                if digest in hashes and identity not in records:
                    exact_duplicates+=1
                else:
                    item=inspector(target,candidate["name"],hashlib.sha256(identity.encode()).hexdigest())
                    item["source_identity"]=identity
                    item["original_filename"]=candidate["name"]
                    item["same_title_candidates"]=[x["name"] for x in choices[1:]]
                    item["quality"]="needs_manual_verification"
                    item["pricing_eligible"]=False
                    is_new=identity not in records
                    records[identity]=item
                    hashes.add(digest)
                    if is_new:imported+=1
            state["completed"][identity]=digest
            state["errors"].pop(identity,None)
        except Exception as err:
            state["failure_counts"][identity]=state["failure_counts"].get(identity,0)+1
            message=f"{candidate['name']}: {type(err).__name__}: {str(err)[:140]}"
            state["errors"][identity]=message
            new_errors.append(message)
    now=datetime.now(timezone.utc).isoformat()
    queue={"metadata":{"source":"Plated Google Drive (public-link download)",
             "updated_at_utc":now,"imported":len(records),
             "note":"Preliminary OCR review queue only. NO prices, NO validated recipes."},
           "recipes":sorted(records.values(),key=lambda r:r.get("title_extracted","").lower())}
    status={"updated_at_utc":now,"manifest_pdf_count":len(manifest["files"]),
            "unique_title_candidates":len(groups),
            "attempted_this_run":attempted,"new_records_this_run":imported,
            "records_in_queue":len(records),"exact_duplicates_this_run":exact_duplicates,
            "pricing_eligible":0,"download_or_ocr_errors_this_run":new_errors[:20],
            "blocked_after_three_failures":sum(x>=3 for x in state["failure_counts"].values()),
            "manual_review_required":True}
    for path,value in [(state_path,state),(queue_path,queue),(stats_path,status)]:
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(status,ensure_ascii=False))
    return status

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",default="plated_drive_manifest.json")
    p.add_argument("--batch",type=int,default=12)
    options=p.parse_args()
    if not 1<=options.batch<=30:p.error("Batch size 1-30")
    run(options.manifest,batch=options.batch)
