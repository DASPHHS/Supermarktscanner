"""Second-pass OCR for Plated source cards missing ingredient candidates.

Non-destructive: reads original PDF in GitHub Release ZIP, OCRs the left
ingredient column of page 2 at 300 dpi, stores verbatim candidates and
does not approve prices or silently rewrite original extracted quantities.
"""
import argparse,hashlib,json,re,subprocess,tempfile,zipfile
from pathlib import Path

from drive_plated_sync import ingredient_lines,provisional_four

def load(path,default):
 p=Path(path)
 return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
def save(path,data):
 Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def left_column_ocr(pdf):
 # Native pdf text first. Plated cards use the left margin of page 2 for ingredients.
 text=subprocess.run(["pdftotext","-f","2","-l","2","-layout",str(pdf),"-"],
    capture_output=True,text=True,timeout=90)
 if text.returncode==0:
  lines=ingredient_lines(text.stdout)
  if len(lines)>=4 and any(re.match(r"^\s*\d",x) for x in lines):
   return lines,"native_pdf_page_2"
 with tempfile.TemporaryDirectory() as td:
  stem=Path(td)/"page"
  p=subprocess.run(["pdftoppm","-f","2","-l","2","-r","300","-singlefile","-png",str(pdf),str(stem)],
    capture_output=True,text=True,timeout=130)
  if p.returncode or not stem.with_suffix(".png").exists():
   raise ValueError("page 2 cannot be rendered")
  # Plated original cards generally show ingredients in the leftmost column.
  from PIL import Image,ImageOps,ImageEnhance
  with Image.open(stem.with_suffix(".png")) as im:
   left=im.convert("L").crop((0,0,int(im.width*0.30),int(im.height*0.77)))
   left=ImageOps.autocontrast(left)
   left=ImageEnhance.Contrast(left).enhance(1.4)
   target=Path(td)/"left.png";left.save(target)
  o=subprocess.run(["tesseract",str(target),"stdout","-l","eng","--psm","6"],
    capture_output=True,text=True,timeout=90)
  if o.returncode:raise ValueError("Tesseract ingredient column failed")
  lines=ingredient_lines(o.stdout)
  return lines,"ocr_left_page_2_300dpi"

def run(archive,queue="plated_release_review_queue.json",out="plated_ingredient_rescan.json",batch=35):
 sources=load(queue,{}).get("recipes",[])
 data=load(out,{"metadata":{},"records":{}})
 data.setdefault("records",{})
 missing=[r for r in sources if not r.get("ingredients_4p") and r.get("source_member")]
 # Repeated failures are retained and reconsidered in subsequent cycles.
 attempted=0;success=0;errors=[]
 with zipfile.ZipFile(archive) as z:
  for r in missing:
   key=r.get("source_identity") or r["source_member"]
   if key in data["records"] and data["records"][key].get("status")=="extracted":continue
   if attempted>=batch:break
   attempted+=1
   try:
    with tempfile.TemporaryDirectory() as td:
     pdf=Path(td)/"source.pdf"
     with z.open(r["source_member"]) as fh, pdf.open("wb") as target:
      size=0
      while True:
       b=fh.read(1024*1024)
       if not b:break
       size+=len(b)
       if size>80*1024*1024:raise ValueError("PDF too large")
       target.write(b)
     lines,method=left_column_ocr(pdf)
     # Quantity candidates are suggestions only, no automatic pricing eligibility.
     parse=provisional_four(lines,r.get("servings_original"))
    data["records"][key]={"status":"extracted" if lines else "needs_manual_check",
      "source_file":r.get("source_file"),"source_identity":key,
      "method":method,"ocr_ingredient_lines_unverified":lines[:60],
      "quantity_candidates_unverified":parse,
      "pricing_eligible":False,"requires_original_card_review":True}
    if lines:success+=1
   except Exception as exc:
    data["records"][key]={"status":"error","error":str(exc)[:200],
      "source_file":r.get("source_file"),"pricing_eligible":False}
    errors.append(r.get("source_file"))
 completed=sum(v.get("status")=="extracted" for v in data["records"].values())
 data["metadata"]={"source":"Second-pass 300dpi Plated ingredient column OCR",
   "review_queue_count":len(sources),"originally_empty_ingredients":len(missing),
   "rescan_with_candidate_lines":completed,"attempted_this_run":attempted,
   "new_candidates_this_run":success,"errors_this_run":errors[:15],
   "pricing_eligible":0,"status":"requires_manual_review"}
 save(out,data)
 print(json.dumps(data["metadata"],ensure_ascii=False))
 return data
if __name__=="__main__":
 parser=argparse.ArgumentParser()
 parser.add_argument("--archive",required=True)
 parser.add_argument("--queue",default="plated_release_review_queue.json")
 parser.add_argument("--out",default="plated_ingredient_rescan.json")
 parser.add_argument("--batch",type=int,default=35)
 opts=parser.parse_args()
 run(opts.archive,opts.queue,opts.out,opts.batch)
