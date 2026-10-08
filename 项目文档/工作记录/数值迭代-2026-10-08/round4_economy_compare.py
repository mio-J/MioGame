"""Compare last authorized candidate purchase events after full repair debit."""
import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAME='经济稳守工业延住宅保险'
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
old_path=ROOT/'round4_economy_delay_home_combat_input.json'
before=read(old_path.name)[NAME]['events']
after=read('round4_economy_events.json')[NAME]['events']
feedback=read('round4_combat_feedback.json')[NAME]
result=read('round4_economy_results.json')['scenarios'][NAME]
def completions(events):
    counts={};out={}
    for e in events:
        if not e['type'].endswith('_complete'):continue
        key=(e['type'],e['id']);counts[key]=counts.get(key,0)+1
        out[(*key,counts[key])]=e['second']
    return out
bc,ac=completions(before),completions(after)
differences=[{'type':key[0],'id':key[1],'occurrence':key[2],
              'before_second':bc.get(key),'after_second':ac.get(key)}
             for key in sorted(set(bc)|set(ac)) if bc.get(key)!=ac.get(key)]
checks={
 'scenario':NAME,'before_event_count':len(before),'after_event_count':len(after),
 'all_asset_and_worker_events_identical':before==after,
 'completion_time_differences':differences,
 'before_events_sha256':digest(before),'after_events_sha256':digest(after),
 'combat_input_snapshot_sha_matches':hashlib.sha256(old_path.read_bytes()).hexdigest()==feedback['economic_input_sha256'],
 'repair_feedback_total':round(sum(x['gold'] for x in feedback['repair_spend_events']),2),
 'repair_debit_total':result['total_spent']['repair_gold'],
 'repair_failed_events':sum(e['event']=='repair_payment_failed' for e in result['events']),
 'cash_ever_negative':result['gold_ever_negative'],
 'scope':'conditional synthetic event/repair fixed point only; not random map, engine navigation or player validation',
 'actual_enemy_losses':feedback.get('actual_losses',[]),
 'external_shocks':'1200 house10 residents;1560 A2+2militia handled, completed refund0',
}
checks['conditional_purchase_repair_converged']=checks['all_asset_and_worker_events_identical'] and checks['combat_input_snapshot_sha_matches'] and checks['repair_feedback_total']==checks['repair_debit_total'] and checks['repair_failed_events']==0 and not checks['cash_ever_negative']
(ROOT/'round4_economy_convergence.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
