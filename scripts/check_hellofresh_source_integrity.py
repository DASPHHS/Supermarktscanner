import json
from pathlib import Path
from collections import Counter

audit = json.loads((Path(__file__).resolve().parents[1] / "hellofresh/library_source_audit.json").read_text())
records = audit["records"]
hello = [r for r in records if r["source"] == "HelloFresh"]
ids = [r["id"] for r in records]
assert len(ids) == len(set(ids)), "Duplicate IDs"
assert len(records) == audit["summary"]["records_audited"]
assert len(hello) == audit["summary"]["by_source"]["HelloFresh"]
assert all(0 <= r["quantity_rows_present"] <= r["ingredient_rows"] for r in hello)
assert all(r["title"].strip() for r in hello)
issues = Counter(issue for r in hello for issue in r["issues"])
print("HelloFresh:", len(hello))
print("Missing ingredients:", issues["ingredients_missing"])
print("Incomplete quantities:", issues["quantities_incomplete"])
print("Original scans not published:", issues["original_scan_not_published"])
print("Manual verification still required:", sum(not r["source_review_confirmed"] for r in hello))
