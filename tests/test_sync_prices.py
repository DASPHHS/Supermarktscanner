from sync_prices import amount, ingredient_parts, unit_quantity, products, calculate

def test_amount_units():
 assert amount('500 gram')==(500,'g')
 assert amount('1 kilogram')==(1000,'g')
 assert amount('1 liter')==(1000,'ml')
 assert amount('4 stuks')==(4,'stuk')
 assert amount('onbekend')==(None,None)

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
