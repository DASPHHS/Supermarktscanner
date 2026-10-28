"""Render original HelloFresh recipe card pages as low-bandwidth web previews.

Source PDFs are read from explicitly uploaded GitHub Release ZIPs. No OCR
corrections are inferred from the image; this is original-page provenance.
"""
import argparse, io, json, subprocess, tempfile, zipfile
from pathlib import Path
from PIL import Image
from pypdf import PdfReader, PdfWriter

ASSETS={
 "hellofresh1.zip":"https://github.com/DASPHHS/Supermarktscanner/releases/download/plated-database-v1/hellofresh1.zip",
 "hellofresh.2.zip":"https://github.com/DASPHHS/Supermarktscanner/releases/download/plated-database-v1/hellofresh.2.zip",
}
def load(p,default):
 p=Path(p)
 return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
def build_index(archives):
 result={}
 for archive in archives:
  with zipfile.ZipFile(archive) as z:
   for i in z.infolist():
    if i.is_dir() or not i.filename.lower().endswith(".pdf"):continue
    key=Path(i.filename).name.casefold()
    result.setdefault(key,[]).append((Path(archive),i.filename))
 return result
def image_page(pdf,page,target):
 tmp=target.with_suffix(".png")
 result=subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),"-singlefile",
                         "-scale-to","1500","-png",str(pdf),str(tmp.with_suffix(""))],
                         capture_output=True,text=True,timeout=100)
 if result.returncode or not tmp.is_file():
  raise RuntimeError("render failed: "+result.stderr[:150])
 with Image.open(tmp) as im:
  im.convert("RGB").save(target,"WEBP",quality=83,method=4)
 tmp.unlink(missing_ok=True)

def run(archives,recipes_file,root,batch=24):
 root=Path(root)
 manifest_file=root/"preview_manifest.json"
 current=load(manifest_file,{"metadata":{},"recipes":{}})
 current.setdefault("recipes",{})
 source=load(recipes_file,{})["recipes"]
 indexed=build_index(archives)
 output=root/"previews"
 output.mkdir(parents=True,exist_ok=True)
 made=0
 missing=[]
 for recipe in source:
  id=recipe.get("id")
  if id in current["recipes"] and current["recipes"][id].get("original_pdf"):continue
  filename=recipe.get("source_file","")
  choices=indexed.get(filename.casefold(),[])
  if not choices:
   missing.append(filename)
   continue
  if made>=batch:break
  archive,member=choices[0]
  try:
   with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"source.pdf"
    with zipfile.ZipFile(archive) as z, z.open(member) as fh, p.open("wb") as out:
     while True:
      chunk=fh.read(2*1024*1024)
      if not chunk:break
      out.write(chunk)
    result=dict(current["recipes"].get(id,{}))
    for label,page in (("front",recipe.get("source_page_front")),("ingredients",recipe.get("source_page_ingredients"))):
     if not isinstance(page,int) or page<1:continue
     target=output/(id+"-"+label+".webp")
     if not target.exists():image_page(p,page,target)
     result[label]="previews/"+target.name
    if not any(k in result for k in ("front","ingredients")):
     raise ValueError("No valid source page references")
    pages=sorted({recipe.get("source_page_front"),recipe.get("source_page_ingredients")}- {None})
    reader=PdfReader(str(p)); writer=PdfWriter()
    for page in pages:
     if not isinstance(page,int) or not 1<=page<=len(reader.pages):
      raise ValueError("Invalid source page "+str(page))
     writer.add_page(reader.pages[page-1])
    pdf_target=output/(id+"-origineel.pdf")
    with pdf_target.open("wb") as out:writer.write(out)
    result["original_pdf"]="previews/"+pdf_target.name
    current["recipes"][id]={"source_file":filename,
                            "archive":archive.name,"member":member,
                            "source_pages":{"front":recipe.get("source_page_front"),
                                            "ingredients":recipe.get("source_page_ingredients")},
                            **result}
    made+=1
  except Exception as exc:
   missing.append(filename+" ("+str(exc)[:120]+")")
   for label in ("front","ingredients","origineel"):
    (output/(id+"-"+label+(".pdf" if label=="origineel" else ".webp"))).unlink(missing_ok=True)
 current["metadata"]={"rendered":len(current["recipes"]),"recipes_total":len(source),
                      "missing_source_files":sorted(set(missing))[:40],
                      "downloadable_original_pdfs":sum(bool(r.get("original_pdf")) for r in current["recipes"].values()),
                      "status":"original PDF pages rendered; OCR not manually verified"}
 manifest_file.write_text(json.dumps(current,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(json.dumps({"rendered_this_run":made,"rendered_total":len(current["recipes"]),
                   "recipes_total":len(source),"missing_sources":len(set(missing))}))
 return current

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--archives",nargs="+",required=True)
 p.add_argument("--recipes",default="recipes_extracted.json")
 p.add_argument("--root",default="hellofresh")
 p.add_argument("--batch",type=int,default=24)
 x=p.parse_args()
 run(x.archives,x.recipes,x.root,x.batch)
