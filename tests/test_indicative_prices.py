from datetime import date
from copy import deepcopy
import pytest
from indicative_prices import (requirements,product_matches,purchase,estimate_recipe,
                              estimate_with_sensitivity,FAMILIES,prepare_catalog,add_market_products)

TODAY=date(2026,10,29)
def product(name,size=1000,price=2,unit='g',link='https://example.test/product'):
 return dict(name=name,quantity=size,price=price,unit=unit,amount=f'{size} {unit}',link=link)
def recipe(*rows):
 return {'id':'test','quality':'needs_manual_verification','table_repair':{'source_page':2},
         'ingredients_2p':[{'ingredient':n,'quantity_2p_source':q} for n,q in rows]}
def action(**kw):
 x=dict(name='AH Gele uien',quantity='1000 g',price=1,original_price=2,
        valid_from='2026-10-28',valid_until='2026-11-03',promotion_type='one_plus_one',
        multi_buy_quantity=2,multi_buy_price=2,product_url='https://example.test/product')
 x.update(kw);return x

def test_norm_weights_have_disclosed_sources_and_optional_dairy_note():
 x=requirements({'ingredient':'Knoflookteen (stuk(s))','quantity_2p_source':'2'})[0]
 assert x['quantity']==4 and x['norm'] and 'voedingscentrum' in x['source']
 x=requirements({'ingredient':'[Plantaardige] roomboter (el)','quantity_2p_source':'1'})[0]
 assert x['quantity']==15 and x['unit']=='g' and 'plantaardig' in x['note']

def test_missing_ingredient_never_produces_a_total_or_an_eligible_ranking():
 r=recipe(('Ui (stuk(s))','1'),('Onbekende dure saus (bakje(s))','1'))
 x=estimate_recipe(r,{'AH':[product('AH Gele uien')]},'AH',today=TODAY)
 assert not x['eligible'] and x['covered_ingredients']==1 and x['total_ingredients']==2
 assert 'used_total_eur' not in x
 assert x['missing'][0]['ingredient']=='Onbekende dure saus (bakje(s))'

def test_rejected_source_table_cannot_enter_estimated_ranking():
 r=recipe(('Ui (stuk(s))','1'));r.pop('table_repair')
 assert not estimate_recipe(r,{'AH':[product('AH Gele uien')]},'AH',today=TODAY)['eligible']

def test_norm_weight_and_price_changes_recalculate_cost(monkeypatch):
 r=recipe(('Ui (stuk(s))','1'));p=product('AH Gele uien');cat={'AH':[p]}
 assert estimate_recipe(r,cat,'AH',today=TODAY)['used_total_eur']==.2
 aliases,_=FAMILIES['ui'];monkeypatch.setitem(FAMILIES,'ui',(aliases,200))
 assert estimate_recipe(r,cat,'AH',today=TODAY)['used_total_eur']==.4
 p['price']=4
 assert estimate_recipe(r,cat,'AH',today=TODAY)['used_total_eur']==.8

def test_one_plus_one_does_not_halve_cash_and_shows_leftovers():
 x=purchase(100,100,2,action(),TODAY)
 assert x['cash']==2 and x['packages']==2 and x['used']==1 and x['leftover']==100
 x=purchase(150,100,2,action(),TODAY)
 assert x['cash']==2 and x['used']==1.5 and x['leftover']==50
 assert purchase(.1+.2,.3,2)['packages']==1

@pytest.mark.parametrize('change',[{'valid_until':'2026-10-27'}, {'valid_from':'2026-10-30'},
 {'valid_until':''},{'valid_until_estimated':True},{'card_required':True},{'personal_offer':True},
 {'max_per_customer':1},{'multi_buy_quantity':None,'multi_buy_price':None}])
def test_incomplete_expired_future_and_ineligible_promotions_are_not_applied(change):
 x=purchase(100,100,2,action(**change),TODAY)
 assert x['action'] is None and x['cash']==2 and x['packages']==1

def test_card_toggle_changes_action_calculation():
 d=action(card_required=True)
 assert purchase(100,100,2,d,TODAY,False)['used']==2
 assert purchase(100,100,2,d,TODAY,True)['used']==1

