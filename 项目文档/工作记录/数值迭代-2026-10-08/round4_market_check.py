"""Market-card settlement counterexamples; analytical fixtures, not a game test."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent

def settle(groups, shops, card=False):
    incomes = {s['id']: 0.0 for s in shops}
    total_customers = 0
    caps = 0.0
    for g in groups:
        free = max(0, g['residents'] - g.get('reserved_units', 0))
        total_customers += free
        tax = 180 * max(.7, min(2, 1 + g.get('tax_bonus', 0)))
        cap = min(40, max(0, 360 - tax))
        caps += free * cap
        eligible = {}
        for s in shops:
            # Inputs are measured building-edge distances, not centre distances.
            radius = 20 if card and s['ordinary'] and s['market_edge_m'] <= 12 else (18 if s['ordinary'] and s['market_edge_m'] <= 12 else 15)
            if g['shop_edge_m'][s['id']] <= radius:
                eligible.setdefault(s['kind'], []).append(s)
        weights = {k: max(s['weight'] for s in same) for k, same in eligible.items()}
        scale = min(1, cap / sum(weights.values())) if weights else 0
        for kind, same in eligible.items():
            for s in same:
                incomes[s['id']] += free * weights[kind] * scale / len(same)
    assert sum(incomes.values()) <= caps + 1e-8
    return {'incomes_per_min': incomes, 'total_per_min': sum(incomes.values()), 'actual_free_customers': total_customers, 'pool_ceiling': caps}

def main():
    shops = [dict(id='bread', kind='bread', weight=12, ordinary=True, market_edge_m=5), dict(id='grocery', kind='grocery', weight=12, ordinary=True, market_edge_m=8), dict(id='market', kind='market', weight=12, ordinary=False, market_edge_m=0)]
    group = dict(residents=20, shop_edge_m={'bread':19, 'grocery':25, 'market':21})
    fixtures = {
        'new_unserved_street': ([group], shops),
        'already_served_same_shop': ([dict(residents=20, shop_edge_m={'bread':17,'grocery':25,'market':21})], shops),
        'already_saturated_street': ([dict(residents=20, shop_edge_m={'bread':19,'grocery':10,'market':10,'tavern':10})], shops+[dict(id='tavern',kind='tavern',weight=24,ordinary=True,market_edge_m=13)]),
        'tax_space_exhausted': ([dict(group, tax_bonus=1)], shops),
        'same_kind_duplicate': ([dict(residents=20,shop_edge_m={'bread':19,'bread2':10,'grocery':25,'market':21})], shops+[dict(id='bread2',kind='bread',weight=12,ordinary=True,market_edge_m=13)]),
        'recruit_reservation': ([dict(group,reserved_units=4)], shops),
        'market_own_radius_unchanged': ([dict(residents=20,shop_edge_m={'bread':30,'grocery':30,'market':19})], shops),
    }
    out = {}
    for name, (groups, shop_list) in fixtures.items():
        before, after = settle(groups,shop_list), settle(groups,shop_list,True)
        assert before['actual_free_customers'] == after['actual_free_customers']
        out[name] = {'before':before,'after':after,'city_net_delta_per_min':after['total_per_min']-before['total_per_min']}
    assert out['new_unserved_street']['city_net_delta_per_min']==240
    for name in ['already_served_same_shop','already_saturated_street','tax_space_exhausted','same_kind_duplicate','market_own_radius_unchanged']:
        assert abs(out[name]['city_net_delta_per_min'])<1e-8
    assert out['recruit_reservation']['city_net_delta_per_min']==192
    result={'rule':'Only ordinary shops within12m of market get20m service instead18m; market self remains15m. No virtual customers.','engine_test':False,'fixtures':out}
    (HERE/'round4_market_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['city_net_delta_per_min'] for k,v in out.items()},ensure_ascii=False))

if __name__=='__main__': main()
