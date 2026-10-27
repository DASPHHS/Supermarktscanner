"""Pricing and recipe matching for supermarket offers. No invented live prices."""
import csv
import io
from datetime import date, datetime
from pathlib import Path

STORES = {"AH", "Jumbo", "Lidl"}
FIELDS = {"store", "product", "price_eur", "quantity_g", "valid_from", "valid_until"}

def read_offers(source, today=None):
    today = today or date.today()
    if hasattr(source, "read"):
        content = source.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
    else:
        content = Path(source).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    if not FIELDS.issubset(set(reader.fieldnames or [])):
        raise ValueError("Ontbrekende kolommen: " + ", ".join(sorted(FIELDS - set(reader.fieldnames or []))))
    rows = []
    for number, row in enumerate(reader, start=2):
        try:
            store = row["store"].strip()
            if store not in STORES:
                raise ValueError("onbekende supermarkt")
            product = row["product"].strip()
            if not product:
                raise ValueError("leeg product")
            price = float(row["price_eur"].replace(",", "."))
            grams = float(row["quantity_g"].replace(",", "."))
            start = date.fromisoformat(row["valid_from"].strip())
            end = date.fromisoformat(row["valid_until"].strip())
            if price < 0 or grams <= 0 or end < start:
                raise ValueError("ongeldige prijs, hoeveelheid of periode")
            if start <= today <= end:
                rows.append({"store": store, "product": product, "price_eur": price,
                             "quantity_g": grams, "valid_from": start.isoformat(),
                             "valid_until": end.isoformat(), "source_url": row.get("source_url", "").strip(),
                             "price_per_kg": round(price * 1000 / grams, 2)})
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Fout in CSV-regel {number}: {exc}") from exc
    return rows

def calculate_recipe(recipe, offers, store, servings=4):
    """Compute exact purchasable pack cost; unmatched ingredients remain explicitly unpriced."""
    total = 0.0
    missing = []
    matched = []
    for ingredient, grams in recipe["ingredients"].items():
        choices = [o for o in offers if o["store"] == store and o["product"].casefold() == ingredient.casefold()]
        if not choices:
            missing.append(ingredient)
            continue
        best = min(choices, key=lambda o: o["price_per_kg"])
        import math
        packs = math.ceil(grams / best["quantity_g"])
        cost = packs * best["price_eur"]
        total += cost
        matched.append({"ingredient": ingredient, "grams": grams, "packs": packs, "cost": round(cost, 2)})
    return {"name": recipe["name"], "store": store, "servings": servings,
            "known_total_eur": round(total, 2), "known_per_serving_eur": round(total / servings, 2),
            "missing": missing, "complete": not missing, "matched": matched}

RECIPES = [
    {"name": "Kip met broccoli en paprika", "ingredients": {"kipfilet": 700, "broccoli": 600, "paprika": 400}},
    {"name": "Kalkoen met courgette", "ingredients": {"kalkoenfilet": 700, "courgette": 800}},
    {"name": "Roerbak met tofu en broccoli", "ingredients": {"tofu": 800, "broccoli": 800}},
    {"name": "Tonijnsalade met komkommer", "ingredients": {"tonijn": 600, "komkommer": 600}},
    {"name": "Eieren met spinazie", "ingredients": {"eieren": 500, "spinazie": 800}},
]
