"""Enumerate implemented-card masks and every legal town reward history."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
catalog=json.loads((HERE/'round3_card_results.json').read_text(encoding='utf-8'))['economic_cards']
names=list(catalog)

def check(active):
    failures=[];counts={str(x):[] for x in range(2,6)};states=0;leaves=0
    def visit(level,owned,history):
        nonlocal states,leaves
        if level==6:leaves+=1;return
        states+=1
        eligible=[n for n in active if catalog[n]['unlock_town_level']<=level and owned.get(n,0)<catalog[n]['max_rank']]
        counts[str(level)].append(len(eligible))
        if len(eligible)<2:
            failures.append({'town_level':level,'history':history,'eligible':eligible})
        # Continue single-option states only to expose later failures; never claim this is valid UI.
        for choice in eligible:
            nxt=dict(owned);nxt[choice]=nxt.get(choice,0)+1
            visit(level+1,nxt,history+[choice])
    visit(2,{},[])
    return {'implemented_cards':active,'release_pool_valid':not failures,'states':states,'full_histories':leaves,'minimum_distinct_by_level':{k:min(v) if v else None for k,v in counts.items()},'first_failure':failures[0] if failures else None}

def main():
    results=[check([n for i,n in enumerate(names) if mask&(1<<i)]) for mask in range(1<<len(names))]
    valid=[r for r in results if r['release_pool_valid']]
    assert len(valid)==1 and len(valid[0]['implemented_cards'])==5
    missing_market=next(r for r in results if r['implemented_cards']==[n for n in names if n!='集市繁荣'])
    assert missing_market['minimum_distinct_by_level']['5']==1
    result={'actual_game_implementation_mask_verified':False,'checked_masks':len(results),'valid_masks':len(valid),'without_market':missing_market,'results':results,'limitations':'Requires real unlocked dependency objects and implementation flags. All five designed names alone are not release evidence.'}
    (HERE/'round4_pool_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'checked_masks':len(results),'valid_masks':len(valid),'without_market':missing_market['minimum_distinct_by_level']},ensure_ascii=False))

if __name__=='__main__':main()
