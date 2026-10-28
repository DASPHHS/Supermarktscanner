"""Publish readable original Plated card previews for queued PDF scans."""
import argparse, hashlib, io, json, subprocess, tempfile, zipfile
from pathlib import Path
from PIL import Image
from pypdf import PdfReader,PdfWriter

def data(path,default):
 p=Path(path)
 return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
def raster(pdf,page,target):
 stem=target.with_suffix("")
 p=subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),"-singlefile",
                   "-scale-to","1450","-png",str(pdf),str(stem)],
                  capture_output=True,text=True,timeout=120)
 png=stem.with_suffix(".png")
 if p.returncode or not png.exists():raise RuntimeError("PDF render failed "+p.stderr[:140])
 with Image.open(png) as im:im.convert("RGB").save(target,"WEBP",quality=82,method=4)
 png.unlink(missing_ok=True)
def run(archive,queue,root="hellofresh",batch=20):
 archive=Path(archive);root=Path(root)
 manifestpath=root/"plated_preview_manifest.json"
 m=data(manifestpath,{"recipes":{},"metadata":{}})
 m.setdefault("recipes",{})
 out=root/"plated-previews"
 out.mkdir(exist_ok=True,parents=True)
 records=data(queue,{}).get("recipes",[])
 added=0
 failures=[]
 with zipfile.ZipFile(archive) as z:
  available=set(z.namelist())
  for r in records:
   identity=r.get("source_identity")
   member=r.get("source_member")
   if not identity or not member:continue
   key="plated-release-"+identity
   if key in m["recipes"]:continue
   if added>=batch:break
   if member not in available:
    failures.append(member+" not found in ZIP")
    continue
   stem=hashlib.sha256(identity.encode()).hexdigest()[:18]
   try:
    with tempfile.TemporaryDirectory() as td:
     path=Path(td)/"source.pdf"
     with z.open(member) as inp, path.open("wb") as f:
      total=0
      while True:
       chunk=inp.read(1024*1024)
       if not chunk:break
       total+=len(chunk)
       if total>80*1024*1024:raise ValueError("Oversized PDF")
       f.write(chunk)
     reader=PdfReader(str(path))
     writer=PdfWriter()
     preview={}
     for page,label in ((1,"front"),(2,"ingredients")):
      if page>len(reader.pages):continue
      writer.add_page(reader.pages[page-1])
      target=out/(stem+"-"+label+".webp")
      raster(path,page,target)
      preview[label]="plated-previews/"+target.name
     if not preview:raise ValueError("Empty PDF")
     pdf=out/(stem+"-origineel.pdf")
     with pdf.open("wb") as file:writer.write(file)
     preview["original_pdf"]="plated-previews/"+pdf.name
     m["recipes"][key]=preview
     added+=1
   except Exception as e:
    failures.append(member+": "+str(e)[:120])
    for p in out.glob(stem+"-*"):p.unlink(missing_ok=True)
 m["metadata"]={"rendered":len(m["recipes"]),"queue_count":len(records),
                "status":"source PDF page copies; OCR not verified",
                "failures_this_run":failures[:15]}
 manifestpath.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"created":added,"total":len(m["recipes"]),"queue_count":len(records),"failures":failures[:5]}))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--archive",required=True)
 p.add_argument("--queue",default="plated_release_review_queue.json")
 p.add_argument("--root",default="hellofresh")
 p.add_argument("--batch",type=int,default=20)
 o=p.parse_args()
 run(o.archive,o.queue,o.root,o.batch)
