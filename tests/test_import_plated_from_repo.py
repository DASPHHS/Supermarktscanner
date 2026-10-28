import hashlib
from pathlib import Path
from unittest.mock import patch
from import_plated_from_repo import run

def test_scan_batch_and_resume(tmp_path):
    folder=tmp_path/"pdfs";folder.mkdir()
    (folder/"Fish Tacos.pdf").write_bytes(b"pdf-a")
    (folder/"dupe_Fish Tacos (1).pdf").write_bytes(b"pdf-a")
    (folder/"Chicken Soup.pdf").write_bytes(b"pdf-b")
    def inspect(pdf,name,identity):
        return {"id":name,"title_extracted":name,"drive_identity_hash":identity,
                "content_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),
                "ingredients_4p":[],"pricing_eligible":False}
    with patch("import_plated_from_repo.inspect",inspect):
        first=run(folder,batch=20,root=tmp_path)
        second=run(folder,batch=20,root=tmp_path)
    assert first["imported_this_run"]==2
    assert first["possible_title_duplicates"]==1
    assert second["imported_this_run"]==0
    assert second["pending_review"]==2
    assert second["pricing_eligible"]==0
