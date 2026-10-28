import hashlib
from pathlib import Path
from unittest.mock import patch
from drive_plated_sync import title_key, serving_options, ingredient_lines, provisional_four, sync

def test_name_deduplication():
    assert title_key("dupe_Fish Tacos (1).PDF")==title_key("Fish Tacos.pdf")

def test_four_portion_math():
    assert serving_options("2 servings") == [2]
    assert provisional_four(["10 ounces salmon","2 cloves garlic"],2)==[
      {"ingredient":"salmon","quantity_4p_source":"20 ounces","original_quantity":"10 ounces","quality":"unverified_ocr"},
      {"ingredient":"garlic","quantity_4p_source":"4 cloves","original_quantity":"2 cloves","quality":"unverified_ocr"}]
    assert provisional_four(["10 ounces salmon"],4)[0]["quantity_4p_source"]=="10 ounces"
    assert provisional_four(["10 ounces salmon"],None)==[]

def test_ingredient_blocks():
    assert ingredient_lines("WHAT WE SEND\n10 ounces salmon\n2 cloves garlic\nWHAT YOU'LL NEED\nolive oil")==["10 ounces salmon","2 cloves garlic"]

class Call:
    def __init__(self,v): self.v=v
    def execute(self): return self.v
class Files:
    def list(self,**kwargs):
        return Call({"files":[{"id":"a","name":"Salmon Soup.PDF","modifiedTime":"2026-10-28"},
                              {"id":"b","name":"dupe_Salmon Soup (1).PDF","modifiedTime":"2026-10-28"}]})
class Drive:
    def files(self): return Files()

def test_incremental_resume(tmp_path):
    def download(_,id,path):path.write_bytes(b"mock")
    def inspect(_,name,identity):
        return {"id":"x","title_extracted":"Salmon Soup","drive_identity_hash":identity,
                "content_sha256":hashlib.sha256(b"mock").hexdigest(),
                "ingredients_4p":[],"quality":"needs_manual_verification","pricing_eligible":False}
    with patch("drive_plated_sync.download",download),patch("drive_plated_sync.inspect",inspect):
        r1=sync(Drive(),"folder",batch=10,root=tmp_path)
        r2=sync(Drive(),"folder",batch=10,root=tmp_path)
    assert r1["batch_imported"]==1
    assert r2["batch_imported"]==0
    assert r2["queue_count"]==1
    assert r2["price_eligible_from_queue"]==0
