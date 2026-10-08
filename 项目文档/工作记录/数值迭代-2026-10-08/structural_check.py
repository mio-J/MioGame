"""Compare a proposed economic rule; does not write canonical parameters."""
import json
import math
from pathlib import Path
from economy_check import ledger, tax_income

HERE = Path(__file__).resolve().parent
assert tax_income(50, 'diminishing_candidate') == tax_income(50) == 9000
assert tax_income(100, 'diminishing_candidate') == 15000
assert tax_income(216, 'diminishing_candidate') == 21480
assert all(tax_income(n + 1, 'diminishing_candidate') > tax_income(n, 'diminishing_candidate')
           for n in range(400))

rows = []
for route in ('经济稳守', '科技扩矿', '魔法远征'):
    for policy in ('current', 'diminishing_candidate'):
        run = ledger(route, duration=3400, tax_policy=policy)
        first3 = next((e['second'] for e in run['events']
                       if e['event'] == 'order' and e.get('kind') in ('research3','magic3')), None)
        rows.append({'route':route, 'policy':policy, 'duration_seconds':3400,
                     'final_gold':run['snapshots'][-1]['gold'],
                     'final_net_per_minute':run['snapshots'][-1]['net_per_minute'],
                     'main3_order_second':first3,
                     'town_level_first_seconds':run['town_level_first_seconds'],
                     'unfinished_order_count':len(run['unfinished_actions']) + len(run['pending']),
                     'gold_ever_negative':run['gold_ever_negative']})

camps = [(350,0),(450,100),(550,0),(450,-100)]
assert all(math.hypot(*p) >= 300 for p in camps)
assert all(math.dist(a,b) >= 100 for i,a in enumerate(camps) for b in camps[i+1:])
walk = sum(math.dist(a,b) for a,b in zip([(0,0)]+camps,camps+[(0,0)]))
result = {'status':'unreviewed_counterfactual_not_playtest',
          'limitations':['同一固定采购策略；不是优化后的玩家策略',
                         '商业消费池保持40；无税收增益；未定义候选规则的增益分配，不能写入正文',
                         '沿用原账本输入的英雄等级、清营奖励和未补齐生产前置；不证明可通关'],
          'comparison':rows,
          'legal_camp_coordinate_example':{'positions':camps,'straight_route_m':round(walk,2),
                                           'assumed_path_factor':1.25,
                                           'walk_seconds_at_3mps':round(walk*1.25/3,2),
                                           'combat_lower_bound_seconds':72,
                                           'navigation_verified':False}}
(HERE/'structural_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
