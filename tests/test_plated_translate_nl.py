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


def test_focused_ocr_candidates_are_displayed_without_false_four_portion_quantity():
    from plated_translate_nl import enrich
    recipe={"source_identity":"source-empanadas","title_extracted":"Argentine Beef Empanadas (4)",
            "ingredients_4p":[],"servings_original":None}
    rescan={"status":"extracted","method":"pdf_text_layout",
            "quantity_candidates_unverified":[{"name_original":"ground beef","quantity_source":"1 1/2 pounds"},
                                               {"name_original":"garlic","quantity_source":"2 cloves"}]}
    record=enrich(recipe,rescan)
    assert record["rescan_ingredient_candidates"] is True
    assert record["ingredient_ocr_missing"] is False
    assert record["pricing_eligible"] is False
    assert record["ingredients_nl"][0]["name_nl"]=="rundergehakt"
    assert record["ingredients_nl"][0]["quantity_metric"]==680
    assert record["ingredients_nl"][0]["original_quantity_4p"] is None
    assert record["ingredients_nl"][0]["quantity_basis"]=="source_servings_not_verified"

def test_first_pass_quantities_stay_original_when_rescan_exists():
    from plated_translate_nl import enrich
    original={"source_identity":"abc","title_extracted":"Sample",
              "ingredients_4p":[{"ingredient":"ground beef","quantity_4p_source":"24 ounces"}]}
    rescanned={"status":"extracted","quantity_candidates_unverified":[
                {"name_original":"ground beef","quantity_source":"1 pound"}]}
    record=enrich(original,rescanned)
    assert record["ingredients_nl"][0]["quantity_metric"]==680
    assert record["ingredients_nl"][0]["provenance"]=="first_pass_ocr"


def test_frequent_unambiguous_ingredients_have_dutch_names():
    from plated_translate_nl import translated_ingredient
    for english,dutch in (
        ("grape tomatoes","druiftomaten"),
        ("parsley","peterselie"),
        ("granulated sugar","kristalsuiker"),
        ("jasmine rice","jasmijnrijst"),
        ("boneless chicken breasts","kipfilet"),
        ("shredded Monterey Jack","geraspte Monterey Jack"),
    ):
        row=translated_ingredient(english)
        assert row["canonical_nl"]==dutch
        assert row["translation_status"]=="dictionary_exact"
