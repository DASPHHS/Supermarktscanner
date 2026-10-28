import hashlib
import json
import zipfile
from pathlib import Path
from import_plated_release import run

def archive(path, files):
    with zipfile.ZipFile(path,"w") as z:
        for name,data in files:
            z.writestr(name,data)

def inspector(path,name,identity):
    return {"id":identity,"title_extracted":name,"source_file":name,
            "content_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "ingredients_4p":[],"pricing_eligible":False}

def test_duplicates_and_resume(tmp_path):
    path=tmp_path/"Plated-test.zip"
    archive(path,[("A/Curry.pdf",b"%PDF-1.4-one"),
                  ("B/Curry.pdf",b"%PDF-1.4-two"),
                  ("B/dupe_Curry.pdf",b"%PDF-1.4-one")])
    first=run(path,tmp_path,1,inspector)
    assert first["completed_members"]==1
    second=run(path,tmp_path,10,inspector)
    assert second["completed_members"]==3
    assert second["records_in_review"]==2
    assert second["duplicates_total"]==1
    assert second["complete"] is True
    third=run(path,tmp_path,10,inspector)
    assert third["attempted_this_run"]==0

def test_bad_pdf_retry_and_safety(tmp_path):
    path=tmp_path/"Plated-test.zip"
    archive(path,[("bad.pdf",b"notpdf"),("valid.pdf",b"%PDF-1.4-good")])
    result=run(path,tmp_path,10,inspector)
    assert result["completed_members"]==1
    assert result["failures_pending"]==1
    assert not result["complete"]
    queue=json.loads((tmp_path/"plated_release_review_queue.json").read_text())
    assert all(r["pricing_eligible"] is False for r in queue["recipes"])
