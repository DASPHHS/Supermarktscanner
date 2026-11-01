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


def test_rotating_search_keeps_recent_prices_without_renewing_old_actions():
    from sync_market_deals import merge_recent_history
    result={'updated_at_utc':'2026-11-01T12:00:00+00:00','search_coverage':{},'stores':{'AH':{'products':[{'product_id':'same','price':2,'extracted_at':'2026-11-01'}],'deals':[]}}}
    previous={'updated_at_utc':'2026-10-31T12:00:00+00:00','stores':{'AH':{'products':[
        {'product_id':'same','price':1,'extracted_at':'2026-10-31'},
        {'product_id':'keep','price':3,'extracted_at':'2026-10-30'},
        {'product_id':'old','price':3,'extracted_at':'2026-10-27'},
        {'product_id':'future','price':3,'extracted_at':'2026-11-02'}],
        'deals':[{'product_id':id,'source_term':term,'valid_from':'2026-10-28','valid_until':end,**extra} for id,term,end,extra in [
            ('keep','pasta','2026-11-03',{}),('rechecked','rijst','2026-11-03',{}),
            ('expired','soep','2026-10-31',{}),('stale','bonen','2026-11-03',{'observed_at_utc':'2026-10-29T12:00:00+00:00'})]]}}}
    merge_recent_history(result,previous,{'rijst'})
    group=result['stores']['AH']
    assert {p['product_id']:p['price'] for p in group['products']}=={'same':2,'keep':3}
    assert [d['product_id'] for d in group['deals']]==['keep']
    assert group['deals'][0]['observed_at_utc']==previous['updated_at_utc']
    # Repeated refresh cannot reset the observation clock.
    later={'updated_at_utc':'2026-11-02T13:00:00+00:00','search_coverage':{},'stores':{'AH':{'products':[],'deals':[]}}}
    merge_recent_history(later,result,set())
    assert later['stores']['AH']['deals']==[]
