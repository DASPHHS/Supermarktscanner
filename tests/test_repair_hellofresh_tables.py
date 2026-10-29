import pytest
from repair_hellofresh_tables import extract_table

TABLE='''Ingrediënten voor 1 - 6 personen
1p 2p 3p 4p 5p 6p
Zoete aardappel (g)
150 300 450 600 750 900
Gedroogde tijm (zakje(s))
⅓ ⅔ 1 1⅓ 1⅔ 2
Zelf toevoegen
Water (ml)
50 100 150 200 250 300
Peper & zout
naar smaak
* in de koelkast bewaren
Voedingswaarden
'''
def test_keep_all_units_and_direct_source_columns_once():
 rows=extract_table(TABLE+TABLE)
 assert len(rows)==4
 assert rows[0]['quantities_source'][1]=='300'
 assert rows[1]['quantities_source'][3]=='1⅓'
 assert rows[2]['self_add']
 assert rows[3]['quantities_source'][1] is None

def test_incomplete_or_ambiguous_columns_are_rejected():
 with pytest.raises(ValueError):extract_table(TABLE.replace('150 300 450 600 750 900','150 300 450 600 750900'))
 with pytest.raises(ValueError):extract_table(TABLE.replace('naar smaak','niet verwerkt'))

def test_unquantified_pantry_stays_visible_and_unpriced():
 rows=extract_table(TABLE.replace('Peper & zout','[Plantaardige] melk scheutje\nPeper & zout'))
 assert rows[-2]['ingredient']=='[Plantaardige] melk (scheutje)'
 assert rows[-2]['quantities_source']==[None]*6
