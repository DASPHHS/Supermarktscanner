import json
from pathlib import Path
from merge_plated_results import merge_files

def save(path,data):
    path.write_text(json.dumps(data),encoding="utf-8")

def test_merges_queue_without_losing_records(tmp_path):
    latest=tmp_path/"latest";latest.mkdir()
    local=tmp_path/"new";local.mkdir()
    a={"source_identity":"a","title_extracted":"Apple","extraction_version":1,"ingredients_4p":[],"pricing_eligible":False}
    av2={"source_identity":"a","title_extracted":"Apple","extraction_version":2,
         "ingredients_4p":[{"ingredient":"apple","quantity_4p_source":"2 stuks"}],"pricing_eligible":False}
    b={"source_identity":"b","title_extracted":"Banana","extraction_version":2,"ingredients_4p":[],"pricing_eligible":False}
    save(latest/"plated_drive_public_review_queue.json",{"recipes":[a],"metadata":{}})
    save(local/"plated_drive_public_review_queue.json",{"recipes":[av2,b],"metadata":{}})
    save(latest/"plated_drive_public_state.json",{"completed":{"a":"v1"},"errors":{}})
    save(local/"plated_drive_public_state.json",{"completed":{"a":"v2","b":"v1"},"errors":{}})
    save(local/"plated_drive_public_progress.json",{"records_in_queue":2,"pricing_eligible":0})
    merge_files(local,latest)
    items=json.loads((latest/"plated_drive_public_review_queue.json").read_text())["recipes"]
    assert len(items)==2
    assert next(x for x in items if x["source_identity"]=="a")["extraction_version"]==2
    assert all(x["pricing_eligible"] is False for x in items)
    state=json.loads((latest/"plated_drive_public_state.json").read_text())
    assert state["completed"]=={"a":"v2","b":"v1"}
    progress=json.loads((latest/"plated_drive_public_progress.json").read_text())
    assert progress["records_in_queue"]==2
