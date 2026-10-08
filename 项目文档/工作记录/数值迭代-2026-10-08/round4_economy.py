"""Round 4 real purchase events under combat-driven clock. stdlib only.
Reads round3 source/inputs; never writes earlier models or formal documents.
"""
import importlib.util, json, math, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('round3_readonly',ROOT/'round3_economy.py')
r3=importlib.util.module_from_spec(spec);spec.loader.exec_module(r3)
DEFAULT_BIG=[430,925,1416,1922.1,2426.7,2929.8]
DEFAULT_END=3043.4
KIND={'tower':'arrow','frost':'frost','double':'double','cannon':'cannon',
      'steelrain':'steel','storm':'storm','ring':'ring','corrosion':'corrosion','verdict':'verdict',
      'furnace':'furnace','sentry':'sentry'}
CFG={
 '经济稳守工业':('经济稳守','industrial'),
 '经济稳守住房':('经济稳守','housing'),
 '科技扩矿工业':('科技扩矿','industrial'),
 '科技扩矿住房':('科技扩矿','housing'),
 '经济稳守工业保险':('经济稳守','industrial'),
 '经济稳守工业延住宅保险':('经济稳守','industrial'),
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def round4_plan(route):
    actions,camps,soldiers=r3.candidate_plan(route)
    # Combat-reported actual repair replaces the old fixed600 half-tower case.
    actions=[a for a in actions if a['kind']!='repair']
    if r3.SCENARIO.get('dedicated_repair_crews'):
        for i,t in enumerate((360,375)):
            actions.append({'earliest':t,'kind':'repair_worker','id':f'repair{i+1}',
                            'pos':(0,0),'target':None})
    if r3.SCENARIO.get('opening_insurance'):
        # Pull already-budgeted military forward; no gifted structures or time.
        changed={'W1':90,'W4':120,'H2':240,'H3':360,'A3':240,'A4':300,
                 'Z1':420,'extraFrost0':540,'L1':780,'L2':900,'extraCannon0':1080,
                 'repair2':180,'repair1':210,'extraSteel0':2280}
        positions={'extraFrost0':(-18,18),'extraCannon0':(-18,24),
                   'extraSteel0':(42,48),'extraSteel2':(48,48),'extraSteel4':(54,48)}
        for a in actions:
            if a['id']=='U1' and r3.SCENARIO.get('delay_first_home_upgrade'):a['earliest']=1560
            if a['id'] in changed:a['earliest']=changed[a['id']]
            if a['id'] in positions:a['pos']=positions[a['id']]
    return sorted(actions,key=lambda a:a['earliest']),camps,soldiers

def compile_engine(clock):
    source=r3.source
    old='or t in (430,940,1460,2025,2600,3185):'
    assert old in source
    source=source.replace(old,'or t in SNAPSHOT_TIMES:')
    # Formal adopted boundary: destroyed completed buildings do not refund.
    assert 'refund=.5*(2000+5*house_slope);gold+=refund' in source
    source=source.replace('refund=.5*(2000+5*house_slope);gold+=refund','refund=0;gold+=refund')
    source=source.replace("lost=buildings.pop('A2');gold+=1200","lost=buildings.pop('A2');gold+=0")
    source=source.replace("'loss_tower_and_2_militia','refund':1200","'loss_tower_and_2_militia','refund':0")
    assert "'walk_seconds':walk,'build_seconds':seconds" in source
    source=source.replace("'walk_seconds':walk,'build_seconds':seconds",
        "'worker_id':w['id'] if w else None,'worker_from_pos':list(w['pos']) if w else None,'walk_seconds':walk,'build_seconds':seconds")
    source=source.replace("producer='CITY' if k=='worker_unit'", "producer='CITY' if k in ('worker_unit','repair_worker')")
    assert "        # B's S02 aggregate loot expectation" in source
    source=source.replace("        # B's S02 aggregate loot expectation", """        if t in SCENARIO.get('repair_by_second',{}):
            amount=SCENARIO['repair_by_second'][t]
            if gold+1e-8<amount:
                rows.append({'second':t,'event':'repair_payment_failed','cost_gold':amount,'gold':gold})
            else:
                gold-=amount;spent['gold']+=amount;spent['repair_gold']+=amount
                rows.append({'second':t,'event':'actual_repair_payment','cost_gold':amount,'gold':round(gold,2)})
        # B's S02 aggregate loot expectation""")
    env=dict(r3.env)
    env['SNAPSHOT_TIMES']=set(math.floor(x) for x in clock['big_seconds'])
    exec(compile(source,'round4_clock_engine','exec'),env)
    # exec resets catalog to old engine; restore adopted round3 parameters.
    env['CATALOG'].update({k:tuple(v) for k,v in r3.PARAMS.items()})
    env['CATALOG']['repair_worker']=(1000,0,0,0,15,60,0,1,0)
    env['UNIT_KINDS']=set(env['UNIT_KINDS'])|{'repair_worker'}
    env['candidate_plan']=round4_plan;env['xp_at']=r3.xp_at;env['walk_seconds']=r3.walk_seconds
    return env

def run(name,route,profile,clock,scenario=None):
    scenario=dict(scenario or {},growth_profile=profile,dedicated_repair_crews=True,
                  opening_insurance=name.endswith('保险'),delay_first_home_upgrade='延住宅' in name)
    scenario['repair_by_second']={}
    for fee in scenario.get('repair_spend_events',[]):
        if fee['second']>clock['end_second']:continue
        t=min(math.ceil(fee['second']),math.floor(clock['end_second']))
        scenario['repair_by_second'][t]=scenario['repair_by_second'].get(t,0)+fee['gold']
    r3.SCENARIO.clear();r3.SCENARIO.update(scenario)
    env=compile_engine(clock)
    ledger=env['ledger'](route,duration=math.floor(clock['end_second']),crystal_drop_mode='zero')
    milestones={e['id']:e['second'] for e in ledger['events'] if e['event']=='complete'}
    starts={};complete_at={}
    planned={a['id']:a for a in round4_plan(route)[0]}
    events=[{'second':0,'type':'worker_complete','id':'worker1','kind':'worker','lane':'A','pos':[0,0],'role':'construction_only'},
            {'second':0,'type':'worker_complete','id':'worker2','kind':'worker','lane':'B','pos':[0,0],'role':'construction_only'},
            {'second':0,'type':'hero_present','id':'hero','kind':'hero','lane':'A','pos':[0,0]}]
    for ident,p in planned.items():p['lane']='A' if p['pos'][0]<=6 else 'B'
    for e in ledger['events']:
        if e['event']=='order':
            starts[e['id']]=e
            if e.get('worker_id'):
                p=planned.get(e['id'],{'pos':(36,0),'lane':'B'})
                events.append({'second':e['second'],'type':'worker_task_start','id':e['worker_id'],
                    'target_id':e['id'],'until_second':e['finish_second'],'kind':e['kind'],
                    'from_pos':e['worker_from_pos'],'pos':p['pos'],'lane':p['lane'],
                    'walk_seconds':e['walk_seconds']})
        elif e['event']=='complete':
            complete_at[e['id']]=e['second']
            k=e['kind'];order=starts.get(e['id'],{})
            p=planned.get(e['id'],{'pos':(36,0),'lane':'B'})
            if order.get('worker_id'):
                events.append({'second':e['second'],'type':'worker_task_finish','id':order['worker_id'],
                    'target_id':e['id'],'pos':p['pos'],'lane':p['lane']})
            if k in KIND or k=='wall' or k in env['UNIT_KINDS']:
                # Use actually paid placement, never duplicate a tower per lane.
                pos=p['pos']
                event={'second':e['second'],'id':e['id'],'kind':KIND.get(k,k),
                       'lane':'A' if pos[0]<=6 else 'B','pos':pos,'order_second':order.get('second'),
                       'purchase_gold':order.get('cost_gold'),'purchase_iron':order.get('cost_iron'),
                       'walk_seconds':order.get('walk_seconds'),'build_seconds':order.get('build_seconds')}
                event['type']='tower_complete' if k in KIND else 'wall_complete' if k=='wall' else 'worker_complete' if k in ('worker_unit','repair_worker') else 'unit_complete'
                if k=='worker_unit':event['role']='construction_only'
                if k=='repair_worker':
                    dest=(-18,0) if e['id']=='repair1' else (36,0)
                    travel=math.ceil(math.dist((0,0),dest)*1.25/2.5)
                    event.update(second=e['second']+travel,kind='worker',lane='A' if dest[0]<0 else 'B',
                                 pos=dest,role='repair_only',recruit_complete_second=e['second'],
                                 travel_seconds=travel,excluded_from_construction_pool=True)
                if k=='wall':event.update(hp=2000,armor=15)
                if event['type']=='unit_complete':
                    # Level locked when order begins, not at spawn completion.
                    t_order=order['second'];is_magic=k in ('priest','assassin')
                    l3='SHR_L3' if is_magic else 'R1_L3';l2='SHR_L2' if is_magic else 'R1_L2'
                    level=3 if complete_at.get(l3,float('inf'))<=t_order else 2 if complete_at.get(l2,float('inf'))<=t_order else 1
                    event.update(kind={'militia_unit':'militia','gun':'musket','knight':'knight','priest':'priest','assassin':'assassin'}[k],
                                 facility_level=level,armor=0,equipment=None,
                                 equipment_note='smith at (48,6), barracks(-18,-12): out of15m; no free armor')
                events.append(event)
        elif e['event']=='loss_tower_and_2_militia':
            events.append({'second':e['second'],'type':'tower_destroyed','id':'A2','kind':'arrow','lane':'B'})
            events.append({'second':e['second'],'type':'unit_loss','count':2,'kind':'militia','source':'controlled loss input, combat not predicted'})
    events.sort(key=lambda e:e['second'])
    phases=[]
    for i,big in enumerate(clock['big_seconds']):
        if big>clock['end_second']:continue
        snap=next(s for s in ledger['snapshots'] if s['second']==math.floor(big))
        live={}
        for e in events:
            if e['second']>big:continue
            if e['type']=='tower_complete':live[e['id']]=e
            elif e['type']=='tower_destroyed':live.pop(e['id'],None)
        by_lane={lane:{kind:sum(e['lane']==lane and e['kind']==kind for e in live.values())
                       for kind in sorted(set(KIND.values()))} for lane in ['A','B']}
        phases.append({'stage':i+1,'big_second':big,'balance_time_floor':snap['second'],
                       'balance':snap,'actual_live_towers_by_lane':by_lane,
                       'actual_live_tower_ids':sorted(live)})
    fifth=clock['big_seconds'][4] if len(clock['big_seconds'])>4 else None
    ledger.update(scenario=name,clock=clock,milestones=milestones,phase_ledgers=phases,
                  accepted_map_scope='finite synthetic map only, actor navigation/foundations unverified',
                  limitations=['fixed combat clock is an input pass, not a closed fixed point',
                     'controlled 20min house /26min tower+two troops losses preserved; completed buildings refund0',
                     'old fixed repair600 removed; actual combat repair fees required, missing fees not counted as included',
                     'enemy damage, repaired HP and garrison behavior must be fed back by combat model',
                     'phase balances use floor-second conservative snapshots; completions compare to exact float wave time'],
                  fifth_wave_target={'steel_id':'L3','completion':milestones.get('L3'),
                     'big_second':fifth,
                     'seconds_margin':None if 'L3' not in milestones or fifth is None else round(fifth-milestones['L3'],3)})
    # Upgrade/recruit/unlock share production queue; verify actual order log.
    producer_until={}
    for e in ledger['events']:
        if e['event']!='order':continue
        k=e['kind']
        assert e['energy_used_reserved']<=e['energy_supply'],e
        if k in env['UNIT_KINDS'] or k in r3.SELF_TASKS:
            producer='CITY' if k in ('worker_unit','repair_worker') else 'SHR' if k in ('priest','assassin','shrine2','shrine3','assassin_unlock') else 'R1'
            assert e['second']>=producer_until.get(producer,0),e
            producer_until[producer]=e['finish_second']
    return ledger,{'events':events,'hero_absences':scenario.get('absences',[]),
                   'notes':ledger['limitations'],'initial_workers':2,'initial_towers':0,'initial_walls':0,
                   'repair_policy':'available_workers','repair_targets':'walls_only',
                   'clock_input':clock,'economic_event_source':'actual purchase completion seconds, zero future towers'}

def main():
    feedback_path=ROOT/'round4_combat_feedback.json'
    feedback=json.loads(feedback_path.read_text(encoding='utf-8')) if feedback_path.exists() else {}
    results={'schema':'round4_v1','feedback_loaded':bool(feedback),'status':'feedback purchase pass; require combat replay and compare, never assume fixed point',
             'feedback_source_sha256':sha(feedback_path) if feedback_path.exists() else None,
             'modes':'campaign and survival; S01 internal short check only',
             'input_hashes':{p:sha(ROOT/p) for p in ['round3_economy.py','economy_check.py','survival_config.json']},
             'scenarios':{}}
    exported={}
    for name,(route,profile) in CFG.items():
        entry=feedback.get(name,{})
        clock=dict(entry.get('clock',{'big_seconds':DEFAULT_BIG,'end_second':DEFAULT_END}))
        if entry.get('defeat_second') is not None:clock['end_second']=entry['defeat_second']
        scenario={'repair_spend_events':entry.get('repair_spend_events',[])}
        if '延住宅' in name and not entry:
            scenario['repair_spend_events']=feedback.get('经济稳守工业保险',{}).get('repair_spend_events',[])
        results['scenarios'][name],exported[name]=run(name,route,profile,clock,scenario)
        results['scenarios'][name]['combat_feedback']=entry
        results['scenarios'][name]['actual_enemy_losses_inventory_reconciled']=bool(entry) and '延住宅' in name and not entry.get('actual_losses')
        results['scenarios'][name]['repair_cost_input_present']='repair_spend_events' in entry
    # No unverified camps credited. A magic example cannot buy research or
    # alchemy from a promise of 500 total; bootstrap remains explicit.
    name='魔法未验证营地反例';entry=feedback.get(name,{})
    clock=dict(entry.get('clock',{'big_seconds':DEFAULT_BIG,'end_second':DEFAULT_END}))
    if entry.get('defeat_second') is not None:clock['end_second']=entry['defeat_second']
    results['scenarios'][name],exported[name]=run(name,'魔法远征','housing',clock,{'repair_spend_events':entry.get('repair_spend_events',[])})
    results['scenarios'][name]['combat_feedback']=entry
    results['scenarios'][name]['actual_enemy_losses_inventory_reconciled']=False
    (ROOT/'round4_economy_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'round4_economy_events.json').write_text(json.dumps(exported,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,r in results['scenarios'].items():
        print(name,json.dumps(r['fifth_wave_target'],ensure_ascii=False), 'final_cash',r['snapshots'][-1]['gold'])
if __name__=='__main__':main()