def test_same_sku_for_two_source_families_buys_one_package():
 r=recipe(('Olijfolie (el)','1'),('Extra vierge olijfolie (el)','1'))
 x=estimate_recipe(r,{'AH':[product('AH Olijfolie extra vierge',300,3,'ml')]},'AH',today=TODAY)
 assert x['eligible'] and len(x['lines'])==1
 assert x['used_total_eur']==.3 and x['whole_packages_eur']==3
 assert x['lines'][0]['quantity']==30 and x['lines'][0]['packages']==1

def test_norm_scenarios_are_labeled_not_statistical_confidence():
 x=estimate_with_sensitivity(recipe(('Ui (stuk(s))','1')),{'AH':[product('AH Gele uien')]},'AH',[],TODAY)
 assert x['norm_scenario_low_eur']==.15 and x['norm_scenario_high_eur']==.25
 assert 'geen statistisch' in x['scenario_note']

@pytest.mark.parametrize('family,name',[
 ('ui','Jumbo Filet Americain Ui 150 g'),('ui','Jumbo Peen en Ui Hutspot 500 g'),
 ('zoete aardappel','Jumbo Frietjes Zoete Aardappel 400 g'),
 ('kipfilet','AH Gerookte kipfilet'),('kipfilet','Vivera Plantaardige Kipfilet 200 g'),
 ('tomaat','AH Tomaat Soep'),('ei','Kinder Chocolade Surprise Ei'),
 ('rode puntpaprika','Puntpaprika groen 400 g'),('witte kaas','AH Olijven met Witte Kaas'),
 ('witte kaas','Jumbo Witte Kaasblokjes in olie 265 g')])
def test_wrong_food_or_wrong_variant_is_rejected(family,name):
 assert not product_matches(family,product(name))

def test_disclosed_pack_assumption_is_not_a_silent_weight():
 raw=[{'n':'ah','u':'https://ah.test/','d':[{'n':'AH Gele uien','s':'1 kg','p':2,'l':'ui'}]},
      {'n':'jumbo','u':'https://jumbo.test/','d':[{'n':'Jumbo Courgette','s':'','p':.99,'l':'courgette'},
          {'n':'Jumbo Gele uien','s':'1 kg','p':2,'l':'ui'}]}]
 cat=prepare_catalog(raw)
 p=next(p for p in cat['Jumbo'] if p['name']=='Jumbo Courgette')
 assert p['unit']=='stuk' and p['assumed_package_unit']
 x=estimate_recipe(recipe(('Courgette (stuk(s))','1')),cat,'Jumbo',today=TODAY)
 assert x['eligible'] and x['used_total_eur']==.99
 assert 'aangenomen' in x['lines'][0]['package_conversion']

def test_old_secondary_price_is_not_imported():
 cat={'AH':[]};p=dict(name='AH Gele uien',quantity='1000 g',price=2,product_url='https://example.test/ui')
 market={'stores':{'AH':{'products':[{**p,'extracted_at':'2026-10-20'},{**p,'extracted_at':'2026-10-29'}]}}}
 add_market_products(cat,market,TODAY)
 assert len(cat['AH'])==1

def test_known_effective_action_price_is_not_discounted_twice():
 p=product('AH Gele uien',1000,1,link='https://www.ah.nl/producten/product/wi123/ah-uien')
 d=action(product_url=p['link'],quantity='1000 g',original_price=2,card_required=True)
 cat={'AH':[p]};add_market_products(cat,{'stores':{'AH':{'deals':[d]}}},TODAY)
 assert p['price']==2
 r=recipe(('Ui (stuk(s))','1'))
 assert estimate_recipe(r,cat,'AH',[d],TODAY,False)['used_total_eur']==.2
 assert estimate_recipe(r,cat,'AH',[d],TODAY,True)['used_total_eur']==.1

def test_volume_in_product_url_is_not_mistaken_for_a_sku():
 p=product('Jumbo Olijfolie',120,5,'ml',link='https://www.jumbo.com/producten/olijfolie-120ml-123456AB')
 d=action(product_url='https://www.jumbo.com/producten/saus-120ml-987654CD',quantity='120 ml',original_price=2)
 add_market_products({'Jumbo':[p]},{'stores':{'Jumbo':{'deals':[d]}}},TODAY)
 assert p['price']==5

