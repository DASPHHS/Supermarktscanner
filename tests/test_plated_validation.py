from fractions import Fraction
import tempfile
from pathlib import Path
import pytest
from plated_validation import parse_amount,scale_amount,normalized_metric,duplicate_groups,check_recipe

@pytest.mark.parametrize("raw,expected",[("½",Fraction(1,2)),("2½",Fraction(5,2)),("1 1/4",Fraction(5,4)),("¾",Fraction(3,4)),("2",Fraction(2,1))])
def test_us_fractions(raw,expected):
    assert parse_amount(raw)==expected

def test_four_portions_are_not_double_scaled():
    assert scale_amount("12",4)== "12"
    assert scale_amount("3/4",2)=="1 1/2"

def test_imprecise_range_rejected():
    with pytest.raises(ValueError):parse_amount("2-3")

def test_oz_to_g():
    assert normalized_metric("12","oz")=={"quantity":"340.19","unit":"g","note":""}

def test_cups_to_volume_not_fake_grams():
    assert normalized_metric("1","cup")["unit"]=="ml"
    assert normalized_metric("1","packet") is None

def test_duplicate_sha256():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)
        (p/"a.pdf").write_bytes(b"%PDF duplicate")
        (p/"b.pdf").write_bytes(b"%PDF duplicate")
        (p/"c.pdf").write_bytes(b"%PDF different")
        dup=duplicate_groups(p)
        assert len(dup)==1 and len(next(iter(dup.values())))==2

def test_no_automatic_price_approval():
    data={"original_servings":4,"servings":4,"ingredients_4p":[{"ingredient":"salmon","quantity_4p_source":"4 stuks"}]}
    assert "Package or piece weight unknown for salmon" in check_recipe(data)
