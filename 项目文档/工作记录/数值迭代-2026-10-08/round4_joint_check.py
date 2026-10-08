"""Read-only audit of fourth-round economy/combat coupling, never writes models."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent

def main():
    economy=json.loads((HERE/'round4_economy_results.json').read_text(encoding='utf-8'))
    combat=json.loads((HERE/'round4_combat_results.json').read_text(encoding='utf-8'))
    events_sha=hashlib.sha256((HERE/'round4_economy_events.json').read_bytes()).hexdigest()
    same_input=combat.get('economic_input_sha256')==events_sha
    current_events=json.loads((HERE/'round4_economy_events.json').read_text(encoding='utf-8'))
    snapshot_path=HERE/'round4_economy_delay_home_combat_input.json'
    snapshot=json.loads(snapshot_path.read_text(encoding='utf-8')) if snapshot_path.exists() else {}
    snapshot_matches=snapshot_path.exists() and hashlib.sha256(snapshot_path.read_bytes()).hexdigest()==combat.get('economic_input_sha256')
    results={}
    for name,e in economy['scenarios'].items():
        b=combat.get('dynamic_hero_response',{}).get(name)
        if b is None:continue
        verified_events=same_input or (snapshot_matches and name in snapshot and name in current_events and snapshot[name]['events']==current_events[name]['events'])
        expected=[p['big_spawn_sec'] for p in b['phases']]
        planned=e['clock']['big_seconds']
        clock_equal=len(expected)==len(planned) and all(abs(a-z)<=.11 for a,z in zip(expected,planned))
        input_fees=e['combat_feedback'].get('repair_spend_events',[])
        actual_fees=b.get('repair_spend_events',[])
        # Compare every paid second, not merely end balances.
        def fee_map(rows):
            out={}
            for row in rows:out[row['second']]=out.get(row['second'],0)+row['gold']
            return out
        left,right=fee_map(input_fees),fee_map(actual_fees)
        fee_diff=sum(abs(left.get(t,0)-right.get(t,0)) for t in set(left)|set(right))
        uninterrupted=len(b['phases'])==6 and not b['errors']
        results[name]={'same_completion_input':verified_events,'clock_matches_feedback':clock_equal,
            'per_second_repair_fee_difference':round(fee_diff,6),
            'paid_repair_sum':round(sum(left.values()),2),'combat_repair_sum':round(sum(right.values()),2),
            'six_phase_condition_clear':uninterrupted,'stop_second':b['stop_sec'],
            'coupling_fixed_point':verified_events and clock_equal and fee_diff<.01,
            'actual_enemy_losses_reconciled':e.get('actual_enemy_losses_inventory_reconciled',False),
            'map_scope':e['accepted_map_scope']}
    report={'method':'SHA of actual completion events; matching wave clock and every repair payment second',
        'engine_navigation_test':False,'scenarios':results}
    (HERE/'round4_joint_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
