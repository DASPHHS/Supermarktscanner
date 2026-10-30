import json
from datetime import datetime, timezone, timedelta
from verified_rankings import build, verdict, valid_recipe, verified_match, official_url

NOW=datetime(2026,10,30,8,0,tzinfo=timezone.utc)
URL='https://www.ah.nl/producten/product/wi123456/broccoli'

def recipe():
    return dict(id='r1',title_extracted='Broccoli',quality='verified',pricing_eligible=True,
                ingredients_verified=True,quantities_verified=True,servings_verified=True,
                servings=4,ingredients_2p=[dict(ingredient='Broccoli (g)',quantity_2p_source='400')])

def matched():
    return dict(ingredient='Broccoli (g)',product='AH Broccoli',link=URL,package_size='500 gram',
                package_price=1.5,packages=1,cash_cost=1.5,used_cost=1.2,
                status='REGULIERE BRONPRIJS; actie niet bevestigd')

def record():
    return dict(recipe_id='r1',store='AH',complete=True,servings=2,missing=[],
                recipe_review_required=False,ingredient_matches_complete=True,
                matches=[matched()],whole_packages_eur=1.5,used_cost_eur=1.2)

def evidence():
    return [dict(store='AH',product_url=URL,price_eur=1.5,quantity='500 g',
                 checked_by='handmatige controle',checked_at_utc=NOW.isoformat())]

def test_no_approval_without_recipe_validation():
    r=recipe();r['quantities_verified']=False
    assert not valid_recipe(r)
    assert verdict(r,record(),'AH',evidence(),NOW)=='recept_niet_handmatig_gevalideerd'

def test_no_approval_without_current_official_price_evidence():
    assert verdict(recipe(),record(),'AH',[],NOW)=='actuele_officiele_prijsbevestiging_ontbreekt'
    e=evidence();e[0]['checked_at_utc']=(NOW-timedelta(hours=49)).isoformat()
    assert not verified_match(matched(),'AH',e,NOW)
    e=evidence();e[0]['product_url']='https://evil.example/ah/product'
    assert not verified_match(matched(),'AH',e,NOW)
    assert official_url('https://www.ah.nl.evil.example/producten/product/wi123456','AH') is None

def test_verified_cash_total_is_approved_only_with_complete_evidence():
    assert verdict(recipe(),record(),'AH',evidence(),NOW)=='goedgekeurd'
    x=record();x['whole_packages_eur']=1.49
    assert verdict(recipe(),x,'AH',evidence(),NOW)=='prijsberekening_onconsistent'
    x=record();x['matches'][0]['packages']=0
    assert verdict(recipe(),x,'AH',evidence(),NOW)=='actuele_officiele_prijsbevestiging_ontbreekt'

def test_missing_ingredient_or_zero_quantity_is_not_a_price():
    x=record();x['missing']=[dict(ingredient='Olie',reason='geen match')]
    assert verdict(recipe(),x,'AH',evidence(),NOW)=='ingredienten_of_porties_onvolledig'
    x=record();x['matches'][0]['used_cost']=0
    assert verdict(recipe(),x,'AH',evidence(),NOW)=='actuele_officiele_prijsbevestiging_ontbreekt'

def test_build_returns_partial_top10_and_excludes_plated(tmp_path):
    (tmp_path/'recipes_extracted.json').write_text(json.dumps({'recipes':[recipe()]}))
    (tmp_path/'plated_release_review_queue.json').write_text(json.dumps({'recipes':[{'id':'plated-1'}]}))
    (tmp_path/'recipe_prices.json').write_text(json.dumps({'fetched_at_utc':NOW.isoformat(),'results':[record()]}))
    (tmp_path/'price_verifications.json').write_text(json.dumps({'products':evidence()}))
    out=build(tmp_path,NOW)
    assert out['stores']['AH']['verified_count']==1
    assert out['stores']['AH']['top10'][0]['whole_packages_eur']==1.5
    assert out['stores']['AH']['blocked_counts']['plated_nog_niet_prijsgeschikt']==1
    assert out['stores']['Lidl']['verified_count']==0
    old=build(tmp_path,NOW+timedelta(days=3))
    assert old['stores']['AH']['verified_count']==0
    assert not old['price_snapshot_fresh']
