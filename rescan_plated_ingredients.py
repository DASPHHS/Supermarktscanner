"""Layout-aware, provenance-preserving second pass for missing Plated ingredients.

Prefer the PDF text layer on the *ingredient page*, then optional 300 dpi OCR.
Parsed entries are candidates at the source serving size, NEVER approved 4p
quantities or price-eligible ingredient lines. Record every fallback and failure.
"""
import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from fractions import Fraction
from pathlib import Path

from drive_plated_sync import ingredient_lines
from plated_translate_nl import quantity_nl, translated_ingredient

EXTRACTION_VERSION = 3
MAX_PDF_BYTES = 80 * 1024 * 1024
VULGAR = {"½":"1/2","¼":"1/4","¾":"3/4","⅓":"1/3","⅔":"2/3",
          "⅛":"1/8","⅜":"3/8","⅝":"5/8","⅞":"7/8"}
UNITS = r"ounces?|oz|lbs?|pounds?|cups?|tablespoons?|tbsp|teaspoons?|tsp|cloves?|cans?|packets?|packages?|jars?|pieces?|bunches?|sticks?|pints?|slices?|heads?|ears?"
QUANTITY = re.compile(r"^\s*(?P<qty>\d+(?:\s+\d+/\d+|/\d+)?)\s+(?:(?P<unit>"+UNITS+r")\s+)?(?P<name>[A-Za-zÀ-ÿ][^\n]{1,95})\s*$",re.I)

def load(path,default):
    p=Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def save(path,data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def normalize_fractions(text):
    s=str(text).strip()
    for mark,value in VULGAR.items():
        s=s.replace(mark," "+value+" ")
    return " ".join(s.split())

def candidate(line):
    """Return source-quantity evidence; never infer servings, pack weights or prices."""
    line=str(line).strip().lstrip("•*●- ").strip()
    if any(ch in line for ch in ("?","%","�")):
        return None
    m=QUANTITY.match(normalize_fractions(line))
    if not m:
        return None
    try:
        val=sum((Fraction(x) for x in m.group("qty").split()),Fraction(0))
    except (ValueError,ZeroDivisionError):
        return None
    if not 0<val<=1000:
        return None
    ingredient=m.group("name").strip()
    if re.search(r"\b(?:preheat|oven|degrees|minute|stir|cook|bake|serve)\b",ingredient,re.I):
        return None
    unit=m.group("unit") or "stuks"
    # Preserve source quantity for audit; numeric conversions only for exact mass units.
    original=m.group("qty")+" "+unit
    translated=translated_ingredient(ingredient)
    amount=quantity_nl(original)
    return {"raw_line":str(line).strip(),"name_original":ingredient,
            "name_nl":translated["name_nl"],
            "canonical_nl":translated["canonical_nl"],
            "translation_status":translated["translation_status"],
            "quantity_source":original,**amount,
            "source_portions_not_verified":True,"pricing_eligible":False}

def scan_native(pdf,page):
    result=subprocess.run(["pdftotext","-f",str(page),"-l",str(page),
                           "-layout",str(pdf),"-"],
                          capture_output=True,text=True,timeout=60)
    if result.returncode:
        return []
    return ingredient_lines(result.stdout)

def render_ingredient_page(pdf,page,stem):
    """Retry oversized scans with bounded pixels after a 300 dpi timeout.

    The source PDF is never modified. A failed rasterization remains retryable.
    """
    target=stem.with_suffix(".png")
    for args,timeout in [
        (["-r","300"],130),
        (["-scale-to","1500","-gray"],90),
    ]:
        try:
            p=subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),
                              *args,"-singlefile","-png",str(pdf),str(stem)],
                             capture_output=True,text=True,timeout=timeout)
            if p.returncode==0 and target.exists():
                return target
        except subprocess.TimeoutExpired:
            continue
    raise RuntimeError("PDF page rasterization failed at 300dpi and bounded fallback")


def scan_ocr(pdf,page):
    from PIL import Image,ImageOps,ImageEnhance
    with tempfile.TemporaryDirectory() as td:
        stem=Path(td)/"page"
        image_path=render_ingredient_page(pdf,page,stem)
        with Image.open(image_path) as im:
            left=im.convert("L").crop((0,0,int(im.width*.36),int(im.height*.86)))
            left=ImageOps.autocontrast(left)
            left=ImageEnhance.Contrast(left).enhance(1.35)
            target=Path(td)/"left.png"
            left.save(target)
        o=subprocess.run(["tesseract",str(target),"stdout","-l","eng","--psm","6"],
                         capture_output=True,text=True,timeout=90)
        if o.returncode:
            return []
        return ingredient_lines(o.stdout)

