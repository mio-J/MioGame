"""Round 3 independent candidate checks. No formal source or prior outputs changed.
Run with Python stdlib. Derived ledger fixes are explicit; no game playtest claims.
"""
import json, math
from pathlib import Path
from normal_clock import normal_spawn_times
ROOT=Path(__file__).resolve().parent
PARAMS={
 'barracks2':[3000,20,0,20,40,0,0,1,4],
 'barracks3':[6000,60,0,30,60,0,0,1,4],
 'shrine2':[4000,0,20,20,40,0,0,1,4],
 'shrine3':[7000,0,40,30,60,0,0,1,4],
 'gun_unlock':[1200,10,0,0,30,0,0,1,0],
 'assassin_unlock':[2000,0,15,0,40,0,0,1,0],
 'alchemy':[5000,0,25,50,30,300,0,1,6],
 'stage_worker':[0,0,0,0,0,0,0,1,0],
}
SELF_TASKS=set(PARAMS)-{'alchemy','stage_worker'}
# A finite, explicit candidate map; not existing generator guarantees.
MINES=[(120,0),(180,0),(350,200),(260,-30),(400,10),(480,-10)]
CAMP_POS=[(350,0),(450,100),(550,0),(450,-100)]
SCENARIO={}

def synthetic_trip(depart=657, positions=CAMP_POS, combat=30, structure=15):
    prev=(0,0); now=depart; rows=[]
    for i,p in enumerate(positions):
        now+=math.ceil(math.dist(prev,p)*1.25/3)+combat+structure
        rows.append({'id':f'C{i+1}','pos':p,'clear_second':now,'crystal':50,
                     'guard_points':6,'camp_xp':30,'guard_seconds':combat,
                     'structure_seconds':structure})
        prev=p
    return rows, now+math.ceil(math.dist(prev,(0,0))*1.25/3)

# Independent in-memory derived engine. Original module is never imported or
# run: its main and output writes are excluded. All substitutions are asserted.
source=(ROOT/'economy_check.py').read_text(encoding='utf-8')
source=source[:source.index('def main():')]
def replace(old,new):
    global source
    assert old in source,old
    source=source.replace(old,new)
replace("actions,camps,soldiers=teaching_plan(route) if route.startswith('S01') else plan(route)",
        "actions,camps,soldiers=candidate_plan(route)")
