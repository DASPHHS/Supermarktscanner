"""Audit every indexed HelloFresh and Plated recipe; NEVER attest visual/OCR accuracy.

Read local source files; no scraping or copying HelloFresh web content.
Missing and inconsistent quantities remain review items, not inferred values.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata


def read(root: Path, filename: str):
    return json.loads((root / filename).read_text(encoding="utf-8"))


def normalized(s):
    s = unicodedata.normalize("NFKD", str(s or "").casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def ingredient_row(row, label="ingredient", quantity="quantity_2p_source"):
    if not isinstance(row, dict):
        return False, False
    name = row.get(label)
    amount = row.get(quantity)
    return bool(isinstance(name, str) and name.strip()), bool(
        isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0
        or isinstance(amount, str) and bool(normalized(amount)) and
        normalized(amount) not in ("unknown", "onbekend", "none", "niet bekend", "n a", "naar smaak")
    )


def analyze(root: Path, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    hf = read(root, "recipes_extracted.json").get("recipes", [])
    plated = read(root, "plated_release_review_queue.json").get("recipes", [])
    nl = read(root, "plated_nl_catalog.json").get("recipes", [])
    hf_pages = read(root, "hellofresh/preview_manifest.json").get("recipes", {})
    pl_pages = read(root, "hellofresh/plated_preview_manifest.json").get("recipes", {})
    translated = {r.get("source_identity"): r for r in nl}
    records = []
    keys = Counter()
    issues = Counter()
    total_rows = 0
    amount_rows = 0
    sources = Counter()
    for source, items in (("HelloFresh", hf), ("Plated", plated)):
        for item in items:
            title = str(item.get("title_extracted") or "").strip()
            original_id = str(item.get("id") or "")
            rid = original_id if source == "HelloFresh" else "plated-release-" + str(item.get("source_identity") or "")
            key = source + "|" + normalized(title)
            keys[key] += 1
            reason = []
            if not title:
                reason.append("title_missing")
            if not original_id or (source == "Plated" and not item.get("source_identity")):
                reason.append("identity_missing")
            preview = (hf_pages if source == "HelloFresh" else pl_pages).get(rid) or {}
            has_card = bool(preview.get("front") and preview.get("original_pdf"))
            if not has_card:
                reason.append("original_card_missing")
            rows = []
            if source == "HelloFresh":
                rows = item.get("ingredients_2p") or item.get("ingredients_4p") or []
                quantity_field = "quantity_2p_source" if item.get("ingredients_2p") else "quantity_4p_source"
                labels = [(r, "ingredient", quantity_field) for r in rows]
            else:
                trans = translated.get(item.get("source_identity")) or {}
                rows = trans.get("ingredients_nl") or item.get("ingredients_4p") or []
                if trans.get("ingredients_nl"):
                    labels = [(r, "name_nl", "quantity_display_nl") for r in rows]
                else:
                    labels = [(r, "ingredient", "quantity_4p_source") for r in rows]
                if trans.get("servings_source") not in (2, 4):
                    reason.append("portions_unconfirmed")
                if any(r.get("quantity_basis") == "source_servings_not_verified"
                       for r in trans.get("ingredients_nl", []) if isinstance(r, dict)):
                    if "portions_unconfirmed" not in reason:
                        reason.append("portions_unconfirmed")
            present = len(labels)
            good_labels, good_amounts = 0, 0
            for row, name_field, quantity_field in labels:
                name_ok, amount_ok = ingredient_row(row, name_field, quantity_field)
                good_labels += int(name_ok)
                good_amounts += int(amount_ok)
            total_rows += present
            amount_rows += good_amounts
            if not present:
                reason.append("ingredients_missing")
            else:
                if good_labels < present:
                    reason.append("ingredient_names_incomplete")
                if good_amounts < present:
                    reason.append("quantities_incomplete")
            # Important: source matching and OCR structure do not amount to
            # human review. Do not derive 'verified' from a recipe title.
            certified = (item.get("quality") == "verified"
                         and item.get("ingredients_verified") is True
                         and item.get("quantities_verified") is True
                         and item.get("servings_verified") is True
                         and has_card and not reason)
            if not certified:
                reason.append("human_source_review_required")
            # No official-site match is inferred solely from the title.
            issues.update(reason)
            sources[source] += 1
            records.append({
                "id": rid, "source": source, "title": title[:200],
                "ingredient_rows": present, "ingredient_names_present": good_labels,
                "quantity_rows_present": good_amounts, "original_card_present": has_card,
                "source_review_confirmed": bool(certified),
                "original_pdf": preview.get("original_pdf") if isinstance(preview.get("original_pdf"), str) and re.fullmatch(r"(?:previews|plated-previews)/[a-zA-Z0-9_-]+-origineel\.pdf", preview["original_pdf"]) else None,
                "issues": sorted(set(reason)),
            })
    for record in records:
        if keys[record["source"] + "|" + normalized(record["title"])] > 1:
            record["issues"].append("duplicate_title_variant")
            issues["duplicate_title_variant"] += 1
    total = len(records)
    confirmed = sum(r["source_review_confirmed"] for r in records)
    has_ingredients = sum(r["ingredient_rows"] > 0 for r in records)
    names_complete = sum(r["ingredient_rows"] > 0 and
                         r["ingredient_rows"] == r["ingredient_names_present"] for r in records)
    quantities_complete = sum(r["ingredient_rows"] > 0 and
                              r["ingredient_rows"] == r["quantity_rows_present"] for r in records)
    with_card = sum(r["original_card_present"] for r in records)
    return {
        "schema_version": 1,
        "generated_at_utc": now.astimezone(timezone.utc).isoformat(),
        "mode": "structural_review_only_no_official_recipe_content_copied",
        "summary": {
            "records_audited": total,
            "by_source": dict(sources),
            "title_records": sum(bool(x["title"]) for x in records),
            "with_original_card": with_card,
            "with_ingredient_rows": has_ingredients,
            "ingredient_names_structurally_complete": names_complete,
            "quantity_rows_structurally_complete": quantities_complete,
            "ingredient_rows_inspected": total_rows,
            "ingredient_quantity_rows_present": amount_rows,
            "human_source_review_confirmed": confirmed,
            "require_human_review": total - confirmed,
            "issues": dict(issues),
        },
        "disclaimer": "Automatische controle van aanwezige velden en bronverwijzing; geen visuele verificatie van PDF of gelijkheid met HelloFresh.nl. Meerdere versies delen soms een titel.",
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="hellofresh/library_source_audit.json")
    args = parser.parse_args()
    output = analyze(Path(args.root))
    if output["summary"]["records_audited"] < 1:
        raise SystemExit("Empty recipe library; refusing to publish a blank audit")
    if output["summary"]["records_audited"] != sum(output["summary"]["by_source"].values()):
        raise SystemExit("Audit coverage mismatch")
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
