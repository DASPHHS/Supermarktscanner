from pathlib import Path
from import_plated_public_drive import run

def test_batch_resume_and_quality_gate(tmp_path):
    data={"files":[{"id":"a","name":"Chicken Curry.pdf"},
                   {"id":"b","name":"dupe_Chicken Curry (1).PDF"},
                   {"id":"c","name":"Salmon Rice.pdf"}]}
    (tmp_path/"manifest.json").write_text(__import__("json").dumps(data))
    def fake_fetch(id,path):path.write_bytes(b"%PDF-1.4-"+id.encode())
    def fake_inspect(path,name,identity):
        import hashlib
        return {"title_extracted":name,"source_file":name,
                "content_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "ingredients_4p":[],"quality":"unverified","pricing_eligible":False}
    first=run(str(tmp_path/"manifest.json"),root=tmp_path,batch=1,fetcher=fake_fetch,inspector=fake_inspect)
    second=run(str(tmp_path/"manifest.json"),root=tmp_path,batch=5,fetcher=fake_fetch,inspector=fake_inspect)
    third=run(str(tmp_path/"manifest.json"),root=tmp_path,batch=5,fetcher=fake_fetch,inspector=fake_inspect)
    assert first["new_records_this_run"]==1
    assert second["new_records_this_run"]==1
    assert third["new_records_this_run"]==0
    assert third["unique_title_candidates"]==2
    assert third["pricing_eligible"]==0