replace("if kind in UNIT_KINDS:","if kind in SELF_TASKS:\n                buildings[a['id']]={'kind':kind,'pos':a['pos'],'size':spec[8]}\n            elif kind in UNIT_KINDS:")
replace("elif k=='magic3' and ('MAG' not in buildings or t<1740):reason='requires_magic2_or_hero_lv10_assumed_29min'", "elif k=='magic3' and ('MAG' not in buildings or xp_at(t)<1260):reason='requires_actual_xp1260'")
replace("elif k=='magic' and t<660:reason='hero_lv5_assumed_11min'", "elif k=='magic' and xp_at(t)<SCENARIO.get('magic2_xp_gate',360):reason='requires_actual_magic2_xp_gate'")
replace("elif k=='knight' and 'TEC3' not in buildings:reason='requires_tech3'", "elif k=='knight' and 'R1_L3' not in buildings:reason='requires_barracks3'")
replace("elif k=='gun' and 'TEC' not in buildings:reason='requires_tech2'", "elif k=='gun' and 'GUN_UNLOCK' not in buildings:reason='requires_gun_unlock'")
replace("elif k in ('priest','assassin') and 'SHR' not in buildings:reason='requires_shrine'", "elif k in ('priest','assassin') and 'SHR' not in buildings:reason='requires_shrine'\n            elif k=='assassin' and 'ASS_UNLOCK' not in buildings:reason='requires_assassin_unlock'\n            elif k in ('barracks2','gun_unlock') and 'R1' not in buildings:reason='requires_barracks'\n            elif k=='barracks2' and 'TEC' not in buildings:reason='requires_tech2'\n            elif k=='barracks3' and ('R1_L2' not in buildings or 'TEC3' not in buildings):reason='requires_barracks2_and_tech3'\n            elif k=='shrine2' and ('SHR' not in buildings or 'MAG' not in buildings):reason='requires_shrine_and_magic2'\n            elif k=='shrine3' and ('SHR_L2' not in buildings or 'MAG3' not in buildings):reason='requires_shrine2_and_magic3'\n            elif k=='assassin_unlock' and 'SHR' not in buildings:reason='requires_shrine'\n            elif k=='alchemy' and 'MAG' not in buildings:reason='requires_magic2'\n            elif k=='militia_unit' and 'R1' not in buildings:reason='requires_barracks'")
replace("if k in UNIT_KINDS:\n                if pop<=population_units", "if k in UNIT_KINDS or k in SELF_TASKS:\n                if k in UNIT_KINDS and pop<=population_units")
replace("producer='CITY' if k=='worker_unit' else 'SHR' if k in ('priest','assassin') else 'R1'", "producer='CITY' if k=='worker_unit' else 'SHR' if k in ('priest','assassin','shrine2','shrine3','assassin_unlock') else 'R1'")
replace("w=None if k in UNIT_KINDS else min", "w=None if k in UNIT_KINDS or k in SELF_TASKS else min")
replace("else:producer_busy[producer]=finish;population_units+=1", "else:\n                producer_busy[producer]=finish\n                if k in UNIT_KINDS:population_units+=1")
replace("actions.sort(key=lambda a:a['earliest'])", "actions.sort(key=lambda a:a['earliest'])\n        if 'ALCH' in buildings and (t==next((x['second'] for x in rows if x.get('event')=='complete' and x.get('id')=='ALCH'),-1) or t%600==0):\n            buy=min(15, int(gold//800))\n            gold-=buy*800; crystal+=buy;spent['gold']+=buy*800\n            rows.append({'second':t,'event':'alchemy_exchange','crystal_bought':buy,'cost_gold':buy*800})")
# Alchemy completion comes later in the same second. Immediate first quota at
# t+1 is needed; use a per-day marker, avoiding any rebuilding reset.
start=source.index("        if 'ALCH' in buildings and (")
end=source.index("        # B's S02 aggregate",start)
source=source[:start]+"""        if 'ALCH' in buildings and alchemy_day!=t//600:
            buy=min(15, int(gold//800))
            gold-=buy*800;crystal+=buy;spent['gold']+=buy*800
            alchemy_day=t//600
            rows.append({'second':t,'event':'alchemy_exchange','crystal_bought':buy,'cost_gold':buy*800})
"""+source[end:]
replace("levels={1:0}; deliveries=[];", "alchemy_day=-1;levels={1:0}; deliveries=[];")
replace("        # B's S02 aggregate loot expectation", """        for loss in SCENARIO.get('army_losses',[]):
            if math.ceil(loss['second'])!=t:continue
            ids=[i for i,b in buildings.items() if b['kind']=='militia_unit'][:loss['count']]
            for ident in ids:buildings.pop(ident)
            population_units=max(2,population_units-len(ids))
            rows.append({'second':t,'event':'camp_militia_loss','count':len(ids)})
        # B's S02 aggregate loot expectation""")
replace("t in phase_times:","t in phase_times:") # expected loot disabled by caller
replace("'assumed_actual_camp_clear_not_simulated_combat'", "'fixed_route_guard_structure_synthetic_event'")
replace("'final_force_counts':", "'hero_xp_final':xp_at(duration),'xp_events':SCENARIO.get('xp_events',[]),'camp_scenario':SCENARIO.get('camps',[]),'hero_absences':SCENARIO.get('absences',[]),'final_force_counts':")
replace("walk=0 if w is None else math.ceil(math.dist(w['pos'],a['pos'])*1.25/2.5)","walk=walk_seconds(w,a)")
replace("if t%120==0 or t==duration:","if t%120==0 or t==duration or t in (430,940,1460,2025,2600,3185):")
replace("'store_types':sorted(types),'combo_points'", "'force_counts':{k:sum(b['kind']==k for b in buildings.values()) for k in CATALOG if any(b['kind']==k for b in buildings.values())},'hero_xp':xp_at(t),'store_types':sorted(types),'combo_points'")
replace("population_units=max(2,population_units-2);military_upkeep=max(0,military_upkeep-200)","population_units=max(2,population_units-2);military_upkeep=max(0,military_upkeep-200)\n            for dead_id in [i for i,b in buildings.items() if b['kind']=='militia_unit'][:2]:buildings.pop(dead_id)")
replace("|UNIT_KINDS:spent['military_gold']+=c", "|UNIT_KINDS|SELF_TASKS:spent['military_gold']+=c")
env={'__file__':str(ROOT/'round3_economy.py'),'SELF_TASKS':SELF_TASKS,'SCENARIO':SCENARIO}
exec(compile(source,'round3_derived_engine','exec'),env)
env['CATALOG'].update({k:tuple(v) for k,v in PARAMS.items()})
oldplan=env['plan'];oldteaching=env['teaching_plan']

def xp_at(t):
    return sum(e['xp'] for e in SCENARIO.get('xp_events',[]) if e['second']<=t)
