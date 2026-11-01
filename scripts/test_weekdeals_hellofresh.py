import unittest
from datetime import datetime, timedelta, timezone

from sync_weekdeals_hellofresh import transform

NOW = datetime(2026, 11, 1, 12, 20, tzinfo=timezone.utc)
STAMP = (NOW - timedelta(minutes=20)).isoformat()

def offer(shop, name, category="groente-fruit", start="2026-10-28", end="2026-11-03", **kwargs):
    return {
        "id": f"prijsprofeet:{shop}:{name}",
        "winkel": shop, "product": name, "categorie": category,
        "van": start, "tot": end, "prijs": 1.49, "korting": 0.5,
        "url": "https://example.com/product", **kwargs,
    }

def payload(items):
    filler = [offer("Albert Heijn", f"Aardappelen {i}") for i in range(100)]
    records = filler + items
    return {"source": "PrijsProfeet", "updated_at": STAMP,
            "total_published": len(records), "deals": records}

class WeekdealsTests(unittest.TestCase):
    def test_filters_upcoming_expired_and_nonfood(self):
        data = payload([
            offer("Jumbo", "Kikkererwten 380 g"),
            offer("Lidl", "Aubergine"),
            offer("Jumbo", "Toekomst", start="2026-11-02", end="2026-11-08"),
            offer("Lidl", "Verlopen", start="2026-10-20", end="2026-10-30"),
            offer("Albert Heijn", "Vaatwasmiddel", category="huishouden"),
        ])
        x = transform(data, NOW)
        self.assertEqual(len(x["stores"]["AH"]["deals"]), 100)
        self.assertEqual(len(x["stores"]["Jumbo"]["deals"]), 1)
        self.assertEqual(len(x["stores"]["Lidl"]["deals"]), 1)
        self.assertTrue(x["coverage"]["food_category_filtered"])

    def test_multibuy_does_not_invent_bundle_price(self):
        x = transform(payload([
            offer("Jumbo", "Kikkererwten", bundelaantal=2, van_prijs=2.98),
            offer("Lidl", "Aubergine", ledenprijs=0.59),
        ]), NOW)
        d = x["stores"]["Jumbo"]["deals"][0]
        self.assertEqual(d["multi_buy_quantity"], 2)
        self.assertIsNone(d["multi_buy_price"])
        self.assertTrue(x["stores"]["Lidl"]["deals"][0]["loyalty_warning"])

    def test_incomplete_feed_rejected(self):
        data = payload([offer("Jumbo", "Peen"), offer("Lidl", "Ui")])
        data["total_published"] = 2
        with self.assertRaises(ValueError):
            transform(data, NOW)

    def test_missing_lidl_rejected(self):
        with self.assertRaises(ValueError):
            transform(payload([offer("Jumbo", "Peen")]), NOW)

    def test_stale_feed_rejected(self):
        data = payload([offer("Jumbo", "Peen"), offer("Lidl", "Ui")])
        data["updated_at"] = (NOW - timedelta(days=4)).isoformat()
        with self.assertRaises(ValueError):
            transform(data, NOW)

    def test_duplicate_ignored(self):
        identical = offer("Jumbo", "Kikkererwten 380 g")
        x = transform(payload([identical, identical, offer("Lidl", "Aubergine")]), NOW)
        self.assertEqual(len(x["stores"]["Jumbo"]["deals"]), 1)

if __name__ == "__main__":
    unittest.main()
