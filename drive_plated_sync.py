"""Incremental Drive->Plated OCR review queue. Never approves unverified prices."""
import argparse,hashlib,json,os,re,subprocess,tempfile,unicodedata
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction

DEFAULT_FOLDER="1gXrQK_EM3QvWPMYvGDze8TmpvD0MZP3K"
def title_key(name):
    x=re.sub(r"^dupe_","",Path(name).stem,flags=re.I)
    x=re.sub(r"(?:\s*\(\d+\)|_card|_ocr)+$","",x,flags=re.I)
    x=unicodedata.normalize("NFKD",x)
    return re.sub("[^a-z0-9]","", "".join(c for c in x if not unicodedata.combining(c)).lower())
def command(argv):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=180)
    if p.returncode: raise RuntimeError(argv[0]+": "+p.stderr[:200])
    return p.stdout
def pdf_text(path):
    """Prefer existing text, then OCR individual bounded-size pages.

    Some unusually large scanned PDFs time out when Poppler rasterizes the
    first three pages in one command. Process pages independently and preserve
    any successful result; never imply extraction was verified.
    """
    try:
        raw=command(["pdftotext","-layout",str(path),"-"])
        if len(raw.strip())>250 and re.search(r"WHAT WE SEND|INGREDIENTS",raw,re.I):
            return raw,"pdf_text"
    except (subprocess.TimeoutExpired,RuntimeError):
        raw=""
    parts=[]
    failures=[]
    with tempfile.TemporaryDirectory() as td:
        # Plated ingredients are usually on the second page; first page
        # sometimes carries the serving count, and third is a fallback.
        for page in (2,1,3):
            target=Path(td)/("page-"+str(page))
            try:
                command(["pdftoppm","-f",str(page),"-l",str(page),
                         "-singlefile","-scale-to","1350","-gray","-png",
                         str(path),str(target)])
                rendered=target.with_suffix(".png")
                text=command(["tesseract",str(rendered),"stdout","-l","eng","--psm","3"])
                if text.strip():
                    parts.append(text)
            except (subprocess.TimeoutExpired,RuntimeError) as exc:
                failures.append(str(page)+": "+type(exc).__name__)
                continue
    if not parts:
        raise RuntimeError("All bounded OCR pages failed: "+", ".join(failures))
    method="ocr_unverified_partial" if failures else "ocr_unverified"
    return "\n".join(parts),method
EXTRACTION_VERSION=2
def serving_options(raw):
    candidates=re.findall(r"\b([246])\s*servings?\b|\bserves\s*:?\s*([246])\s*(?:people|persons?|servings?)?\b",raw,re.I)
    return sorted({int(v) for pair in candidates for v in pair if v})
def ingredient_lines(raw):
    """Plated cards normally put INGREDIENTS *after* cooking steps and tips.

    Also accepts WHAT WE SEND for web-derived cards; all ingredients remain
    unverified until checked against the original PDF layout.
    """
    active=False; lines=[]
    for rawline in raw.splitlines():
        line=rawline.strip()
        if re.search(r"(?:^|[^A-Z])INGREDIENTS\b|WHAT WE SEND",line,re.I) and len(line)<65:
            active=True
            continue
        if active and re.search(r"YOU.LL NEED|WHAT YOU.LL NEED|ALLERGENS|QUESTIONS OR COMMENTS|COOKING STEPS",line,re.I):
            if lines:break
        if active and line and len(line)<100:
            lines.append(line)
        if len(lines)>=85:break
    return lines
def provisional_four(lines,servings):
    """Parse only unambiguous OCR quantities; preserve original US unit.

    Unclear OCR fractions such as '2%' are deliberately excluded. Counts
    without a weight remain counts and must not be priced by grams.
    """
    if servings not in (2,4):return []
    result=[]
    chars={"¼":"1/4","½":"1/2","¾":"3/4","⅓":"1/3","⅔":"2/3","⅛":"1/8","⅜":"3/8","⅝":"5/8","⅞":"7/8"}
    units=r"ounces?|oz|lbs?|pounds?|cups?|tablespoons?|tbsp|teaspoons?|tsp|cloves?|cans?|packets?|pieces?|bunches?|sticks?|pints?"
    pattern=re.compile(r"^\s*(\d+(?:\s+\d+/\d+|/\d+|[¼½¾⅓⅔⅛⅜⅝⅞])?)\s+(?:(?P<unit>"+units+r")\s+)?(?P<name>[A-Za-z].{2,75})$",re.I)
    for line in lines:
        m=pattern.match(line)
        if not m or re.search(r"[%?]",line):continue
        raw=m.group(1)
        for key,value in chars.items():raw=raw.replace(key," "+value)
        try:
            quantity=sum((Fraction(p) for p in raw.split()),Fraction(0))*Fraction(4,servings)
        except (ValueError,ZeroDivisionError):continue
        if quantity<=0:continue
        original_unit=m.group("unit") or "stuks"
        total=str(quantity.numerator) if quantity.denominator==1 else f"{quantity.numerator}/{quantity.denominator}"
        result.append({"ingredient":m.group("name").strip(),
                       "quantity_4p_source":total+" "+original_unit,
                       "original_quantity":m.group(1)+" "+original_unit,
                       "quality":"unverified_ocr"})
    return result

