from sync_prices import amount, ingredient_parts, unit_quantity, products, calculate, number, matches

def test_amount_units():
 assert amount('500 gram')==(500,'g')
 assert amount('1 kilogram')==(1000,'g')
 assert amount('1 liter')==(1000,'ml')
 assert amount('4 stuks')==(4,'stuk')
 assert amount('onbekend')==(None,None)
 assert amount('1,5 liter')==(1500,'ml')
 assert amount('1.5 kg')==(1500,'g')
 assert amount('2 x 200 gram')==(None,None)
 assert amount('100 g / 200 ml')==(None,None)
 assert amount('500 gram uitlekgewicht 300 gram')==(None,None)

def test_fractions_and_invalid_quantities():
 assert number('1⅓')==1+1/3
 assert number('1 1/2')==1.5
 assert number('½')==.5
 for bad in ('-2','NaN','inf','1-2','unknown','1/0',''):assert number(bad) is None

def test_no_free_seasoning_or_dry_spoon_conversions():
 cat={'AH':[{'name':'Peper zout','n':'peper zout','unit':'ml','quantity':100,'price':1,'amount':'100 ml','link':None}]}
 for label in ('Peper & zout','Roomboter (el)','Kerriepoeder (tl)'):
  r={'id':'x','ingredients_4p':[{'ingredient':label,'quantity_4p_source':'1'}]}
  x=calculate(r,cat,'AH')
  assert x['missing'] and not x['matches']

def test_two_people_use_actual_source_column_and_recalculate_packages():
 cat={'AH':[{'name':'Broccoli','n':'broccoli','unit':'g','quantity':500,'price':1.5,'amount':'500 g','link':None}]}
 r={'id':'x','quality':'verified','pricing_eligible':True,'ingredients_verified':True,'quantities_verified':True,'servings_verified':True,'servings':4,
    'ingredients_4p':[{'ingredient':'Broccoli (g)','quantity_4p_source':'800'}],
    'ingredients_2p':[{'ingredient':'Broccoli (g)','quantity_2p_source':'375'}]}
 x=calculate(r,cat,'AH',servings=2)
 assert x['complete'] and x['whole_packages_eur']==1.5
 assert x['matches'][0]['quantity']==375 and x['used_cost_4p_eur'] is None
 del r['ingredients_2p']
 assert not calculate(r,cat,'AH',servings=2)['complete']

def test_duplicate_ingredients_are_not_silently_dropped():
 r={'id':'x','ingredients_4p':[{'ingredient':'Broccoli (g)','quantity_4p_source':'400'}]*2}
 x=calculate(r,{},'AH')
 assert any('dubbele' in m['reason'] for m in x['missing'])

def test_no_raw_meat_match_to_vegan_product():
 assert not matches('kipfilet','vivera plantaardige kipfilet')
 assert not matches('ei','kinder chocolade surprise ei')
 assert not matches('tomaat','zongedroogde tomaat')
 assert not matches('ui','jumbo filet americain ui 150 g')
 assert not matches('ui','jumbo gesneden peen en ui hutspot 500 g')
 assert matches('champignons','jumbo biologische champignons 250 g')
 assert unit_quantity(4,'plakje(s)')==(None,None)

def test_4_portions_and_pack_cost():
 data=[{'n':'jumbo','c':'Jumbo','d':[{'n':'Jumbo broccoli','p':1.2,'s':'500 gram'}]}, {'n':'ah','c':'AH','d':[{'n':'Broccoli','p':1.5,'s':'500 gram'}]}]
 cat=products(data)
 r={'id':'x','quality':'verified','pricing_eligible':True,
    'ingredients_verified':True,'quantities_verified':True,'servings_verified':True,
    'servings':4,'ingredients_4p':[{'ingredient':'Broccoli (g)','quantity_4p_source':'800'}]}
 x=calculate(r,cat,'Jumbo')
 assert x['complete'] and x['price_per_portion_eur']==0.48 and x['whole_packages_eur']==2.4

def test_fail_closed_for_missing_unit():
 data=[{'n':'jumbo','d':[{'n':'Courgette','p':0.79,'s':'400 gram'}]}, {'n':'ah','d':[{'n':'Courgette','p':0.95,'s':'400 gram'}]}]
 r={'id':'x','ingredients_4p':[{'ingredient':'Courgette (stuk(s))','quantity_4p_source':'4'}]}
 assert not calculate(r,products(data),'Jumbo')['complete']

def test_matched_but_unverified_recipe_has_no_approved_price():
 data=[{'n':'jumbo','d':[{'n':'Broccoli','p':1.2,'s':'500 gram'}]},
       {'n':'ah','d':[{'n':'Broccoli','p':1.5,'s':'500 gram'}]}]
 base={'id':'x','ingredients_4p':[{'ingredient':'Broccoli (g)','quantity_4p_source':'800'}]}
 for changes in ({}, {'quality':'verified'},
                 {'quality':'verified','pricing_eligible':True},
                 {'quality':'verified','pricing_eligible':True,'ingredients_verified':True,
                  'quantities_verified':True,'servings_verified':True,'servings':2}):
  result=calculate({**base,**changes},products(data),'Jumbo')
  assert result['ingredient_matches_complete']
  assert not result['complete']
  assert result['price_per_portion_eur'] is None
  assert result['whole_packages_eur'] is None
  assert result['recipe_review_required']
  assert result['validation_missing']


def test_empty_ingredients_never_count_as_complete():
 data=[{'n':'jumbo','d':[{'n':'Broccoli','p':1.2,'s':'500 gram'}]},
       {'n':'ah','d':[{'n':'Broccoli','p':1.5,'s':'500 gram'}]}]
 verified={'id':'x','quality':'verified','pricing_eligible':True,
           'ingredients_verified':True,'quantities_verified':True,
           'servings_verified':True,'servings':4,'ingredients_4p':[]}
 assert not calculate(verified,products(data),'Jumbo')['complete']
