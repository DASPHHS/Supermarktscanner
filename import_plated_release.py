"""Import Plated PDF cards directly from GitHub Release ZIP assets.

Each ZIP member is a distinct source; content SHA-256 is used for exact dedupe.
Never trust archive paths or extraction quantities for pricing.
"""
import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from drive_plated_sync import inspect, EXTRACTION_VERSION

MAX_MEMBER_SIZE = 80 * 1024 * 1024

def load(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def save(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def entries(archive):
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if not info.is_dir() and info.filename.lower().endswith(".pdf"):
                yield info

def run(archive, root=".", batch=60, inspector=inspect):
    archive, root = Path(archive), Path(root)
    root.mkdir(parents=True, exist_ok=True)
    statefile = root / "plated_release_state.json"
    queuefile = root / "plated_release_review_queue.json"
    progressfile = root / "plated_release_progress.json"
    state = load(statefile, {"completed":{}, "failures":{}, "duplicates":{}})
    queue = load(queuefile, {"metadata":{}, "recipes":[]})
    state.setdefault("completed", {})
    state.setdefault("failures", {})
    state.setdefault("duplicates", {})
    existing = {r["source_identity"]:r for r in queue.get("recipes",[]) if r.get("source_identity")}
    known_hashes = {r.get("content_sha256") for r in existing.values()}
    archive_id = archive.name
    with zipfile.ZipFile(archive) as z:
        files = sorted(
            [i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith(".pdf")],
            key=lambda i: (Path(i.filename).name.lower().startswith("dupe_"), i.filename.casefold()))
        attempted = imported = duplicates = 0
        errors = []
        # Retry failures last, without permanently blocking them.
        files.sort(key=lambda i: (int(i.file_size > MAX_MEMBER_SIZE),
                                  bool(state["failures"].get(archive_id+"::"+i.filename)),
                                  i.filename.casefold()))
        for item in files:
            key = archive_id + "::" + item.filename
            if key in state["completed"]:
                continue
            if attempted >= batch:
                break
            attempted += 1
            try:
                if item.file_size > MAX_MEMBER_SIZE:
                    raise ValueError("Unusually large PDF member (>80 MiB); manual inspection required")
                with tempfile.TemporaryDirectory() as td:
                    pdf = Path(td) / "source.pdf"
                    digest = hashlib.sha256()
                    written = 0
                    with z.open(item) as source, pdf.open("wb") as target:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > MAX_MEMBER_SIZE:
                                raise ValueError("Uncompressed file exceeds safety limit")
                            digest.update(chunk)
                            target.write(chunk)
                    if not pdf.read_bytes()[:4] == b"%PDF":
                        raise ValueError("ZIP member is not a PDF")
                    sha = digest.hexdigest()
                    if sha in known_hashes:
                        duplicates += 1
                        state["duplicates"][key] = sha
                    else:
                        record = inspector(pdf, Path(item.filename).name, hashlib.sha256(key.encode()).hexdigest())
                        record["source_identity"] = key
                        record["source_archive"] = archive_id
                        record["source_member"] = item.filename
                        record["content_sha256"] = sha
                        record["extraction_version"] = EXTRACTION_VERSION
                        record["pricing_eligible"] = False
                        record["quality"] = "needs_manual_verification"
                        existing[key] = record
                        known_hashes.add(sha)
                        imported += 1
                state["completed"][key] = sha
                state["failures"].pop(key, None)
            except Exception as exc:
                state["failures"][key] = type(exc).__name__ + ": " + str(exc)[:180]
                errors.append(item.filename + ": " + state["failures"][key])
    now = datetime.now(timezone.utc).isoformat()
    queue["recipes"] = sorted(existing.values(), key=lambda r:r.get("title_extracted","").casefold())
    queue["metadata"] = {"source":"Plated GitHub Release", "archive":archive_id,
                         "updated_at_utc":now,"count":len(queue["recipes"]),
                         "status":"manual_review_required"}
    completed = sum(1 for i in files if archive_id+"::"+i.filename in state["completed"])
    outstanding = len(files)-completed
    progress = {"updated_at_utc":now, "archive":archive_id, "pdf_members":len(files),
                "completed_members":completed, "remaining_members":outstanding,
                "attempted_this_run":attempted, "imported_this_run":imported,
                "duplicate_files_this_run":duplicates,
                "duplicates_total":len(state["duplicates"]),
                "records_in_review":len(queue["recipes"]),
                "failures_pending":len(state["failures"]),
                "errors_this_run":errors[:20], "pricing_eligible":0,
                "complete":outstanding==0 and not state["failures"]}
    save(statefile, state)
    save(queuefile, queue)
    save(progressfile, progress)
    print(json.dumps(progress, ensure_ascii=False))
    return progress

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",required=True)
    parser.add_argument("--batch",type=int,default=60)
    args=parser.parse_args()
    if not 1<=args.batch<=100:parser.error("--batch must be 1..100")
    run(args.archive,batch=args.batch)
