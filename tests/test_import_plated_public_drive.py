import hashlib
import json
from import_plated_public_drive import run

def fake_inspect(path, name, identity):
    return {"title_extracted": name, "source_file": name,
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "ingredients_4p": [], "quality": "unverified",
            "extraction_version": 2, "pricing_eligible": False}

def test_same_title_different_contents_not_lost(tmp_path):
    manifest = {"files": [
        {"id": "a", "name": "Chicken Curry.pdf"},
        {"id": "b", "name": "dupe_Chicken Curry (1).PDF"},
        {"id": "c", "name": "Salmon Rice.pdf"}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    def fetch(identity, target):
        target.write_bytes(b"%PDF-1.4-" + identity.encode())
    first = run(str(path), root=tmp_path, batch=1, fetcher=fetch, inspector=fake_inspect)
    second = run(str(path), root=tmp_path, batch=5, fetcher=fetch, inspector=fake_inspect)
    third = run(str(path), root=tmp_path, batch=5, fetcher=fetch, inspector=fake_inspect)
    assert first["new_records_this_run"] == 1
    assert second["new_records_this_run"] == 2
    assert third["new_records_this_run"] == 0
    assert third["unique_title_candidates"] == 2
    assert third["records_in_queue"] == 3
    assert third["pricing_eligible"] == 0
    assert third["manifest_files_completed"] == 3

def test_exact_content_duplicates_are_collapsed(tmp_path):
    manifest = {"files": [
        {"id": "a", "name": "Curry.pdf"},
        {"id": "b", "name": "dupe_Curry.pdf"}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    def fetch(identity, target):
        target.write_bytes(b"%PDF-1.4-same")
    result = run(str(path), root=tmp_path, batch=9, fetcher=fetch, inspector=fake_inspect)
    assert result["records_in_queue"] == 1
    assert result["exact_duplicates_this_run"] == 1
    assert result["manifest_files_completed"] == 2

def test_failed_source_retries_without_blocking_others(tmp_path):
    manifest = {"files": [
        {"id": "a", "name": "A.pdf"},
        {"id": "b", "name": "B.pdf"}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    def fetch(identity, target):
        if identity == "a":
            raise RuntimeError("Temporary 429")
        target.write_bytes(b"%PDF-1.4-ok")
    for _ in range(4):
        result = run(str(path), root=tmp_path, batch=2, fetcher=fetch, inspector=fake_inspect)
    assert result["blocked_after_three_failures"] == 0
    assert result["failures_retryable"] == 1
    assert result["records_in_queue"] == 1
    assert result["manifest_files_completed"] == 1
