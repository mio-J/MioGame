"""Exhaust all first-slice town reward choices; no cash fillers or duplicate IDs."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
economic={
    '夜市灯火':{'unlock_town_level':2,'max_rank':1},
    '招兵买马':{'unlock_town_level':2,'max_rank':2},
    '旧房翻新':{'unlock_town_level':2,'max_rank':1},
    '公共建筑扩建':{'unlock_town_level':3,'max_rank':1},
    '集市繁荣':{'unlock_town_level':3,'max_rank':1},
}
records=[]; leaves=[]
def walk(level,owned,history):
    if level==6:
        leaves.append({'history':history,'owned_ranks':owned});return
    eligible=[name for name,rule in economic.items()
              if rule['unlock_town_level']<=level and owned.get(name,0)<rule['max_rank']]
    assert len(eligible)>=2,(level,owned,eligible)
    records.append({'level':level,'owned':owned,'eligible':eligible,'display_count':min(3,len(eligible))})
    for choice in eligible:
        following=dict(owned);following[choice]=following.get(choice,0)+1
        walk(level+1,following,history+[choice])
walk(2,{},[])
synergies=[['穿云箭','跳弹'],['破甲','斩杀线'],['碎冰','凝滞'],
           ['阴阳轮转','瓮中捉鳖'],['代理领主之旗','结阵'],['老兵','归营疗养']]
battle=list(dict.fromkeys(name for pair in synergies for name in pair))+['火力渐强','塔下驻军','不屈']
assert len(battle)==15 and len(set(battle))==15
worst={str(level):min(len(r['eligible']) for r in records if r['level']==level) for level in range(2,6)}
exhausted6=[{'history':leaf['history'],'eligible':[name for name,rule in economic.items()
             if leaf['owned_ranks'].get(name,0)<rule['max_rank']]}
            for leaf in leaves]
result={'status':'slice_levels_2_to_5_choices_valid_not_playtest','economic_cards':economic,
        'dependency_rule':'implemented in slice and unlocked; not-yet-built dependencies shown as pending',
        'minimum_distinct_eligible_by_level':worst,'checked_choice_states':len(records),
        'complete_choice_sequences':len(leaves),'level6_minimum_eligible':min(len(r['eligible']) for r in exhausted6),
        'level6_supported':False,'battle_pool':battle,'synergies':synergies,
        'limitations':['all configured dependencies assumed implemented; real candidate filtering must rerun after scope changes',
                       'six synergy pairs are proposed content, not proven actual implementation or fun',
                       'S02 town level6 not required by first-slice route; if enabled, reward pool must be validated separately']}
(HERE/'round3_card_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('minimum_distinct_eligible_by_level','checked_choice_states',
                                     'complete_choice_sequences','level6_minimum_eligible')},ensure_ascii=False))
