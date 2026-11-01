#!/usr/bin/env python3
"""Import the complete published Weekdeals promotional feed for HelloFresh.

Read-only upstream: DASPHHS/specialedeals/weekdeals/deals.json.
Only current supermarket food promotions are published. A product promotion
is a candidate, NOT a verified ingredient substitution or recipe discount.
"""
from __future__ import annotations

import argparse
import json
import math
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://dasphhs.github.io/specialedeals/weekdeals/deals.json"
FALLBACK_URL = "https://raw.githubusercontent.com/DASPHHS/specialedeals/main/weekdeals/deals.json"
OUTPUT = Path(__file__).resolve().parents[1] / "weekdeals_hellofresh.json"
STORES = {"Albert Heijn": "AH", "Jumbo": "Jumbo", "Lidl": "Lidl"}
FOOD_CATEGORIES = (
    "groente-fruit", "vlees", "vis", "vega", "kaas", "zuivel-eieren",
    "soepen-conserven-sauzen", "pasta-rijst-wereldkeuken",
    "diepvries", "brood-bakkerij", "ontbijt",
)

def number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    return value if math.isfinite(value) else None

def read_weekdeals():
    for url in (URL, FALLBACK_URL):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "HelloFreshWeekdeals/1.0 (+https://github.com/DASPHHS/Supermarktscanner)",
            })
            with urllib.request.urlopen(req, timeout=65) as res:
                return json.load(res)
        except (OSError, ValueError, TimeoutError) as exc:
            print(f"Source unavailable: {url}: {exc}")
    raise RuntimeError("No usable Weekdeals publication; keeping the previous file")

def transform(data, now=None):
    now = now or datetime.now(ZoneInfo("Europe/Amsterdam"))
    if not isinstance(data, dict) or data.get("source") != "PrijsProfeet":
        raise ValueError("Unexpected Weekdeals source")
    published = data.get("deals")
    if not isinstance(published, list) or not isinstance(data.get("total_published"), int):
        raise ValueError("Invalid Weekdeals records/count")
    if len(published) != data["total_published"] or len(published) < 100:
        raise ValueError("Incomplete Weekdeals list; keeping prior snapshot")
    try:
        updated = datetime.fromisoformat(data["updated_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid timestamp") from exc
    if updated.tzinfo is None:
        raise ValueError("Timestamp lacks timezone")
    age = now.astimezone(timezone.utc) - updated.astimezone(timezone.utc)
    if not timedelta(0) <= age < timedelta(hours=48):
        raise ValueError("Weekdeals source not fresh enough")
    today = now.date().isoformat()
    shops = {key: {"deals": []} for key in ("AH", "Jumbo", "Lidl")}
    active_all = {key: 0 for key in shops}
    seen = set()
    for d in published:
        if not isinstance(d, dict) or d.get("winkel") not in STORES:
            continue
        shop = STORES[d["winkel"]]
        start, end = d.get("van"), d.get("tot")
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        try:
            if date.fromisoformat(start) > now.date() or date.fromisoformat(end) < now.date():
                continue
        except ValueError:
            continue
        active_all[shop] += 1
        if d.get("categorie") not in FOOD_CATEGORIES:
            continue
        price = number(d.get("prijs"))
        if price is None or price <= 0 or not isinstance(d.get("product"), str):
            continue
        ident = d.get("id")
        if not isinstance(ident, str) or not ident or (shop, ident) in seen:
            continue
        seen.add((shop, ident))
        discount = number(d.get("korting"))
        discount_text = (
            f"{100*discount:.1f}% korting"
            if discount is not None and 0 < discount <= 1
            else "Actieve aanbieding"
        )
        multibuy = d.get("bundelaantal")
        multibuy = multibuy if type(multibuy) is int and multibuy > 1 else None
        shops[shop]["deals"].append({
            "product_id": ident,
            "name": d["product"],
            "price": price,
            "original_price": number(d.get("van_prijs")),
            "discount": discount_text,
            "valid_from": start,
            "valid_until": end,
            "product_url": d.get("url") if isinstance(d.get("url"), str)
                           and d["url"].startswith("https://") else None,
            "quantity": d.get("verpakking") if isinstance(d.get("verpakking"), str) else None,
            "category": d["categorie"],
            "promotion_type": d.get("actievorm") if isinstance(d.get("actievorm"), str) else None,
            "multi_buy_quantity": multibuy,
            # Weekdeals public JSON does not contain an independently verified bundle total.
            "multi_buy_price": None,
            # Member pricing is flagged, not assumed to be an unconditional checkout price.
            "card_required": False,
            "loyalty_warning": number(d.get("ledenprijs")) is not None,
            "personal_offer": False,
        })
    if sum(len(s["deals"]) for s in shops.values()) < 100 or any(
        len(s["deals"]) == 0 for s in shops.values()
    ):
        raise ValueError("Food offer coverage too low or a retailer missing")
    return {
        "schema_version": 1,
        "source": "DASPHHS/specialedeals Weekdeals / PrijsProfeet",
        "source_url": "https://dasphhs.github.io/specialedeals/weekdeals/",
        "updated_at_utc": updated.astimezone(timezone.utc).isoformat(),
        "as_of_date": today,
        "coverage": {
            "full_promotional_feed": True,
            "all_retailer_active": active_all,
            "food_category_filtered": True,
            "categories": sorted(FOOD_CATEGORIES),
            "include_only_current": True,
            "not_complete_store_assortment": True,
        },
        "stores": shops,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = transform(read_weekdeals())
    counts = {k: len(v["deals"]) for k, v in data["stores"].items()}
    print(f"Weekdeals food offers: {counts}; source={data['updated_at_utc']}")
    if args.check:
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                   encoding="utf-8")
    tmp.replace(OUTPUT)

if __name__ == "__main__":
    main()
