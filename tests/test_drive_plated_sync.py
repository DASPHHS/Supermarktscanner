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


def test_actual_plated_ocr_footer_and_servings():
    from drive_plated_sync import serving_options, ingredient_lines, provisional_four
    source = """Thai-Peanut Chicken Curry
Serves: 2 people
1. Cook Sticky Rice
4. Simmer Curry
@- INGREDIENTS
% ° cup sticky rice
3 cups baby spinach
2 boneless skinless chicken breasts
1 can lite coconut milk
2% tablespoons peanut butter
1 packet raw sugar
1 teaspoon gochujang
¥- YOU'LL NEED
kosher salt
"""
    assert serving_options(source)==[2]
    entries=ingredient_lines(source)
    assert len(entries)==7
    parsed=provisional_four(entries,2)
    amounts={x["ingredient"]:x["quantity_4p_source"] for x in parsed}
    assert amounts["baby spinach"]=="6 cups"
    assert amounts["boneless skinless chicken breasts"]=="4 stuks"
    assert amounts["lite coconut milk"]=="2 can"
    assert amounts["raw sugar"]=="2 packet"
    assert amounts["gochujang"]=="2 teaspoon"
    assert "peanut butter" not in amounts
    assert "sticky rice" not in amounts

def test_plated_original_four_servings_are_not_doubled():
    from drive_plated_sync import serving_options, provisional_four
    assert serving_options("Serves: 4 people")==[4]
    rows=provisional_four(["12 flour tortillas", "4 ounces salmon"],4)
    assert rows[0]["quantity_4p_source"]=="12 stuks"
    assert rows[1]["quantity_4p_source"]=="4 ounces"
