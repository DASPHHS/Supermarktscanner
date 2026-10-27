from datetime import date
from io import StringIO
import pytest
from scanner import read_offers, calculate_recipe

HEADER = "store,product,price_eur,quantity_g,valid_from,valid_until,source_url\n"
def test_expired_excluded():
    data = HEADER + "AH,broccoli,1.5,500,2025-01-01,2025-01-07,https://example.org\n"
    assert read_offers(StringIO(data), date(2026, 10, 27)) == []

def test_packs_and_missing():
    data = HEADER + "AH,broccoli,1.5,500,2026-10-01,2026-10-31,https://example.org\n"
    offers = read_offers(StringIO(data), date(2026, 10, 27))
    result = calculate_recipe({"name": "Test", "ingredients": {"broccoli": 800, "kipfilet": 600}}, offers, "AH")
    assert result["known_total_eur"] == 3
    assert result["known_per_serving_eur"] == 0.75
    assert result["missing"] == ["kipfilet"]
    assert not result["complete"]

def test_invalid_store():
    with pytest.raises(ValueError):
        read_offers(StringIO(HEADER + "Onbekend,broccoli,1.5,500,2026-10-01,2026-10-31,\n"), date(2026, 10, 27))
