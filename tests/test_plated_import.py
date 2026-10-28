import tempfile
import unittest
from pathlib import Path
from plated_import import canonical_title, extract_ingredient_lines, classify, read_recipes

class PlatedImportTests(unittest.TestCase):
    def test_duplicate_name(self):
        self.assertEqual(canonical_title("dupe_Curry (1).PDF"), canonical_title("Curry.PDF"))
    def test_original_text_block(self):
        text="WHAT WE SEND\n1 yellow onion\n10 ounces salmon\nWHAT YOU'LL NEED\nsalt\n"
        self.assertEqual(extract_ingredient_lines(text), ["1 yellow onion","10 ounces salmon"])
    def test_classification(self):
        self.assertEqual(classify("Ginger Salmon with Rice"), "vis")
        self.assertEqual(classify("Chicken with Spinach"), "kip")
    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_recipes(Path(d)), [])

if __name__=="__main__":
    unittest.main()