env['xp_at']=xp_at
def walk_seconds(worker,action):
    if worker is None:return 0
    paths=SCENARIO.get('resource_paths',{})
    if action['id'] in paths:
        # Derived terrain route via spawn; actor collision/foundation untested.
        from_base=next((v for i,v in paths.items() if SCENARIO.get('resource_positions',{}).get(i)==list(worker['pos'])),math.dist(worker['pos'],(0,0))*1.25)
        return math.ceil((from_base+paths[action['id']])/2.5)
    return math.ceil(math.dist(worker['pos'],action['pos'])*1.25/2.5)
env['walk_seconds']=walk_seconds

def candidate_plan(route):
    acts,_,soldiers=oldteaching(route) if route.startswith('S01') else oldplan(route)
    def add(t,k,i,pos=(0,0)):
        acts.append({'earliest':t,'kind':k,'id':i,'pos':pos,'target':None})
    if route.startswith('S01'):
        # Guaranteed queued orders instead of one-shot militia skips.
        soldiers=[]
        acts=[a for a in acts if a['id'] not in ('replace1','replace2')]
        for a in acts:
            if a['kind']=='barracks':a['earliest']=150
            if a['kind']=='wall':a['earliest']=360 if a['id']=='W1' else 390
        for i in range(4):add(180+i*20,'militia_unit',f'out{i}',(-18,-12))
        add(270,'tower','HOME3',(36,18));add(360,'frost','HOMEF',(-18,18))
        if route=='S01魔法':
            acts=[a for a in acts if a['kind']!='verdict' and a['id']!='teachRing1']
            if not SCENARIO.get('teaching_lv4_exception'):
                add(1290,'stage_worker','STAGE_RING',(-18,12))
            else:
                for a in acts:
                    if a['id'] in ('MAG','teachRing0'):a['earliest']=0
    else:
        # Preserve total base recruitment and maintenance, guarantee queues.
        for when,count in soldiers:
            for i in range(count):add(when,'militia_unit',f'm{when}_{i}',(-18,-12))
        soldiers=[]
        add(900,'gun_unlock','GUN_UNLOCK',(-18,-12))
        if route!='魔法远征':
            add(780,'barracks2','R1_L2',(-18,-12));add(1740,'barracks3','R1_L3',(-18,-12))
            # Prioritize research/army over 80-steel housing when tier3 needed.
            for a in acts:
                if a['kind']=='upgrade' and a['earliest']<1740:a['earliest']+=600
                if a['kind']=='research3':a['earliest']=1500
                if a['id']=='L3':a['earliest']=1740
            if SCENARIO.get('growth_profile')=='industrial':
                for a in acts:
                    if a['kind']=='upgrade':a['earliest']=1320 if a['id']=='U1' else max(2400,a['earliest'])
        else:
            add(1050,'alchemy','ALCH',(6,-56))
            # Zero-loot affordable candidate: no second storm, no furnace;
            # 1st-tier shrine output, no free enhanced priest attributes.
            acts=[a for a in acts if a['kind'] not in ('furnace','verdict','assassin')
                  and a['id'] not in ('storm2','ring1','priest2','priest3')]
            for a in acts:
                if a['id']=='ring0':a['earliest']=2340
            add(1230,'gun','gun6',(-18,-12));add(1260,'gun','gun7',(-18,-12))
            # Combat B's zero-crystal final formation buys physical counters.
            for i in range(3):add(1980+i*90,'cannon',f'MAG_CANNON{i}',(-18+i*6,42))
            for i in range(2):add(2280+i*90,'double',f'MAG_DOUBLE{i}',(36+i*6,42))
            if SCENARIO.get('optimized_magic_policy'):
                acts=[a for a in acts if a['kind']!='alchemy']
                for a in acts:
                    if a['id']=='ring0':a['earliest']=0
                    if a['id']=='SHR':a['earliest']=1560
                    if a['kind']=='priest':a['earliest']=1620
        # Limit unique store requirements; retain prior art/docs untouched.
        acts=[a for a in acts if a['kind'] not in ('inn','electric','department')]
    camps=[(math.ceil(c['clear_second']),c['crystal']) for c in SCENARIO.get('camps',[])]
    for a in acts:
        if a['kind']=='mine' and a['id'].startswith('M'):a['pos']=MINES[int(a['id'][1:])-1]
        if a['id'] in SCENARIO.get('resource_positions',{}):a['pos']=tuple(SCENARIO['resource_positions'][a['id']])
    for rep in SCENARIO.get('replacements',[]):
        for i in range(rep['count']):add(math.ceil(rep['second']),'militia_unit',f"camp_replace{rep['second']}_{i}",(-18,-12))
    return sorted(acts,key=lambda a:a['earliest']),camps,soldiers
