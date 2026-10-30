"""Verified two-person supermarket rankings: never promote OCR or indicative prices.

Checkjebon and PrijsProfeet are discovery feeds, not proof of current shelf prices.
Only manually validated recipes and recently checked official-store product prices
can appear in the ranking. Unconfirmed actions are never applied.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from sync_prices import amount

STORES = ("Lidl", "Jumbo", "AH")
OFFICIAL = {"Lidl": "lidl.nl", "Jumbo": "jumbo.com", "AH": "ah.nl"}
MAX_AGE = timedelta(hours=48)


def read(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def timestamp(raw):
    try:
        value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def fresh(raw, now):
    at = timestamp(raw)
    return at is not None and timedelta(0) <= now - at <= MAX_AGE


def official_url(url, store):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        domain = OFFICIAL[store]
        if parsed.scheme != "https" or host not in (domain, "www." + domain):
            return None
        if not parsed.path or parsed.path == "/" or parsed.username or parsed.password or parsed.port:
            return None
        return (host, parsed.path.rstrip("/").lower())
    except ValueError:
        return None


def valid_recipe(recipe):
    return (recipe.get("quality") == "verified"
            and recipe.get("pricing_eligible") is True
            and recipe.get("ingredients_verified") is True
            and recipe.get("quantities_verified") is True
            and recipe.get("servings_verified") is True
            and recipe.get("servings") == 4
            and bool(recipe.get("ingredients_2p"))
            and all(row.get("ingredient") and row.get("quantity_2p_source")
                    for row in recipe["ingredients_2p"]))


def finite_positive(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def verified_match(match, store, evidence, now):
    """Require an exact official URL, pack size, price and fresh human check."""
    if match.get("status") == "voorraad":
        return (str(match.get("ingredient", "")).lower().startswith("water")
                and match.get("cost") == 0)
    if match.get("action") or not finite_positive(match.get("package_price")):
        return False
    if not isinstance(match.get("packages"), int) or match["packages"] < 1:
        return False
    if not finite_positive(match.get("cash_cost")) or not finite_positive(match.get("used_cost")):
        return False
    if abs(match["cash_cost"] - match["packages"] * match["package_price"]) > .011:
        return False
    if match["used_cost"] > match["cash_cost"] + .011:
        return False
    link = official_url(match.get("link"), store)
    if not link:
        return False
    original_size = amount(match.get("package_size"))
    if original_size[0] is None:
        return False
    for item in evidence:
        if item.get("store") != store or not item.get("checked_by") or not fresh(item.get("checked_at_utc"), now):
            continue
        if official_url(item.get("product_url"), store) != link:
            continue
        if not finite_positive(item.get("price_eur")) or abs(item["price_eur"] - match["package_price"]) > .001:
            continue
        size = amount(item.get("quantity"))
        if size[0] is not None and size[1] == original_size[1] and abs(size[0] - original_size[0]) < .001:
            return True
    return False


def verdict(recipe, record, store, evidence, now):
    if not valid_recipe(recipe):
        return "recept_niet_handmatig_gevalideerd"
    if not record:
        return "prijsrecord_ontbreekt"
    if (record.get("store") != store or record.get("recipe_id") != recipe.get("id")
            or record.get("complete") is not True or record.get("recipe_review_required") is True
            or record.get("servings") != 2 or record.get("missing")
            or record.get("ingredient_matches_complete") is not True):
        return "ingredienten_of_porties_onvolledig"
    matches = record.get("matches")
    if not isinstance(matches, list) or len(matches) != len(recipe["ingredients_2p"]):
        return "ingredienten_of_porties_onvolledig"
    if not all(verified_match(m, store, evidence, now) for m in matches):
        return "actuele_officiele_prijsbevestiging_ontbreekt"
    cash = record.get("whole_packages_eur")
    used = record.get("used_cost_eur")
    if not finite_positive(cash) or not finite_positive(used) or used > cash + .011:
        return "prijsberekening_onconsistent"
    tolerance = .005 * len(matches) + .001
    if abs(cash - sum(float(m.get("cash_cost", 0)) for m in matches)) > tolerance:
        return "prijsberekening_onconsistent"
    if abs(used - sum(float(m.get("used_cost", m.get("cost", 0))) for m in matches)) > tolerance:
        return "prijsberekening_onconsistent"
    return "goedgekeurd"


def build(root: Path, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    snapshot = read(root / "recipe_prices.json", {})
    hf = read(root / "recipes_extracted.json", {}).get("recipes", [])
    plated = read(root / "plated_release_review_queue.json", {}).get("recipes", [])
    evidence = read(root / "price_verifications.json", {}).get("products", [])
    if not isinstance(evidence, list):
        raise ValueError("price_verifications.json products must be a list")
    snapshot_fresh = fresh(snapshot.get("fetched_at_utc"), now)
    indexed = {(r.get("recipe_id"), r.get("store")): r for r in snapshot.get("results", [])}
    stores = {}
    for store in STORES:
        counts = Counter()
        accepted = []
        missing_examples = []
        for recipe in hf:
            record = indexed.get((recipe.get("id"), store))
            reason = (verdict(recipe, record, store, evidence, now) if snapshot_fresh
                      else "prijssnapshot_verlopen_of_ontbreekt")
            counts[reason] += 1
            if reason == "goedgekeurd":
                accepted.append({"recipe_id": recipe["id"],
                                 "title": recipe.get("title_extracted", ""),
                                 "source": "HelloFresh", "servings": 2,
                                 "whole_packages_eur": record["whole_packages_eur"],
                                 "used_cost_eur": record["used_cost_eur"],
                                 "products": [{"ingredient": m.get("ingredient"),
                                               "product": m.get("product"),
                                               "product_url": m.get("link"),
                                               "package_price_eur": m.get("package_price"),
                                               "packages": m.get("packages")}
                                              for m in record["matches"] if m.get("status") != "voorraad"]})
            elif record and record.get("missing") and len(missing_examples) < 8:
                missing_examples.append({"recipe_id": recipe.get("id"),
                                         "title": recipe.get("title_extracted"),
                                         "missing": [m.get("ingredient") for m in record["missing"][:5]]})
        # Plated is preserved, but its unverified OCR cannot use HelloFresh's price schema.
        counts["plated_nog_niet_prijsgeschikt"] += len(plated)
        accepted.sort(key=lambda x: (x["whole_packages_eur"], x["used_cost_eur"], x["title"].casefold()))
        stores[store] = {"verified_count": len(accepted), "target": 10,
                         "top10": accepted[:10], "blocked_counts": dict(counts),
                         "missing_ingredient_examples": missing_examples}
    return {"generated_at_utc": now.isoformat(),
            "price_snapshot_fetched_at_utc": snapshot.get("fetched_at_utc"),
            "price_snapshot_fresh": snapshot_fresh,
            "policy": {"ranking": "actual checkout total for all required packages, 2 people",
                       "sources": "Only individually verified recipe cards and manually checked official-store product prices",
                       "price_confirmation_max_age_hours": 48,
                       "promotions": "No promotions used without separate manual validation",
                       "missing": "Never infer missing ingredients, quantities, prices or rankings",
                       "estimates": "Indicative estimates are never included in this verified ranking"},
            "library_counts": {"HelloFresh": len(hf), "Plated": len(plated)},
            "stores": stores}


def run(root: Path, now=None):
    output = build(root, now)
    (root / "verified_rankings.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = run(Path(args.root))
    print("Verified two-person checkout top 10:",
          {k: v["verified_count"] for k, v in result["stores"].items()})
