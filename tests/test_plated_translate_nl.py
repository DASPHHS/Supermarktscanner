from plated_translate_nl import enrich,translated_ingredient,translated_title,quantity_nl

def test_argentine_empanadas():
    title,status=translated_title("Argentine Beef Empanadas (4)")
    assert title=="Argentijnse empanada's met rundvlees"
    assert status=="reviewed_dictionary"

def test_supermarket_alias_with_mass():
    r=enrich({"source_identity":"test","title_extracted":"Beef Chili with Cheddar and Beet Chips",
              "ingredients_4p":[{"ingredient":"ground beef","quantity_4p_source":"24 ounces"}]})
    x=r["ingredients_nl"][0]
    assert x["canonical_nl"]=="rundergehakt"
    assert x["quantity_metric"]==680 and x["unit_metric"]=="g"
    assert x["translation_status"]=="dictionary_exact"
    assert r["pricing_eligible"] is False

def test_cups_do_not_get_fabricated_mass():
    x=quantity_nl("2 cups")
    assert x["quantity_metric"] is None
    assert x["conversion_status"]=="needs_density_or_pack_size"

def test_unknown_ingredient_keeps_original():
    x=translated_ingredient("mystery seasoning blend")
    assert x["name_nl"]=="mystery seasoning blend"
    assert x["canonical_nl"] is None

def test_empty_ocr_flag():
    r=enrich({"id":"a","title_extracted":"Argentine Beef Empanadas","ingredients_4p":[]})
    assert r["ingredient_ocr_missing"] is True
    assert r["pricing_eligible"] is False