env['candidate_plan']=candidate_plan

def run(route,scenario,duration):
    scenario=dict(scenario)
    if 'losses' in scenario:
        scenario['army_losses']=[x for x in scenario['losses'] if x['type']=='militia']
        home=math.ceil(max((pair[1] for pair in scenario.get('absences',[])),default=0))
        scenario['replacements']=[{'second':home,'count':sum(x['count'] for x in scenario['army_losses'])}]
    SCENARIO.clear();SCENARIO.update(scenario)
    spec=list(env['CATALOG']['magic3']);spec[2]=scenario.get('magic3_crystal_cost',300)
    env['CATALOG']['magic3']=tuple(spec)
    r=env['ledger'](route,duration=duration,crystal_drop_mode='zero')
    r['assumptions']=['零随机掉落、无经济卡/税光环；保留原180税、木屋递增300、军事维护及固定损失',
       '固定有限候选矿坐标，均正常付3000金/工人赶路；不是实际生成保底',
       '营地与XP由输入战斗事件派生，路线×1.25不是导航实测；不证明守家胜率',
       '本栋升级/解锁/招募单队列，自研不占工；新兵按实际本栋等级取值']
    r['milestones']={e['id']:e['second'] for e in r['events'] if e['event']=='complete'}
    queues={}
    for e in r['events']:
        if e['event']!='order':continue
        kind=e['kind']
        if kind not in env['UNIT_KINDS'] and kind not in SELF_TASKS:continue
        producer='CITY' if kind=='worker_unit' else 'SHR' if kind in ('priest','assassin','shrine2','shrine3','assassin_unlock') else 'R1'
        assert e['second']>=queues.get(producer,0),(producer,e)
        queues[producer]=e['finish_second']
    for c in scenario.get('camps',[]):assert math.hypot(*c['pos'])>=300
    for i,c in enumerate(scenario.get('camps',[])):
        for d in scenario['camps'][i+1:]:assert math.dist(c['pos'],d['pos'])>=100
    return r

