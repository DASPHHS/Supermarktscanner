"""Validate Plated recipe servings, US units and document duplicates.

This validation layer is intentionally conservative: volume cups and pieces
must not silently become grams; uncertain vendor packet/can sizes block pricing.
"""
from __future__ import annotations
import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

GRAMS_PER_OUNCE=Decimal("28.349523125")
ML_PER_FLUID_OUNCE=Decimal("29.5735295625")
ML_PER_US_CUP=Decimal("236.5882365")
ML_PER_US_TBSP=Decimal("14.78676478125")
ML_PER_US_TSP=Decimal("4.92892159375")

def parse_amount(text):
    """Parse common vulgar fractions, ASCII fractions and mixed US amounts."""
    text=str(text).strip().translate(str.maketrans({"¼":"1/4","½":"1/2","¾":"3/4","⅓":"1/3","⅔":"2/3","⅛":"1/8","⅜":"3/8","⅝":"5/8","⅞":"7/8"}))
    text=re.sub(r"(\d)(\d/\d)",r"\1 \2",text)
    text=text.replace("–","-")
    if "-" in text and not text.startswith("-"):
        raise ValueError("Range cannot be an exact amount")
    parts=text.split()
    if not 1<=len(parts)<=2:
        raise ValueError("Expected simple or mixed fraction")
    try:
        result=sum((Fraction(x) for x in parts),Fraction(0,1))
    except (ValueError,ZeroDivisionError) as e:
        raise ValueError("Invalid amount") from e
    if result<=0:
        raise ValueError("Quantity must be positive")
    return result

def exact_amount_string(amount):
    whole, rem=divmod(amount.numerator,amount.denominator)
    if rem==0:return str(whole)
    return (f"{whole} " if whole else "")+f"{rem}/{amount.denominator}"

def scale_amount(original_amount, source_servings, target_servings=4):
    if not isinstance(source_servings,int) or source_servings<1:
        raise ValueError("Source servings must be independently verified")
    return exact_amount_string(parse_amount(original_amount)*Fraction(target_servings,source_servings))

def normalized_metric(amount, unit):
    """Return grams or mL for unambiguous US measures only."""
    a=Decimal(parse_amount(amount).numerator)/Decimal(parse_amount(amount).denominator)
    u=unit.strip().lower()
    factors={"oz":(GRAMS_PER_OUNCE,"g"),"ounce":(GRAMS_PER_OUNCE,"g"),
             "ounces":(GRAMS_PER_OUNCE,"g"),"lb":(GRAMS_PER_OUNCE*16,"g"),
             "fl oz":(ML_PER_FLUID_OUNCE,"ml"),"fluid ounce":(ML_PER_FLUID_OUNCE,"ml"),
             "cup":(ML_PER_US_CUP,"ml"),"cups":(ML_PER_US_CUP,"ml"),
             "tbsp":(ML_PER_US_TBSP,"ml"),"tablespoon":(ML_PER_US_TBSP,"ml"),
             "tsp":(ML_PER_US_TSP,"ml"),"teaspoon":(ML_PER_US_TSP,"ml")}
    if u not in factors: return None
    factor,metric=factors[u]
    return {"quantity":str((a*factor).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)),"unit":metric,
            "note":"Volume conversions are to mL, not ingredient-specific grams" if metric=="ml" else ""}

def duplicate_groups(folder):
    """Byte-identical PDFs only; same-title recipes need manual review."""
    groups=defaultdict(list)
    for file in sorted(Path(folder).rglob("*")):
        if file.is_file() and file.suffix.casefold()==".pdf":
            digest=hashlib.sha256()
            with file.open("rb") as fh:
                for chunk in iter(lambda:fh.read(1024*1024),b""):
                    digest.update(chunk)
            groups[digest.hexdigest()].append(str(file))
    return {digest:files for digest,files in groups.items() if len(files)>1}

def check_recipe(recipe):
    flags=list(recipe.get("audit_flags",[]))
    if recipe.get("original_servings") not in (2,4):
        flags.append("Original serving count must be visually confirmed")
    if recipe.get("servings")!=4:
        flags.append("Four servings required")
    for ingredient in recipe.get("ingredients_4p",[]):
        v=ingredient.get("quantity_4p_source","")
        if not v.strip():
            flags.append("Missing four-portion amount for "+ingredient.get("ingredient","?"))
        if re.search(r"(packet|zakje|blik|can|stuks|piece)",v,re.I) and not ingredient.get("package_net_weight_grams"):
            flags.append("Package or piece weight unknown for "+ingredient.get("ingredient","?"))
    return sorted(set(flags))

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("json_file")
    p.add_argument("--duplicate-folder",default=None)
    p.add_argument("--out",default="plated_validation_report.json")
    opts=p.parse_args()
    d=json.loads(Path(opts.json_file).read_text(encoding="utf-8"))
    report={"recipes":[],"duplicates_by_sha256":duplicate_groups(opts.duplicate_folder) if opts.duplicate_folder else {}}
    for r in d.get("recipes",[]):
        flags=check_recipe(r)
        report["recipes"].append({"id":r.get("id"),"title":r.get("title_extracted"),
                                  "review_flags":flags,"pricing_eligible":False})
    Path(opts.out).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Validated",len(report["recipes"]),"reactions; no automatic pricing approvals")

if __name__=="__main__":
    main()
