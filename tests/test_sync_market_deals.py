from sync_market_deals import is_relevant_food


def test_unrelated_nonfood_hits_are_rejected():
    assert not is_relevant_food("Robijn Color kokos wasmiddel", "kokosmelk")
    assert not is_relevant_food("Kokos Shampoo", "kokosmelk")
    assert not is_relevant_food("Knorr Cup-a-soup Franse ui", "ui")
    assert not is_relevant_food("Honig Bakplaat Mix Aardappel & Broccoli", "broccoli")


def test_relevant_food_matches_are_retained():
    assert is_relevant_food("AH Kokosmelk 400 ml", "kokosmelk")
    assert is_relevant_food("Jumbo Kruimige Aardappelen 600 g", "aardappelen")
    assert is_relevant_food("Bonduelle Kikkererwten 380 g", "kikkererwten")
    assert is_relevant_food("Gele ui 1 kg", "ui")
    assert not is_relevant_food("Fruitmix 1 kg", "ui")