def main():
    provisional,back=synthetic_trip()
    # No invented initial hero levels: provisional nearby XP requires explicit
    # coverage events and is replaced when combat-side event file is available.
    scenario={'camps':provisional,'absences':[[657,back]],
       'xp_events':[{'second':510,'xp':240,'source':'S01 first-stage nearby full coverage candidate'}]+
                   [{'second':c['clear_second'],'xp':30,'source':'camp nearby militia kills'} for c in provisional]}
    external_path=ROOT/'round3_combat_events.json'
    supplied=json.loads(external_path.read_text(encoding='utf-8')) if external_path.exists() else {}
    results={'schema':'round3_candidates_v1','status':'synthetic_not_game_verified',
       'parameters':PARAMS,'finite_map':{'mines':MINES,'camps':CAMP_POS},
       's01':{r:run(r,supplied.get(r,scenario),1535) for r in ['S01科技','S01魔法']}}
    results['s01_lv4_teaching_comparison']=run('S01魔法',dict(supplied.get('S01魔法',scenario),
           magic2_xp_gate=240,teaching_lv4_exception=True),1535)
    results['s01_lv4_teaching_comparison']['experimental_override']={
       'configuration':'S01-L only; not S01/S02 global rule',
       'magic2_xp_gate':240,'default_preserved':360,
       'initial_level_granted':False,'same_camp_events':True,
       'request_lower_bounds_seconds':{'MAG':0,'teachRing0':0}}
    # S02 events intentionally remain empty unless provided by combat author;
    # this counterexample must fail the assumed-lv shortcut, not silently pass.
    empty={'camps':[],'absences':[],'xp_events':[]}
    results['combat_input_present']=bool(supplied)
    config=json.loads((ROOT/'survival_config.json').read_text(encoding='utf-8'))
    sensitivity={}
    for coverage in (.45,.5,.6):
        start=120;events=[]
        for stage,comp in enumerate(config['stages']):
            for j,wave in enumerate(comp):
                points=sum(config['threat_points'][k]*n for k,n in wave.items())
                delay=[110,120,165,175,185,210][stage] if j==3 else 66
                events.append({'second':start+config['s02_clock'][j]+delay,'xp':math.floor(points*coverage)*5,
                               'source':'conditional home nearby kills, no remote camp XP'})
            for local in normal_spawn_times(config['s02_clock']):
                points=min(stage+1,4)
                events.append({'second':start+local+66,'xp':math.floor(points*coverage)*5,
                               'source':'conditional home normal nearby kills'})
            start+=310+[110,120,165,175,185,210][stage]+(90 if stage<5 else 0)
        events.sort(key=lambda e:e['second']);total=0;gates={}
        for e in events:
            total+=e['xp']
            for gate,need in [('Lv5',360),('Lv10',1260)]:
                if total>=need and gate not in gates:gates[gate]=e['second']
        sensitivity[str(coverage)]={'events':events,'first_gate_seconds':gates,'final_xp':total,
                'conditional_only':'home cover allocation and predicted clear delays, not observed battle outcome'}
    results['hero_home_coverage_sensitivity']=sensitivity
    def resource_envelope(count):
        camps=[]
        for i in range(count):
            angle=2*math.pi*i/10
            camps.append({'id':i+1,'pos':(500*math.cos(angle),500*math.sin(angle)),
                          'clear_second':1380 if i<3 else 1800 if i<6 else 2280,
                          'crystal':50,'source':'conditional material arrival envelope, not measured clear route'})
        return dict(empty,camps=camps,xp_events=sensitivity['0.5']['events'])
    results['magic3_material_cost_comparison']={
       'status':'conditional envelope only; nine/ten actual camps and bootstrap unverified',
       'old_300_with_10_camps':run('魔法远征',resource_envelope(10),3395),
       'new_200_same_policy_10_camps':run('魔法远征',dict(resource_envelope(10),magic3_crystal_cost=200),3395),
       'new_200_with_9_camps_no_alchemy':run('魔法远征',dict(resource_envelope(9),magic3_crystal_cost=200,optimized_magic_policy=True),3395)}
    results['s02']={r:run(r,supplied.get(r,empty),3395) for r in ['经济稳守','科技扩矿','魔法远征']}
    results['growth_comparison']={r:run(r,dict(supplied.get(r,empty),growth_profile='industrial'),3395)
                                 for r in ['经济稳守','科技扩矿']}
    mp=ROOT/'round3_map_results.json'
    if mp.exists():
        data=json.loads(mp.read_text(encoding='utf-8'));coords={};paths={}
        for kind,prefix,limit in [(0,'M',6),(1,'C',4),(2,'O',2)]:
            deposits=sorted([x for x in data['resources'] if x['kind']==kind and x.get('grid_access_path_m') is not None],key=lambda x:x['grid_access_path_m'])[:limit]
            for i,d in enumerate(deposits):
                coords[f'{prefix}{i+1}']=d['offset_from_spawn'];paths[f'{prefix}{i+1}']=d['grid_access_path_m']
        results['actual_generator_grid_sensitivity']={'seed':data['seed'],'resource_positions':coords,'resource_paths':paths,
           'actor_navigation_verified':False,'foundation_verified':False,
           'ledgers':{r:run(r,dict(empty,growth_profile='industrial',resource_positions=coords,resource_paths=paths),3395)
                      for r in ['经济稳守','科技扩矿']}}
    (ROOT/'round3_economy_parameters.json').write_text(json.dumps({'catalog':PARAMS,'map':results['finite_map'],
       'queue_rule':'same facility upgrade/unlock/recruit exclusive; upgrade self-research; additive energy',
       'upgrade_prerequisites':{'barracks2':'research2+barracks1','barracks3':'research3+barracks2',
                               'shrine2':'magic2+shrine1','shrine3':'magic3+shrine2'},
       'existing_base_energy':{'barracks':0,'shrine':50},'status':'candidate_not_formal'},ensure_ascii=False,indent=2),encoding='utf-8')
    params_path=ROOT/'round3_economy_parameters.json'
    params=json.loads(params_path.read_text(encoding='utf-8'))
    params['teaching_experiments']={'S01-L_Lv4':{'magic2_xp_gate':240,'camp_crystal_each':65,
             'scope':'independent teaching experiment only','default_magic2_xp_gate_preserved':360,
             'grant_level_or_xp':False,'requests_at_real_preconditions':True}}
    params['magic3_material_experiment']={'old_crystal':300,'candidate_crystal':200,
        'gold_preserved':16000,'incremental_energy_preserved':200,'seconds_preserved':60,
        'hero_xp_gate_preserved':1260,'status':'candidate_only_not_formal'}
    params_path.write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'round3_economy_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    for mode in ['s01','s02']:
        for route,r in results[mode].items():
            print(route,r['milestones'],r['snapshots'][-1],len(r['unfinished_actions']))
if __name__=='__main__':main()
