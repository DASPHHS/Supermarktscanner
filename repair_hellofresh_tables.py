"""Recover all six source columns from the first (non-overlaid) PDF text table.

Never infer a two-person quantity by halving the four-person column. This tool
does not approve recipes or manufacture package weights for sachets and cans.
"""
import argparse
import json
import re
from pathlib import Path
from sync_prices import number

UNITS=r'(?:stuk\(s\)|pak\(ken\)|blik\(?:ken\)|[a-zA-Z]+\(s\)|g|ml|el|tl)'
UNIT_RE=re.compile(r'\((?:g|ml|el|tl|[^()]+\([^()]+\))\)')
NUMBER=re.compile(r'\d+(?:[.,]\d+)?[¼½¾⅓⅔⅛⅜⅝⅞]?|[¼½¾⅓⅔⅛⅜⅝⅞]')

def extract_table(text):
    start=text.find('Ingrediënten voor 1 - 6 personen')
    if start<0: raise ValueError('Geen zeskolomstabel gevonden')
    text=text[start:].split('* in de koelkast bewaren',1)[0]
    text=text.split('Voedingswaarden',1)[0]
    # Drop a second text layer; never combine overlapping representations.
    text=text.split('Ingrediënten voor 1 - 6 personen',2)[1]
    text=re.sub(r'^\s*1p\s*2p\s*3p\s*4p\s*5p\s*6p\s*','',text)
    cursor=0;rows=[]
    for unit in UNIT_RE.finditer(text):
        label=' '.join(text[cursor:unit.end()].split())
        pantry='Zelf toevoegen' in label
        label=label.split('Zelf toevoegen')[-1].strip()
        following=text[unit.end():]
        m=re.match(r'\s*((?:[\d.,¼½¾⅓⅔⅛⅜⅝⅞]+\s*)+)',following)
        if not m: raise ValueError('Geen hoeveelheden voor '+label)
        values=NUMBER.findall(m.group(1))
        if len(values)!=6: raise ValueError('Geen zes eenduidige hoeveelheden voor '+label+': '+repr(values))
        if not label or len(label)>160 or not (label[0].isalpha() or label[0]=='['):raise ValueError('Ongeldig ingrediëntlabel: '+label[:80])
        numeric=[number(v) for v in values]
        if any(v is None for v in numeric) or any(a>b for a,b in zip(numeric,numeric[1:])):
            raise ValueError('Niet-oplopende bronhoeveelheden; beschadigde breuk of kolom controleren: '+label)
        rows.append({'ingredient':label.replace('*',''),'quantities_source':values,
                     'self_add':pantry or bool(rows and rows[-1]['self_add'])})
        cursor=unit.end()+m.end()
    tail=' '.join(text[cursor:].split())
    if not rows: raise ValueError('Lege tabel')
    # Retain unquantified pantry items; they must remain missing price inputs.
    cursor=0
    for item in re.finditer(r'(.+?)\s+(naar smaak|scheutje)(?:\s+|$)',tail):
        label=item.group(1).strip()
        rows.append({'ingredient':label+' ('+item.group(2)+')','quantities_source':[None]*6,'self_add':True})
        cursor=item.end()
    if tail[cursor:].strip():raise ValueError('Onverwerkte tabeltekst: '+tail[cursor:][:120])
    return rows

def main():
    import fitz
    ap=argparse.ArgumentParser();ap.add_argument('pdf_dir',type=Path);ap.add_argument('--repo',type=Path,default=Path('.'))
    args=ap.parse_args();file=args.repo/'recipes_extracted.json'
    key=lambda s:re.sub(r'[^a-z0-9]','',s.casefold())
    data=json.loads(file.read_text());files={key(p.name.split('-',1)[-1]):p for p in args.pdf_dir.glob('*.pdf')}
    changed=[];rejected=[]
    for r in data['recipes']:
        path=files.get(key(r.get('source_file','')))
        if not path: continue
        # Re-running a stricter parser must not preserve an earlier repair that
        # it now rejects. Keep the original OCR record as the explicit fallback.
        if 'ingredients_before_table_repair' in r:
            r['ingredients_4p']=r['ingredients_before_table_repair']
            for field in ('ingredients_2p','ingredient_source_columns','table_repair'):r.pop(field,None)
        try:
            doc=fitz.open(path);page=int(r['source_page_ingredients'])
            text=doc[page-1].get_text();rows=extract_table(text)
            header='Ingrediënten voor 1 - 6 personen'
            second=text.find(header,text.find(header)+len(header))
            if second>=0:
                try:other=extract_table(text[second:])
                except ValueError:other=None
                if other is not None:
                    # '&' versus 'en' is a label-style difference, not a new item.
                    signature=lambda table:[(key(x['ingredient'].replace('&','en')),[number(v) if v is not None else None for v in x['quantities_source']]) for x in table]
                    if signature(rows)!=signature(other):raise ValueError('Twee PDF-tekstlagen verschillen; visuele broncontrole nodig')
        except (ValueError,KeyError,IndexError) as exc:
            rejected.append({'id':r['id'],'reason':str(exc)});continue
        r['ingredients_before_table_repair']=r.get('ingredients_before_table_repair',r['ingredients_4p'])
        r['ingredients_4p']=[{'ingredient':x['ingredient'],'quantity_4p_source':x['quantities_source'][3]} for x in rows]
        r['ingredients_2p']=[{'ingredient':x['ingredient'],'quantity_2p_source':x['quantities_source'][1]} for x in rows]
        r['ingredient_source_columns']=rows
        r['table_repair']={'method':'first text layer; six source columns; no scaling','source_page':page,'rows':len(rows),'manual_review_required':True}
        # Any existing sign-off concerns the old incomplete table and is invalid.
        r['quality']='needs_manual_verification';r['pricing_eligible']=False
        for flag in ('ingredients_verified','quantities_verified','servings_verified'):r[flag]=False
        changed.append({'id':r['id'],'title':r['title_extracted'],'old_rows':len(r['ingredients_before_table_repair']),'new_rows':len(rows)})
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    report={'repaired':changed,'rejected':rejected,'manual_verifications':0}
    (args.repo/'hellofresh_table_repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Repaired',len(changed),'rejected',len(rejected),'new rows',sum(x['new_rows']-x['old_rows'] for x in changed))
if __name__=='__main__':main()