@pytest.mark.parametrize('label,family',[
 ('Rode cherrytomaten (g)','cherrytomaten'),('Mais in blik (g)','mais'),
 ('Geraspte oude Goudse kaas (g)','geraspte oude goudse kaas'),
 ('Zoutarme paddenstoelen- of groentebouillon (ml)','groentebouillon')])
def test_expanded_families_keep_explicit_source_quantities(label,family):
 x=requirements({'ingredient':label,'quantity_2p_source':'100'})[0]
 assert x['family']==family
 assert x['quantity']==(2 if family=='groentebouillon' else 100)

def test_seasoned_meat_proxy_is_visible_and_still_meat():
 r=recipe(('Rundergehakt met Italiaanse kruiden (g)','200'))
 x=estimate_recipe(r,{'AH':[product('AH Rundergehakt',500,5)]},'AH',today=TODAY)
 assert x['eligible'] and not x['vegetarian_ingredients']
 assert x['lines'][0]['price_proxy'] and 'Prijsproxy' in x['assumptions'][0]['note']

def test_shrimp_never_matches_seasoned_or_cocktail_products_or_vega():
 assert not product_matches('garnalen',product('AH Cocktail garnalen'))
 assert not product_matches('garnalen',product('AH Garnalen knoflooksaus'))
 x=estimate_recipe(recipe(('Garnalen (g)','200')),{'AH':[product('AH Garnalen rauw en gepeld')]},'AH',today=TODAY)
 assert x['eligible'] and not x['vegetarian_ingredients']

def test_extra_virgin_oil_to_taste_has_visible_norm():
 x=requirements({'ingredient':'Extra vierge olijfolie (naar smaak)','quantity_2p_source':''})[0]
 assert x['quantity']==15 and x['unit']=='ml' and x['norm']

def test_yoghurt_volume_conversion_does_not_admit_fruit_yoghurt():
 from indicative_prices import product_size
 assert product_size(product('AH Volle yoghurt',1000,1.5,'ml'),'volle yoghurt','g')==(1000,True)
 assert not product_matches('volle yoghurt',product('AH Volle yoghurt aardbei'))

def test_mixed_vegetables_preserve_source_weight_and_disclose_composition():
 rows=requirements({'ingredient':'Rodekool, wittekool en wortel (g)','quantity_2p_source':'150'})
 assert len(rows)==3 and sum(r['quantity'] for r in rows)==150
 assert all(r['proxy'] and r['fixed_quantity'] and r['note'] for r in rows)

def test_source_outage_preserves_existing_market_snapshot(tmp_path,monkeypatch):
 import sync_market_deals as market
 target=tmp_path/'market.json';target.write_text('previous snapshot')
 def fail(term):raise OSError('source unavailable')
 monkeypatch.setattr(market,'query',fail)
 with pytest.raises(RuntimeError,match='bronfouten'):market.main(target)
 assert target.read_text()=='previous snapshot'

def test_rotating_market_queries_are_bounded_and_disclose_partial_coverage():
    from sync_market_deals import select_terms, CORE_TERMS
    from indicative_prices import FAMILIES
    first,total=select_terms(date(2026,10,31),FAMILIES)
    next_day,next_total=select_terms(date(2026,11,1),FAMILIES)
    assert total==next_total and total>len(first)
    assert len(first)<=24 and len(first)==len(set(first))
    assert all(t in first for t in CORE_TERMS)
    assert first!=next_day
    assert len(next_day)<=24


def test_market_source_http_429_is_retried_with_bounded_wait(monkeypatch):
    import io
    import urllib.error
    import sync_market_deals as market
    attempts=[]
    waits=[]
    class Response:
        def __enter__(self): return io.BytesIO(b'{"results":[]}')
        def __exit__(self,*args): return False
    def fake_urlopen(req,timeout):
        attempts.append(1)
        if len(attempts)==1:
            raise urllib.error.HTTPError(req.full_url,429,"rate limited",{"Retry-After":"2"},None)
        return Response()
    monkeypatch.setattr(market.urllib.request,"urlopen",fake_urlopen)
    monkeypatch.setattr(market.time,"sleep",waits.append)
    assert market.query("broccoli")=={"results":[]}
    assert len(attempts)==2
    assert waits==[1.5,2.0]
