"""Publish readable original Plated card previews for queued PDF scans."""
import argparse, hashlib, json, shutil, subprocess, tempfile, zipfile
from pathlib import Path
from PIL import Image
from pypdf import PdfReader

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
  # Publish missing cards first, then replace legacy reserialized PDFs with
  # byte-identical source copies. Both phases are resumable via source_sha256.
  def entry(r):
   return m["recipes"].get("plated-release-"+r.get("source_identity",""),{})
  pending=[r for r in records if r.get("source_identity") and r.get("source_member")
           and not entry(r).get("all_pages_in_pdf")]
  legacy=[r for r in records if r.get("source_identity") and r.get("source_member")
          and entry(r).get("all_pages_in_pdf") and not entry(r).get("source_sha256")]
  for r in pending+legacy:
   identity=r.get("source_identity")
   member=r.get("source_member")
   if not identity or not member:continue
   key="plated-release-"+identity
   old_entry=m["recipes"].get(key,{})
   legacy_copy=bool(old_entry.get("all_pages_in_pdf"))
   if legacy_copy and old_entry.get("source_sha256"):continue
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
     if not reader.pages:raise ValueError("Empty PDF")
     preview=dict(old_entry)
     if not legacy_copy:
      for page,label in ((1,"front"),(2,"ingredients")):
       if page>len(reader.pages):continue
       target=out/(stem+"-"+label+".webp")
       raster(path,page,target)
       preview[label]="plated-previews/"+target.name
     # PdfWriter reserializes the document and can discard metadata or
     # attachments. Publish the original PDF bytes, atomically, instead.
     pdf=out/(stem+"-origineel.pdf")
     temporary=out/(stem+"-origineel.pdf.tmp")
     shutil.copyfile(path,temporary)
     temporary.replace(pdf)
     preview["all_pages_in_pdf"]=True
     preview["source_pdf_page_count"]=len(reader.pages)
     preview["original_pdf"]="plated-previews/"+pdf.name
     preview["source_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
     m["recipes"][key]=preview
     added+=1
   except Exception as e:
    failures.append(member+": "+str(e)[:120])
    (out/(stem+"-origineel.pdf.tmp")).unlink(missing_ok=True)
    # Never delete previously published source cards on a failed retry.
    if not old_entry:
     for p in out.glob(stem+"-*"):p.unlink(missing_ok=True)
 m["metadata"]={"rendered":len(m["recipes"]),"queue_count":len(records),
                "byte_identical_originals":sum(bool(v.get("source_sha256")) for v in m["recipes"].values()),
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
