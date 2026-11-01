import io
import json
import unittest
from unittest.mock import patch
from hfresh_metadata import build_crossrefs, fetch_titles, incremental_batch, safe_recipe_url, title_key


class HFreshMetadataTests(unittest.TestCase):
    def test_exact_nl_title_only(self):
        local = [{"id": "hf-7", "title_extracted": "Héékfilet à la meunière"},
                 {"id": "hf-8", "title_extracted": "Andere maaltijd"}]
        external = [{"id": 101, "name": "Heekfilet a la meuniere",
                     "url": "https://hfresh.info/nl-NL/recipes/heekfilet-a-la-meuniere-101",
                     "total_time": 35, "headline": "met brood en salade", "ingredients": [{"name": "Vis"}],
                     "price_eur": 1.00, "quality": "verified"}]
        found = build_crossrefs(local, external)
        self.assertEqual(found["matched"], 1)
        entry = found["recipe_links"]["hf-7"]
        self.assertEqual(entry["total_time"], 35)
        self.assertEqual(entry["headline"], "met brood en salade")
        self.assertEqual(entry["match"], "exact_title_only")
        self.assertNotIn("ingredients", entry)
        self.assertNotIn("price_eur", entry)
        self.assertNotIn("quality", entry)
        self.assertNotIn("hf-8", found["recipe_links"])

    def test_ambiguous_source_title_not_matched(self):
        local = [{"id": "a", "title_extracted": "Pasta"}]
        external = [
            {"id": n, "name": "Pasta", "url": f"https://hfresh.info/nl-NL/recipes/pasta-{n}"}
            for n in (1, 2)
        ]
        found = build_crossrefs(local, external)
        self.assertEqual(found["matched"], 0)
        self.assertEqual(found["ambiguous"], 1)

    def test_rejects_wrong_locale_untrusted_urls(self):
        self.assertIsNone(safe_recipe_url("https://hfresh.info.evil.test/nl-NL/recipes/x-1"))
        self.assertIsNone(safe_recipe_url("http://hfresh.info/nl-NL/recipes/x-1"))
        self.assertIsNone(safe_recipe_url("https://hfresh.info/de-DE/recipes/x-1"))
        self.assertIsNone(safe_recipe_url("https://hfresh.info/nl-NL/recipes/x-1?token=secret"))
        self.assertEqual(title_key("Héékfilet à la meunière"), "heekfilet a la meuniere")

    def test_api_limits_searches_and_checks_metadata(self):
        urls = []
        def fake_open(req, timeout):
            urls.append(req.full_url)
            page = len(urls)
            data = {"data": [{"id": page, "name": f"Recipe {page}",
                              "url": f"https://hfresh.info/nl-NL/recipes/recipe-{page}"}],
                    "meta": {"current_page": 1, "last_page": 1}}
            return io.BytesIO(json.dumps(data).encode("utf-8"))
        with patch("hfresh_metadata.urllib.request.urlopen", side_effect=fake_open):
            found = fetch_titles("https://api.hfresh.info/nl-NL/recipes", "test-token", ["Recipe 1", "Recipe 2"], pause_seconds=0)
        self.assertEqual([r["id"] for r in found], [1, 2])
        self.assertIn("perPage=200", urls[0])
        self.assertIn("search=Recipe+2", urls[1])

    def test_api_missing_page_metadata_rejected(self):
        response = io.BytesIO(json.dumps({"data": []}).encode())
        with patch("hfresh_metadata.urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "paginatie"):
                fetch_titles("https://api.hfresh.info/nl-NL/recipes", "token", ["Recipe"], pause_seconds=0)

    def test_rotating_batch_is_bounded_and_resumable(self):
        recipes = [{"id": i, "title_extracted": f"Recept {i}"} for i in range(4)]
        first, cursor = incremental_batch(recipes, {}, 2)
        second, end = incremental_batch(recipes, {"scan_cursor": cursor}, 1)
        self.assertEqual([r["id"] for r in first], [1, 2])
        self.assertEqual([r["id"] for r in second], [3])
        self.assertEqual(end, 0)
        with self.assertRaisesRegex(ValueError, "Batchgrootte"):
            incremental_batch(recipes, {}, 26)

    def test_empty_is_not_verification(self):
        result = build_crossrefs([], [])
        self.assertEqual(result["recipe_links"], {})
        self.assertEqual(result["matched"], 0)


if __name__ == "__main__":
    unittest.main()