def extract(pdf, native=scan_native, ocr=scan_ocr):
    """Choose the strongest clearly delimited ingredient column, not arbitrary prose."""
    options=[]
    # Plated cards usually put the Ingredients header in the left column of page 2.
    # Try another page if an alternative card format moved the ingredient block.
    for page in (2,1,3):
        lines=native(pdf,page)
        candidates=[v for line in lines if (v:=candidate(line)) is not None]
        options.append((len(candidates),page,"pdf_text_layout",lines,candidates))
        if len(candidates)>=3:
            break
    if max(x[0] for x in options)<3:
        for page in (2,1,3):
            lines=ocr(pdf,page)
            candidates=[v for line in lines if (v:=candidate(line)) is not None]
            options.append((len(candidates),page,"ocr_crop_300dpi",lines,candidates))
            if len(candidates)>=3:
                break
    count,page,method,lines,candidates=max(options,key=lambda x:x[0])
    return {"method":method,"page":page,"candidate_count":count,
            "ocr_ingredient_lines_unverified":lines[:80],
            "quantity_candidates_unverified":candidates[:60],
            "status":"extracted" if count>=2 else "needs_manual_check",
            "pricing_eligible":False,"requires_original_card_review":True}

def run(archive,queue="plated_release_review_queue.json",out="plated_ingredient_rescan.json",batch=60,extractor=extract):
    sources=load(queue,{}).get("recipes",[])
    data=load(out,{"metadata":{},"records":{}})
    data.setdefault("records",{})
    missing=[r for r in sources if not r.get("ingredients_4p") and r.get("source_member")]
    # A review-required item is not a perpetual retry. It is reconsidered on a
    # newer extraction version; actual exceptions may be retried next cycle.
    missing.sort(key=lambda r:bool(data["records"].get(r.get("source_identity"),{}).get("status")=="error"))
    attempted=0;created=0;errors=[]
    with zipfile.ZipFile(archive) as z:
        for r in missing:
            key=r.get("source_identity") or r["source_member"]
            prior=data["records"].get(key,{})
            if (prior.get("version")==EXTRACTION_VERSION and
                prior.get("status") in ("extracted","needs_manual_check")):
                continue
            if attempted>=batch:
                break
            attempted+=1
            try:
                with tempfile.TemporaryDirectory() as td:
                    pdf=Path(td)/"source.pdf"
                    with z.open(r["source_member"]) as source,pdf.open("wb") as target:
                        size=0
                        while True:
                            chunk=source.read(1024*1024)
                            if not chunk:break
                            size+=len(chunk)
                            if size>MAX_PDF_BYTES:
                                raise ValueError("PDF uncompressed size exceeds safety limit")
                            target.write(chunk)
                    if pdf.read_bytes()[:4]!=b"%PDF":
                        raise ValueError("ZIP member is not a PDF")
                    result=extractor(pdf)
                data["records"][key]={**result,"version":EXTRACTION_VERSION,
                  "source_file":r.get("source_file"),"source_identity":key}
                created+=result.get("status")=="extracted"
            except Exception as exc:
                # Preserve original OCR queue and retain explicit retryable errors.
                data["records"][key]={"version":EXTRACTION_VERSION,"status":"error",
                  "error":str(exc)[:200],"source_identity":key,
                  "source_file":r.get("source_file"),"pricing_eligible":False}
                errors.append(r.get("source_file"))
    active=[data["records"].get(r.get("source_identity") or r["source_member"],{})
            for r in missing]
    extracted=sum(v.get("status")=="extracted" for v in active)
    reviewed=sum(v.get("version")==EXTRACTION_VERSION and
                 v.get("status") in ("extracted","needs_manual_check") for v in active)
    data["metadata"]={"source":"Plated source PDF page/column with optional 300dpi OCR",
      "extraction_version":EXTRACTION_VERSION,
      "review_queue_count":len(sources),"originally_empty_ingredients":len(missing),
      "rescan_with_candidate_lines":extracted,
      "rescan_checked_current_version":reviewed,
      "remaining_to_attempt":len(missing)-reviewed,
      "attempted_this_run":attempted,"new_candidates_this_run":created,
      "errors_this_run":errors[:20],"pricing_eligible":0,
      "status":"candidate_extraction_not_human_verified"}
    save(out,data)
    print(json.dumps(data["metadata"],ensure_ascii=False))
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive",required=True)
    p.add_argument("--queue",default="plated_release_review_queue.json")
    p.add_argument("--out",default="plated_ingredient_rescan.json")
    p.add_argument("--batch",type=int,default=60)
    args=p.parse_args()
    run(args.archive,args.queue,args.out,args.batch)
