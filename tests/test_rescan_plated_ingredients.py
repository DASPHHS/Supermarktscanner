import json
import zipfile
from pathlib import Path

from rescan_plated_ingredients import candidate, extract, run

def test_unicode_fraction_and_ground_beef_are_not_lost():
    x=candidate("1½ pounds ground beef")
    assert x["canonical_nl"]=="rundergehakt"
    assert x["quantity_metric"]==680
    assert x["unit_metric"]=="g"
    assert x["pricing_eligible"] is False
    assert x["source_portions_not_verified"] is True

def test_american_fraction_without_integer():
    x=candidate("⅛ ounce mint")
    assert x is not None
    assert x["quantity_metric"]==4
    assert x["unit_metric"]=="g"

def test_ambiguous_layout_and_instruction_are_not_ingredients():
    assert candidate("1 5-inch squares puff pastry") is None
    assert candidate("5 minutes cook the beef") is None
    assert candidate("cheese") is None
    assert candidate("Y% cup flour") is None

def test_pdf_text_is_preferred_to_ocr_when_sufficient():
    native=lambda p,n:["INGREDIENTS","1½ pounds ground beef","2 cloves garlic",
                       "12 ounces green beans"] if n==2 else []
    calls=[]
    def ocr(p,n):
        calls.append(n)
        return []
    result=extract(Path("unused.pdf"),native=native,ocr=ocr)
    assert result["method"]=="pdf_text_layout"
    assert result["page"]==2
    assert result["candidate_count"]==3
    assert not calls

def test_ocr_fallback_when_pdf_text_is_unreadable():
    native=lambda p,n:[]
    ocr=lambda p,n:["2 ounces mushrooms","1 pound ground beef",
                     "3 cups stock"] if n==2 else []
    result=extract(Path("unused.pdf"),native=native,ocr=ocr)
    assert result["method"]=="ocr_crop_300dpi"
    assert result["page"]==2
    assert result["candidate_count"]==3

def test_resume_skips_final_review_needed_and_does_not_starve_other_sources(tmp_path):
    zip_path=tmp_path/"Plated.zip"
    with zipfile.ZipFile(zip_path,"w") as z:
        for n in ("a.pdf","b.pdf","c.pdf"):
            z.writestr(n,b"%PDF-1.4\nmock")
    queue=tmp_path/"queue.json"
    queue.write_text(json.dumps({"recipes":[
        {"source_identity":x,"source_member":x+".pdf","source_file":x+".pdf","ingredients_4p":[]}
        for x in ("a","b","c")]}))
    out=tmp_path/"rescan.json"
    def extract_none(pdf):
        return {"status":"needs_manual_check","quantity_candidates_unverified":[],
                "pricing_eligible":False}
    first=run(zip_path,queue,out,batch=1,extractor=extract_none)
    second=run(zip_path,queue,out,batch=1,extractor=extract_none)
    third=run(zip_path,queue,out,batch=1,extractor=extract_none)
    assert [a["metadata"]["rescan_checked_current_version"] for a in (first,second,third)]==[1,2,3]
    assert all(x.get("pricing_eligible") is False for x in third["records"].values())
    fourth=run(zip_path,queue,out,batch=5,extractor=extract_none)
    assert fourth["metadata"]["attempted_this_run"]==0


def test_oversized_ingredient_page_retries_at_bounded_resolution(tmp_path):
    import subprocess
    from unittest.mock import patch
    from rescan_plated_ingredients import render_ingredient_page
    calls=[]
    def fake_run(argv,**kwargs):
        calls.append(argv)
        if "-r" in argv:
            raise subprocess.TimeoutExpired(argv,kwargs["timeout"])
        Path(argv[-1]+".png").write_bytes(b"png")
        return subprocess.CompletedProcess(argv,0,"","")
    with patch("rescan_plated_ingredients.subprocess.run",fake_run):
        target=render_ingredient_page(tmp_path/"source.pdf",2,tmp_path/"page")
    assert target.exists()
    assert len(calls)==2
    assert "-r" in calls[0] and "-scale-to" in calls[1]


def test_unreadable_page_stays_an_explicit_retryable_error(tmp_path):
    import subprocess
    import pytest
    from unittest.mock import patch
    from rescan_plated_ingredients import render_ingredient_page
    def timeout(argv,**kwargs):
        raise subprocess.TimeoutExpired(argv,kwargs["timeout"])
    with patch("rescan_plated_ingredients.subprocess.run",timeout):
        with pytest.raises(RuntimeError,match="bounded fallback"):
            render_ingredient_page(tmp_path/"source.pdf",2,tmp_path/"page")
