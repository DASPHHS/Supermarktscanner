import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_recipe_library import analyze, ingredient_row


class LibraryAuditTests(unittest.TestCase):
    def test_quantity_field_requires_real_data(self):
        self.assertEqual(ingredient_row({"ingredient": "Broccoli", "quantity_2p_source": "200 g"}), (True, True))
        self.assertEqual(ingredient_row({"ingredient": "Broccoli", "quantity_2p_source": "onbekend"}), (True, False))
        self.assertEqual(ingredient_row({"ingredient": "", "quantity_2p_source": 100}), (False, True))
        self.assertEqual(ingredient_row({"ingredient": "Courgette", "quantity_2p_source": 0}), (True, False))

    def test_all_records_audited_without_confusing_ocr_and_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def put(name, value):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value), encoding="utf-8")
            put("recipes_extracted.json", {"recipes": [
                {"id": "hf-1", "title_extracted": "Kip", "ingredients_2p": [
                    {"ingredient": "Kipfilet", "quantity_2p_source": "2 stuk(s)"}]},
                {"id": "hf-2", "title_extracted": "Bami", "ingredients_2p": [
                    {"ingredient": "Kool", "quantity_2p_source": "onbekend"}]}
            ]})
            put("plated_release_review_queue.json", {"recipes": [
                {"id": "p-1", "source_identity": "p-src", "title_extracted": "Pasta",
                 "ingredients_4p": [{"ingredient": "Pasta", "quantity_4p_source": 400}]}
            ]})
            put("plated_nl_catalog.json", {"recipes": [
                {"source_identity": "p-src", "servings_source": None,
                 "ingredients_nl": [{"name_nl": "Pasta", "quantity_display_nl": "400 g",
                                     "quantity_basis": "source_servings_not_verified"}]}
            ]})
            put("hellofresh/preview_manifest.json", {"recipes": {
                "hf-1": {"front": "x", "original_pdf": "y"}
            }})
            put("hellofresh/plated_preview_manifest.json", {"recipes": {
                "plated-release-p-src": {"front": "x", "original_pdf": "y"}
            }})
            result = analyze(root)
            self.assertEqual(result["summary"]["records_audited"], 3)
            self.assertEqual(result["summary"]["with_original_card"], 2)
            self.assertEqual(result["summary"]["ingredient_rows_inspected"], 3)
            self.assertEqual(result["summary"]["human_source_review_confirmed"], 0)
            self.assertIn("quantities_incomplete", result["records"][1]["issues"])
            self.assertIn("portions_unconfirmed", result["records"][2]["issues"])
            self.assertIn("human_source_review_required", result["records"][0]["issues"])

    def test_verified_flag_requires_all_manual_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            put = lambda path, obj: (root / path).write_text(json.dumps(obj), encoding="utf-8")
            (root / "hellofresh").mkdir()
            put("recipes_extracted.json", {"recipes": [{
                "id": "h", "title_extracted": "A", "quality": "verified",
                "ingredients_verified": True, "quantities_verified": True, "servings_verified": True,
                "ingredients_2p": [{"ingredient": "B", "quantity_2p_source": "100 g"}],
            }]})
            put("plated_release_review_queue.json", {"recipes": []})
            put("plated_nl_catalog.json", {"recipes": []})
            put("hellofresh/preview_manifest.json", {"recipes": {"h": {"front": "a", "original_pdf": "b"}}})
            put("hellofresh/plated_preview_manifest.json", {"recipes": {}})
            result = analyze(root)
            self.assertTrue(result["records"][0]["source_review_confirmed"])
            self.assertEqual(result["summary"]["human_source_review_confirmed"], 1)
            data = json.loads((root / "recipes_extracted.json").read_text())
            data["recipes"][0]["servings_verified"] = False
            put("recipes_extracted.json", data)
            self.assertFalse(analyze(root)["records"][0]["source_review_confirmed"])


if __name__ == "__main__":
    unittest.main()
