"""Import Plated PDF cards into a review queue; never auto-approve OCR."""
import argparse
import json
import re
import subprocess
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path

PDF_SUFFIX = {".pdf"}
HEADER_PATTERNS = (r"WHAT WE SEND", r"INGREDIENTS(?:\s*&\s*EQUIPMENT)?", r"INGREDIENTS")
STOP_PATTERNS = (r"WHAT YOU.LL NEED", r"YOU.LL NEED", r"COOKING STEPS", r"RECIPE TIPS", r"ALLERGENS", r"RECIPE CARD")

def canonical_title(name):
    s = Path(name).stem
    s = re.sub(r"^dupe_", "", s, flags=re.I)
    s = re.sub(r"(?:\s*\(\d+\)|_card|_OCR)+$", "", s, flags=re.I)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())

def run_command(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr[:200]}")
    return result.stdout

def extract_text(pdf):
    try:
        text = run_command(["pdftotext", "-layout", str(pdf), "-"])
        if len(text.strip()) >= 150:
            return text, "embedded_text"
    except (FileNotFoundError, RuntimeError):
        pass
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "page"
        try:
            run_command(["pdftoppm", "-r", "190", "-gray", "-png", str(pdf), str(out)])
            texts = [run_command(["tesseract", str(p), "stdout", "-l", "eng"])
                     for p in sorted(Path(folder).glob("page-*.png"))]
        except (FileNotFoundError, RuntimeError) as exc:
            return "", f"ocr_unavailable:{exc}"
        return "\n".join(texts), "ocr_unverified"

def extract_ingredient_lines(text):
    lines = [s.strip() for s in text.splitlines()]
    chunks = []
    in_section = False
    for line in lines:
        if any(re.search(p, line, re.I) for p in HEADER_PATTERNS) and (
            re.search(r"WHAT WE SEND", line, re.I) or re.match(r"^[^\w]*INGREDIENTS", line, re.I)
        ):
            in_section = True
            continue
        if in_section and any(re.search(p, line, re.I) for p in STOP_PATTERNS):
            if chunks:
                break
        if in_section and line and len(line) < 100:
            chunks.append(line)
        if len(chunks) > 65:
            break
    return chunks

def classify(title):
    t = title.lower()
    if re.search(r"chicken|turkey", t): return "kip"
    if re.search(r"salmon|fish|cod|shrimp|tuna|trout|scallop", t): return "vis"
    if re.search(r"steak|beef|pork|lamb|bacon|sausage", t): return "vlees"
    return "vega_or_unknown"

def read_recipes(folder):
    groups = defaultdict(list)
    for pdf in sorted(Path(folder).rglob("*")):
        if pdf.is_file() and pdf.suffix.lower() in PDF_SUFFIX:
            groups[canonical_title(pdf.name)].append(pdf)
    result = []
    for key, candidates in sorted(groups.items()):
        # Prefer originals without the duplicate prefix, then the largest file.
        pdf = sorted(candidates, key=lambda p:(p.name.lower().startswith("dupe_"), -p.stat().st_size))[0]
        text, method = extract_text(pdf)
        ing = extract_ingredient_lines(text)
        result.append({
            "id": "plated-" + key[:72],
            "source": "Plated",
            "title_extracted": pdf.stem.replace("dupe_", ""),
            "source_file": pdf.name,
            "duplicate_files": [p.name for p in candidates if p != pdf],
            "category": classify(pdf.stem),
            "ocr_method": method,
            "ingredient_candidates_original": ing,
            "ingredient_candidates_4p": [],
            "servings_original": None,
            "servings_target": 4,
            "quality": "needs_manual_verification",
            "pricing_eligible": False,
            "review_flags": [
                "Original serving count requires visual confirmation",
                "Ingredient lines and units require manual correction",
                "Four-portion values must be audited before pricing"
            ] if ing else ["No reliable ingredient block extracted; inspect PDF visually"]
        })
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Local directory containing Plated PDFs")
    parser.add_argument("--out", default="plated_import_queue.json")
    args = parser.parse_args()
    recipes = read_recipes(args.folder)
    output = {
        "metadata": {"source":"Plated","quality":"unverified","recipe_count":len(recipes),
                     "note":"Review queue only. No recipe is price eligible without manual validation."},
        "recipes":recipes
    }
    Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(recipes)} unique candidate recipes written to {args.out}; 0 approved for pricing")

if __name__ == "__main__":
    main()