def inspect(pdf,name,identity):
    raw,method=pdf_text(pdf);servings=serving_options(raw);lines=ingredient_lines(raw)
    original=servings[0] if len(servings)==1 else None
    return {"id":"plated-"+title_key(name)[:85],"source":"Plated",
            "title_extracted":re.sub(r"^dupe_","",Path(name).stem,flags=re.I),
            "source_file":name,"drive_identity_hash":identity,
            "content_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "ocr_method":method,"servings_original":original,"servings":4,
            "ingredient_candidates_original":lines,"ingredients_4p":provisional_four(lines,original),
            "extraction_version":EXTRACTION_VERSION,
            "quality":"needs_manual_verification","pricing_eligible":False,
            "review_flags":["Verify original PDF ingredient columns and serving count",
                            "Check all US units, package weights and pantry ingredients"]}
def listing(service,folder):
    token=None
    while True:
        result=service.files().list(q=f"'{folder}' in parents and trashed = false and mimeType = 'application/pdf'",
          fields="nextPageToken,files(id,name,size,md5Checksum,modifiedTime)",pageSize=1000,pageToken=token,
          supportsAllDrives=True,includeItemsFromAllDrives=True).execute()
        yield from result.get("files",[])
        token=result.get("nextPageToken")
        if not token:break
def download(service,id,path):
    from googleapiclient.http import MediaIoBaseDownload
    with path.open("wb") as dest:
        d=MediaIoBaseDownload(dest,service.files().get_media(fileId=id,supportsAllDrives=True),chunksize=4*1024*1024)
        finished=False
        while not finished:_,finished=d.next_chunk(num_retries=3)
def read(path,default):
    p=Path(path)
    return json.loads(p.read_text()) if p.exists() else default
def sync(service,folder,batch=12,root=Path(".")):
    state_path=root/"plated_sync_state.json";queue_path=root/"plated_review_queue.json";progress_path=root/"plated_sync_progress.json"
    state=read(state_path,{"done":{},"errors":{}})
    queue=read(queue_path,{"metadata":{},"recipes":[]})
    existing={r["drive_identity_hash"]:r for r in queue["recipes"] if r.get("drive_identity_hash")}
    hashes={r.get("content_sha256") for r in existing.values()}
    allfiles=list(listing(service,folder))
    selected=sorted(allfiles,key=lambda x:(x["name"].lower().startswith("dupe_"),x["name"].casefold()))
    seen=set();attempted=0;imported=0;errors=[]
    for f in selected:
        key=title_key(f["name"])
        if key in seen:continue
        seen.add(key)
        identity=hashlib.sha256(f["id"].encode()).hexdigest()
        version=f.get("md5Checksum") or f.get("modifiedTime") or ""
        if state["done"].get(identity)==version:continue
        if attempted>=batch:break
        attempted+=1
        try:
            with tempfile.TemporaryDirectory() as tmp:
                pdf=Path(tmp)/"input.pdf";download(service,f["id"],pdf)
                recipe=inspect(pdf,f["name"],identity)
            if recipe["content_sha256"] not in hashes:
                # Do not discard an existing manually reviewed card.
                if existing.get(identity,{}).get("quality") in ("verified","reviewed"):
                    recipe["review_flags"].append("Previously reviewed source changed; recheck")
                existing[identity]=recipe;hashes.add(recipe["content_sha256"]);imported+=1
            state["done"][identity]=version
            state["errors"].pop(identity,None)
        except Exception as err:
            msg=f["name"]+": "+type(err).__name__+": "+str(err)[:160]
            state["errors"][identity]=msg;errors.append(msg)
    queue["recipes"]=sorted(existing.values(),key=lambda x:x["title_extracted"].casefold())
    now=datetime.now(timezone.utc).isoformat()
    queue["metadata"]={"source":"Plated","updated_at":now,"count":len(queue["recipes"]),
                       "status":"unverified_extraction_not_price_eligible"}
    progress={"updated_at":now,"total_pdf_files":len(allfiles),"unique_title_candidates":len({title_key(f["name"]) for f in allfiles}),
              "batch_attempted":attempted,"batch_imported":imported,
              "queue_count":len(queue["recipes"]),"price_eligible_from_queue":0,
              "errors":errors[:20],"review_required":True}
    for path,value in [(state_path,state),(queue_path,queue),(progress_path,progress)]:
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(progress,ensure_ascii=False))
    return progress
def drive():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    raw=os.environ.get("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
    if not raw:raise RuntimeError("GitHub secret GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON ontbreekt")
    creds=service_account.Credentials.from_service_account_info(json.loads(raw),
      scopes=["https://www.googleapis.com/auth/drive.readonly"])
    return build("drive","v3",credentials=creds,cache_discovery=False)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--folder",default=os.environ.get("PLATED_DRIVE_FOLDER_ID") or DEFAULT_FOLDER)
    p.add_argument("--batch",type=int,default=12)
    args=p.parse_args()
    if not 1<=args.batch<=30:p.error("Batch must be 1-30")
    sync(drive(),args.folder,args.batch)
