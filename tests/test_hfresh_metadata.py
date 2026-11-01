import io
import json
import unittest
from unittest.mock import patch
from hfresh_metadata import build_crossrefs, fetch_catalog, safe_recipe_url, title_key


class HFreshMetadataTests(unittest.TestCase):
    def test_exact_nl_title_only(self):
        local = [{"id": "hf-7", "title_extracted": "Héékfilet à la meunière"},
                 {"id": "hf-8", "title_extracted": "Andere maaltijd"}]
        external = [{"id": 101, "name": "Heekfilet a la meuniere",
                     "url": "https://hfresh.info/nl-NL/recipes/heekfilet-a-la-meuniere-101",
                     "total_time": 35, "ingredients": [{"name": "Vis"}],
                     "price_eur": 1.00, "quality": "verified"}]
        found = build_crossrefs(local, external)
        self.assertEqual(found["matched"], 1)
        entry = found["recipe_links"]["hf-7"]
        self.assertEqual(entry["total_time"], 35)
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

    def test_api_uses_meta_to_fetch_every_page(self):
        urls = []
        def fake_open(req, timeout):
            urls.append(req.full_url)
            page = len(urls)
            data = {"data": [{"id": page, "name": f"Recipe {page}",
                              "url": f"https://hfresh.info/nl-NL/recipes/recipe-{page}"}],
                    "meta": {"current_page": page, "last_page": 2}}
            return io.BytesIO(json.dumps(data).encode("utf-8"))
        with patch("hfresh_metadata.urllib.request.urlopen", side_effect=fake_open):
            found = fetch_catalog("https://api.hfresh.info/nl-NL/recipes", "test-token", pause_seconds=0)
        self.assertEqual([r["id"] for r in found], [1, 2])
        self.assertIn("perPage=200", urls[0])
        self.assertIn("page=2", urls[1])

    def test_api_missing_page_metadata_rejected(self):
        response = io.BytesIO(json.dumps({"data": []}).encode())
        with patch("hfresh_metadata.urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "paginatie"):
                fetch_catalog("https://api.hfresh.info/nl-NL/recipes", "token")

    def test_empty_is_not_verification(self):
        result = build_crossrefs([], [])
        self.assertEqual(result["recipe_links"], {})
        self.assertEqual(result["matched"], 0)


if __name__ == "__main__":
    unittest.main()
