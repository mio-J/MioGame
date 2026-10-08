"""Deterministic paper economy checks; no claims of playtest validation.
Run: python economy_check.py. Requires only Python standard library.
"""
import json
import csv
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Round 2 plan ledger. All durations and positions are scenario inputs, not
# measured navigation/collision results or claims of viable battle outcomes.
CATALOG = {
 'house':(2000,0,0,0,20,0,0,1,4),
 'upgrade':(3000,80,0,0,30,0,0,2,4),
 'apartment':(5000,0,0,0,40,0,0,4,4),
 'tower':(2400,0,0,0,20,200,0,1,3),
 'sentry':(1600,0,0,20,15,100,0,1,3),
 'barracks':(3000,0,0,0,30,0,0,1,4),
 'wall':(1000,0,0,0,30,0,0,1,4),
 'mine':(3000,0,0,0,30,100,0,1,6),
 'coal':(3000,0,0,0,30,100,300,1,6),
 'oil':(5000,40,0,0,30,200,400,1,5),
 'bread':(2000,0,0,0,25,0,0,1,3),
 'grocery':(2000,0,0,0,25,0,0,1,3),
 'tavern':(3000,0,0,0,25,0,0,2,3),
 'smith':(3000,20,0,0,30,0,0,2,3),
 'potion':(4000,0,0,0,30,0,0,3,3),
 'market':(5000,0,0,0,30,0,0,3,3),
 'inn':(6000,30,0,0,35,0,0,4,3),
 'electric':(8000,60,0,50,35,0,0,5,3),
 'department':(16000,150,0,100,45,0,0,6,6),
 'cinema':(8000,0,0,100,45,300,0,3,6),
 'mill':(7000,40,0,100,40,200,0,1,6),
 'research':(8000,100,0,200,40,0,0,3,6),
 'research3':(16000,300,0,200,60,0,0,5,6),
 'magic':(8000,0,100,200,40,0,0,1,6),
 'magic3':(16000,0,300,200,60,0,0,1,6),
 'frost':(3600,0,0,0,20,260,0,1,3),
 'double':(4800,40,0,50,30,400,0,1,3),
 'cannon':(5600,60,0,50,35,400,0,1,3),
 'steelrain':(10000,120,0,100,40,650,0,1,3),
 'storm':(9000,0,70,100,40,600,0,1,3),
 'repair':(600,0,0,0,10,0,0,1,3),
 'corrosion':(4200,40,0,50,30,400,0,1,3),
 'ring':(4800,0,30,50,30,400,0,1,3),
 'verdict':(4600,0,30,50,30,400,0,1,3),
 'furnace':(11000,0,100,120,40,700,0,1,3),
 'shrine':(5000,0,40,50,30,0,0,1,4),
 'solar':(10000,0,0,0,35,0,300,1,6),
 'gun':(2200,5,0,0,20,140,0,1,0),
 'knight':(3000,12,0,0,25,160,0,1,0),
 'priest':(2600,0,5,0,20,160,0,1,0),
 'assassin':(3400,0,12,0,20,180,0,1,0),
 'militia_unit':(1200,0,0,0,15,100,0,1,0),
 'worker_unit':(1000,0,0,0,15,60,0,1,0),
}
UNIT_KINDS={'gun','knight','priest','assassin','militia_unit','worker_unit'}
STORES={'bread':12,'grocery':12,'smith':6,'potion':12,'market':12,'electric':20,'department':24}

def plan(route):
    def action(second,kind,ident,x=0,y=0,target=None):
        return {'earliest':second,'kind':kind,'id':ident,'pos':(x,y),'target':target}
    actions=[]
    # Two six-house courtyards and a separate two-house worker quarter.
    positions=[(-12,-12),(-6,-12),(0,-12),(-12,-6),(-6,-6),(0,-6),
               (18,-12),(24,-12),(30,-12),(18,-6),(24,-6),(30,-6),(6,18),(12,18)]
    for i,p in enumerate(positions):
        actions.append(action(i*120,'house',f'H{i+1}',*p))
    actions.append(action(2100,'house','H15',18,18))
    actions.append(action(1320,'repair','fix_A1',-18,0,target='A1'))
    actions += [action(480,'worker_unit','worker3',0,0),action(1080,'worker_unit','worker4',0,0)]
    common=[(55,'tower','A1',-18,0),(150,'tower','A2',36,0),
            (180,'coal','C1',80,0),(240,'bread','B1',-6,-18),
            (300,'barracks','R1',-18,-12),(360,'grocery','G1',0,-18),
            (420,'sentry','Q1',42,0),(480,'tavern','T1',24,-18),
            (540,'wall','W1',-20,6),(570,'wall','W2',-16,6),
            (600,'wall','W3',-12,6),(720,'smith','S1',48,6),
            (960,'potion','P1',12,-18),(1080,'market','K1',6,-18),
            (1140,'cinema','F1',6,-32),(1500,'inn','I1',36,-18),
            (1800,'electric','E1',18,-24),(2220,'department','D1',24,-32),
            (720,'coal','C2',150,0),(1200,'oil','O1',210,20),
            (900,'tower','A3',-24,6),(1200,'tower','A4',42,6),
            (1500,'frost','Z1',42,12),(1680,'wall','W4',36,6)]
    actions += [action(*row) for row in common]
    if route=='经济稳守':
        actions += [action(240,'mine','M1',120,0),action(720,'mine','M2',180,0),
                    action(540,'research','TEC',6,-40),action(1740,'research3','TEC3',6,-40),
                    action(960,'mill','J1',150,18),
                    action(1380,'double','L1',-18,12),action(1620,'cannon','L2',36,12),
                    action(2100,'steelrain','L3',-24,12)]
        up_times=[960,1080,1260,1380,1620,1860,2100,2220]
        camp_times=[(780,35),(1200,35),(1620,40)]
        soldiers=[(480,2),(900,2),(1500,2),(2100,2)]
    elif route=='科技扩矿':
        actions += [action(210,'mine','M1',120,0),action(510,'mine','M2',180,0),
                    action(900,'mine','M3',350,0),action(660,'research','TEC',6,-40),
                    action(900,'mill','J1',240,0),action(1800,'research3','TEC3',6,-40),
                    action(900,'double','L1',-18,12),action(1380,'cannon','L2',36,12),
                    action(1920,'steelrain','L3',-24,12)]
        up_times=[780,1020,1260,1500,1740,1980,2100,2220]
        camp_times=[(900,35),(1440,40)]
        soldiers=[(540,2),(1080,2),(1560,2),(2100,2)]
    else:
        actions += [action(360,'mine','M1',120,0),action(960,'mine','M2',180,0),
                    action(720,'magic','MAG',6,-40),action(1800,'magic3','MAG3',6,-40),
                    action(960,'research','TEC',6,-48),action(1500,'coal','C3',260,0),
                    action(1980,'storm','L3',-24,12)]
        up_times=[780,1020,1260,1500,1740,1980,2100,2220]
        camp_times=[(360,40),(540,40),(690,40),(1020,50),(1260,50),
                    (1500,50),(1620,50),(1740,60),(1860,60),(1980,60)]
        soldiers=[(300,2),(660,2),(1200,2),(1680,2),(2100,2)]
    actions += [action(t,'upgrade',f'U{i+1}',*positions[i],target=f'H{i+1}') for i,t in enumerate(up_times)]
    # B's round-2 cumulative defenses; resource availability determines actual
    # completion. Tower placement remains a force-budget layout, not a tested
    # complete two-front combat formation.
    for i in range(2):actions.append(action(1620,'militia_unit',f'replacement{i}',-18,-12))
    for i in range(8 if route!='魔法远征' else 6):actions.append(action(1080+i*30,'gun',f'gun{i}',-18,-12))
    if route!='魔法远征':
        actions.append(action(1440,'coal','C3',260,20))
        actions.append(action(1380,'coal','C4',210,-80))
        actions.append(action(1800,'oil','O2',320,20))
        for i in range(4):actions.append(action(1920+i*30,'knight',f'knight{i}',-18,-12))
        for i in range(5):actions.append(action((1260+i*120) if i<3 else (2280+(i-3)*90),'double',f'extraDouble{i}',-24+i*6,24))
        for i in range(2):actions.append(action(1440 if i==0 else 2340,'cannon',f'extraCannon{i}',36+i*6,24))
        for i in range(2):actions.append(action(1080+i*180,'tower',f'extraArrow{i}',-18+i*6,30))
        for i in range(3):actions.append(action(1380+i*180,'frost',f'extraFrost{i}',36+i*6,30))
        for i in range(5):actions.append(action(2340+i*90,'steelrain',f'extraSteel{i}',-24+i*6,30))
        for i in range(4):actions.append(action(2280+i*120,'corrosion',f'extraCorrosion{i}',36+i*6,36))
        for i in range(2):actions.append(action(2760+i*90,'cannon',f'lastCannon{i}',36+i*6,42))
        # At least three extra near mines to support the 6 steel-rain cost,
        # rather than assuming 2 mines feed 1500+ iron combat spend instantly.
        actions += [action(1500,'mine','M4',260,-30),action(1860,'mine','M5',400,10),
                    action(2220,'mine','M6',480,-10)]
        for i in range(5):actions.append(action(2040+i*180,'solar',f'V{i}',60+i*8,-30))
    else:
        actions.append(action(2340,'shrine','SHR',-18,-24))
        for i in range(4):actions.append(action(2400+i*30,'priest',f'priest{i}',-18,-24))
        for i in range(2):actions.append(action(2490+i*30,'assassin',f'assassin{i}',-18,-24))
        for i in range(2):actions.append(action(1200 if i==0 else 2340,'ring',f'ring{i}',-18+i*6,24))
        actions.append(action(2400,'verdict','verdict0',42,24))
        for i in range(5):actions.append(action(1200+i*150,'frost',f'extraFrost{i}',30+i*6,30))
        for i in range(6):actions.append(action(1080+i*120,'tower',f'extraArrow{i}',-18+i*6,30))
        actions.append(action(2460,'furnace','furnace0',42,36))
        actions.append(action(2580,'storm','storm2',-18,36))
        actions += [action(1920,'coal','C4',380,20),action(2340,'coal','C5',480,20)]
        # Additional field clear inputs; failures are reported in scenario text.
        camp_times.extend([(2460,60),(2820,60),(3120,60)])
    return sorted(actions,key=lambda a:a['earliest']),camp_times,soldiers

def teaching_plan(route):
    actions=[]
    def put(t,k,i,x=0,y=0):actions.append({'earliest':t,'kind':k,'id':i,'pos':(x,y),'target':None})
    positions=[(-12,-12),(-6,-12),(0,-12),(-12,-6),(-6,-6),(0,-6),(18,-12),(24,-12),(30,-12),(18,-6)]
    for i,p in enumerate(positions):put(i*120,'house',f'H{i+1}',*p)
    for row in [(55,'tower','A1',-18,0),(150,'tower','A2',36,0),(180,'coal','C1',80,0),
                (240,'mine','M1',120,0),(300,'barracks','R1',-18,-12),(360,'grocery','G1',0,-18),
                (480,'bread','B1',-6,-18),(540,'wall','W1',-20,6),(570,'wall','W2',36,6),
                (600,'worker_unit','worker3',0,0),(660,'coal','C2',150,0),(720,'mine','M2',180,0),
                (720,'sentry','Q1',42,0),(1590,'militia_unit','replace1',-18,-12),
                (1590,'militia_unit','replace2',-18,-12)]:put(*row)
    if route=='S01科技':
        put(660,'research','TEC',6,-40)
        for n,t in enumerate([900,1050,1200]):put(t,'double',f'teachDouble{n}',-18+n*6,12)
        for n,t in enumerate([1140,1320]):put(t,'cannon',f'teachCannon{n}',36+n*6,12)
        put(1080,'frost','Z1',42,18)
    else:
        put(720,'magic','MAG',6,-40)
        for n,t in enumerate([900,1050]):put(t,'ring',f'teachRing{n}',-18+n*6,12)
        put(1200,'verdict','teachVerdict',42,12)
        for n,t in enumerate([1080,1260]):put(t,'frost',f'teachFrost{n}',36+n*6,18)
        for n,t in enumerate([900,1140]):put(t,'tower',f'teachArrow{n}',-18+n*6,18)
    return sorted(actions,key=lambda a:a['earliest']),[(480,50),(600,50),(720,50),(840,50)],[(420,2),(540,2)]

def tax_income(free, policy='current'):
    if policy == 'current':
        return free * 180
    if policy == 'diminishing_candidate':
        # Counterfactual only: never exported as the current game parameters.
        return sum(max(0, min(free - start, width)) * rate
                   for start, width, rate in ((0,50,180),(50,50,120),(100,100,60),(200,1000000,30)))
    raise ValueError(policy)

def ledger(route,duration=3400,house_slope=300,crystal_drop_mode='expected',tax_policy='current'):
    actions,camps,soldiers=teaching_plan(route) if route.startswith('S01') else plan(route)
    gold,iron,crystal=3000.,0.,0.
    workers=[{'id':'worker1','pos':(0.,0.),'busy_until':0}, {'id':'worker2','pos':(0.,0.),'busy_until':0}]
    buildings={'CITY':{'kind':'city','pos':(0,0),'size':8,'residents':10}}
    pending=[]; rows=[]; snapshots=[]; population_units=2; military_upkeep=0; recruit_finishes=[]; producer_busy={}
    spent={'gold':0.,'iron':0.,'crystal':0.,'military_gold':0.,'upkeep_gold':0.,'repair_gold':0.}
    levels={1:0}; deliveries=[]; rejections={}; walk_total=0.; dead=False
    thresholds=[0,30,80,150,240,340]; unlocked=1
    def combinations():
        groups=[]; counts={}; slots={}
        def add(name,ids,base):
            if not all(i in buildings for i in ids) or any(slots.get(i,0)>=2 for i in ids):return
            core=buildings[ids[0]]
            radius=20 if any(buildings[i]['kind'] in ('mine','coal') for i in ids) else 10
            for ident in ids[1:]:
                b=buildings[ident]
                # Euclidean distance between edges of axis-aligned footprints.
                dx=max(0,abs(core['pos'][0]-b['pos'][0])-(core['size']+b['size'])/2)
                dy=max(0,abs(core['pos'][1]-b['pos'][1])-(core['size']+b['size'])/2)
                if math.hypot(dx,dy)>radius:return
            repeat=counts.get(name,0)
            if repeat>=5:return
            points=base*(1 if repeat==0 else .5 if repeat==1 else .25)
            counts[name]=repeat+1
            for ident in ids:slots[ident]=slots.get(ident,0)+1
            groups.append({'name':name,'members':ids,'points':points})
        for start in (1,7):
            six=[f'H{i}' for i in range(start,start+6)]
            if all(i in buildings for i in six):add('大杂院',six,10)
            else:
                for first in (start,start+3):add('小村落',[f'H{i}' for i in range(first,first+3)],5)
        add('小村落',['H13','H14','H15'],5)
        add('城下町',['CITY','H1','H2','H4','H5'],10)
        add('军属大院',['R1','H1','H2','H4'],5)
        add('早市',['K1','B1','G1'],10)
        add('不夜城',['F1','T1','I1'],20)
        add('冰品铺',['Z1','B1'],5)
        return groups
    for t in range(duration+1):
        actions.sort(key=lambda a:a['earliest'])
        # B's S02 aggregate loot expectation by phase. This is not a guarantee
        # and the zero-drop counterfactual is run independently below.
        phase_times=(510,1060,1620,2440,3020,3600) if duration>3400 else (510,1060,1620,2200,2780,3360)
        if crystal_drop_mode=='expected' and not route.startswith('S01') and t in phase_times:
            amount=dict(zip(phase_times,(10,20,30,45,60,68)))[t]
            crystal+=amount
            deliveries.append({'second':t,'crystal':amount,'note':'phase_loot_expectation_not_guaranteed'})
        if t in recruit_finishes:military_upkeep+=100*recruit_finishes.count(t)
        for e in list(pending):
            if e['finish']!=t:continue
            pending.remove(e); a=e['action']; kind=a['kind']; spec=CATALOG[kind]
            if kind in UNIT_KINDS:
                buildings[a['id']]={'kind':kind,'pos':a['pos'],'size':0}
                if kind=='worker_unit':workers.append({'id':a['id'],'pos':a['pos'],'busy_until':t})
            elif kind=='repair':
                pass
            elif kind in ('upgrade','apartment'):
                if a['target'] in buildings:
                    buildings[a['target']]['fill_start']=t
                    buildings[a['target']]['fill_end']=t+50
                    buildings[a['target']]['fill_base']=buildings[a['target']]['residents']
            elif kind in ('research3','magic3'):
                buildings[a['id']]={'kind':kind,'pos':a['pos'],'size':spec[8]}
            else:
                buildings[a['id']]={'kind':kind,'pos':a['pos'],'size':spec[8],'residents':0}
                if kind=='house':buildings[a['id']].update(fill_start=t,fill_end=t+50,fill_base=0)
            if e.get('worker'):e['worker']['pos']=a['pos']
            rows.append({'second':t,'event':'complete','id':a['id'],'kind':kind,'gold':round(gold,2),'iron':round(iron,2),'crystal':round(crystal,2)})
        for b in buildings.values():
            if b.get('fill_start') is not None:
                b['residents']=b['fill_base']+min(10,(t-b['fill_start'])//5)
                if t>=b['fill_end']:b.pop('fill_start')
        for when,amount in list(camps):
            if t==when:
                crystal+=amount; deliveries.append({'second':t,'crystal':amount,'note':'assumed_actual_camp_clear_not_simulated_combat'})
        for when,count in soldiers:
            if t==when:
                if gold>=count*1200 and buildings.get('R1'):
                    gold-=count*1200;population_units+=count
                    recruit_finishes.extend(t+15*i for i in range(1,count+1))
                    spent['gold']+=count*1200;spent['military_gold']+=count*1200
                    rows.append({'second':t,'event':'militia_recruit','count':count,'gold':round(gold,2),'iron':round(iron,2),'crystal':round(crystal,2)})
                else:rows.append({'second':t,'event':'militia_skipped_unaffordable','count':count})
        # Controlled loss cases: one house, one tower, two soldiers. Cost/time
        # of rebuild is charged; enemy damage/outcome is an input, not predicted.
        if t==1200 and 'H6' in buildings:
            lost=buildings.pop('H6'); refund=.5*(2000+5*house_slope);gold+=refund
            actions.append({'earliest':t+30,'kind':'house','id':'H6','pos':lost['pos'],'target':None})
            rows.append({'second':t,'event':'loss_house','id':'H6','lost_residents':lost['residents'],'refund':refund})
        if t==1560 and 'A2' in buildings:
            lost=buildings.pop('A2');gold+=1200
            actions.append({'earliest':t+30,'kind':'tower','id':'A2','pos':lost['pos'],'target':None})
            population_units=max(2,population_units-2);military_upkeep=max(0,military_upkeep-200)
            rows.append({'second':t,'event':'loss_tower_and_2_militia','refund':1200})
        combos=combinations()
        pop=sum(b.get('residents',0) for b in buildings.values())
        types={b['kind'] for b in buildings.values() if b['kind'] in set(STORES)|{'tavern','inn'}}
        prosperity=pop+len(types)*8+sum(g['points'] for g in combos)+(10 if 'F1' in buildings else 0)
        while unlocked<6 and prosperity>=thresholds[unlocked]:
            unlocked+=1;levels[unlocked]=t
        supply=sum(CATALOG[b['kind']][6] for b in buildings.values() if b['kind'] in CATALOG)
        used=sum(CATALOG[b['kind']][3] for b in buildings.values() if b['kind'] in CATALOG)
        # Upgrade is incremental 200; old TEC/MAG 200 remains included.
        reserve=sum(CATALOG[e['action']['kind']][3] for e in pending)
        for a in list(actions):
            if t<a['earliest']:continue
            k=a['kind'];c,s,m,e,seconds,maintenance,power,lv,size=CATALOG[k]
            if k=='house':c+=house_slope*sum(b['kind']=='house' for b in buildings.values())+house_slope*sum(p['action']['kind']=='house' for p in pending)
            reason=None
            if unlocked<lv:reason='town_level'
            elif a.get('target') and a['target'] not in buildings:reason='target_absent'
            elif k in ('oil','mill','double','cannon') and 'TEC' not in buildings:reason='requires_tech2'
            elif k in ('research3','steelrain') and 'TEC' not in buildings:reason='requires_tech2'
            elif k=='steelrain' and 'TEC3' not in buildings:reason='requires_tech3'
            elif k=='magic3' and ('MAG' not in buildings or t<1740):reason='requires_magic2_or_hero_lv10_assumed_29min'
            elif k=='magic' and t<660:reason='hero_lv5_assumed_11min'
            elif k=='storm' and 'MAG3' not in buildings:reason='requires_magic3'
            elif k=='furnace' and 'MAG3' not in buildings:reason='requires_magic3'
            elif k in ('ring','verdict','shrine') and 'MAG' not in buildings:reason='requires_magic2'
            elif k=='knight' and 'TEC3' not in buildings:reason='requires_tech3'
            elif k=='gun' and 'TEC' not in buildings:reason='requires_tech2'
            elif k=='solar' and 'TEC3' not in buildings:reason='requires_tech3'
            elif k in ('priest','assassin') and 'SHR' not in buildings:reason='requires_shrine'
            elif gold+1e-8<c:reason='gold'
            elif iron+1e-8<s:reason='iron'
            elif crystal+1e-8<m:reason='crystal'
            elif supply-used-reserve<e:reason='energy'
            idle=[w for w in workers if w['busy_until']<=t]
            producer='CITY' if k=='worker_unit' else 'SHR' if k in ('priest','assassin') else 'R1'
            if k in UNIT_KINDS:
                if pop<=population_units and not reason:reason='population'
                elif producer_busy.get(producer,0)>t and not reason:reason='production_queue'
            elif not idle and not reason:reason='worker'
            if reason:
                rejections.setdefault(a['id'],{}).setdefault(reason,0);rejections[a['id']][reason]+=1
                continue
            w=None if k in UNIT_KINDS else min(idle,key=lambda w:math.dist(w['pos'],a['pos']))
            walk=0 if w is None else math.ceil(math.dist(w['pos'],a['pos'])*1.25/2.5)
            walk_total+=walk
            finish=t+walk+seconds
            if w:w['busy_until']=finish
            else:producer_busy[producer]=finish;population_units+=1
            gold-=c;iron-=s;crystal-=m
            spent['gold']+=c;spent['iron']+=s;spent['crystal']+=m
            if k=='repair':spent['repair_gold']+=c
            if k in set(('tower','sentry','barracks','wall','frost','double','cannon','steelrain','storm','ring','verdict','furnace','corrosion','shrine'))|UNIT_KINDS:spent['military_gold']+=c
            pending.append({'action':a,'finish':finish,'worker':w});actions.remove(a);reserve+=e
            rows.append({'second':t,'event':'order','id':a['id'],'kind':k,'cost_gold':c,'cost_iron':s,'cost_crystal':m,
                         'walk_seconds':walk,'build_seconds':seconds,'finish_second':finish,
                         'gold':round(gold,2),'iron':round(iron,2),'crystal':round(crystal,2),'energy_supply':supply,'energy_used_reserved':used+reserve})
        free=max(0,pop-population_units)
        # Conservative tax: no combination/public bonus included in cash;
        # store cash is actual resident range and consumed once per resident.
        net_tax=tax_income(free,tax_policy);store_cash=0; night=t%600>=360
        homes=[b for b in buildings.values() if b.get('residents',0)]
        remaining_occupied=population_units
        for home in homes:
            occupied_here=min(home['residents'],remaining_occupied);remaining_occupied-=occupied_here
            count=home['residents']-occupied_here
            weights={}
            for b in buildings.values():
                kind=b['kind']
                if kind not in types:continue
                radius=25 if kind=='department' else 15
                if math.dist(home['pos'],b['pos'])>radius:continue
                weights[kind]=24 if kind=='tavern' and night else 6 if kind=='tavern' else 16 if kind=='inn' and night else 8 if kind=='inn' else STORES.get(kind,0)
            store_cash+=count*min(40,sum(weights.values()))
        upkeep=120+military_upkeep+sum(CATALOG[b['kind']][5] for b in buildings.values() if b['kind'] in CATALOG)
        net=net_tax+store_cash-upkeep
        rate=0
        for b in buildings.values():
            if b['kind']!='mine':continue
            distance=math.hypot(*b['pos']);distance_mult=1 if distance<=200 else 1.15 if distance<=500 else 1.3 if distance<=900 else 1.5
            mills=sum(z['kind']=='mill' and math.dist(b['pos'],z['pos'])<=100 for z in buildings.values())
            rate+=20*distance_mult*(1+2*(1-.75**mills))
        if t%120==0 or t==duration:
            snapshots.append({'second':t,'gold':round(gold,2),'iron':round(iron,2),'crystal':round(crystal,2),
                              'population':pop,'occupied':population_units,'town_level':unlocked,'prosperity':prosperity,
                              'store_types':sorted(types),'combo_points':sum(g['points'] for g in combos),
                              'energy_supply':supply,'energy_used':used,'net_per_minute':round(net,2),'iron_per_minute':round(rate,2)})
        if t<duration:
            gold+=net/60;iron+=rate/60;spent['upkeep_gold']+=upkeep/60
            if gold<0:dead=True
    assert all(row.get('gold',0)>=-.01 for row in rows if row['event']=='order')
    return {'route':route,'duration_seconds':duration,'tax_policy':tax_policy,'house_price_slope':house_slope,'crystal_drop_mode':crystal_drop_mode,'assumptions':['无击杀金币；无随机卡经济；无税收加成；无凯旋收益；商业仅基础消费池',
                                       '路径长度输入=直线距离×1.25、工人2.5m/s；包含赶路但不是导航实测',
                                       '组合按矩形边缘距离核对；未运行游戏碰撞/坡地/道路/战斗',
                                       '营地清除时间与晶体为输入；魔法3近营40/4中营50/3远营60为S02固定供给候选，须地图保底与B战斗验算',
                                       '英雄等级11min Lv5/29min Lv10为输入，待B经验验算；其他路线营地无经验门槛收益假设',
                                       '20min损失H6；26min损失箭塔A2和2兵；未预测敌军胜率'],
            'town_level_first_seconds':levels,'total_spent':{k:round(v,2) for k,v in spent.items()},
            'worker_walk_seconds':walk_total,'gold_ever_negative':dead,'final_combinations':combinations(),
            'unfinished_actions':actions,'pending':[{k:v for k,v in p.items() if k!='worker'} for p in pending],
            'wait_reasons_seconds':rejections,'camp_deliveries':deliveries,'snapshots':snapshots,'events':rows,
            'final_force_counts':{k:sum(b['kind']==k for b in buildings.values()) for k in CATALOG if any(b['kind']==k for b in buildings.values())}}

def opening(name, queue, duration=180):
    gold, population, occupied, upkeep = 3000.0, 10, 2, 120
    events, orders, snapshots, index = {}, [], [], 0
    def event(t, kind):
        events.setdefault(t, []).append(kind)
    for second in range(duration + 1):
        for kind in list(events.get(second, [])):
            if kind == 'resident':
                population += 1
            elif kind == 'house':
                for person in range(1, 11):
                    event(second + person * 5, 'resident')
            elif kind == 'tower':
                upkeep += 200
            elif kind == 'militia':
                occupied += 1
                upkeep += 100
        if index < len(queue):
            kind, cost, build_seconds, prerequisite = queue[index]
            if gold + 1e-8 >= cost and second >= prerequisite:
                gold -= cost
                event(second + build_seconds, kind)
                orders.append({'object': kind, 'start_second': second, 'finish_second': second + build_seconds})
                index += 1
        net = (population - occupied) * 180 - upkeep
        if second in (60, 70, 120, 180):
            snapshots.append({'second': second, 'gold': round(gold, 2), 'population': population,
                              'occupied': occupied, 'net_per_minute': net})
        if second < duration:
            gold += net / 60
    return {'name': name, 'orders': orders, 'snapshots': snapshots}

def consumption(customers, prices, cap=40):
    total = sum(prices)
    multiplier = min(1, cap / total) if total else 0
    return {'customers': customers, 'prices': prices, 'cap': cap,
            'store_incomes': [round(customers * p * multiplier, 3) for p in prices],
            'total_income': round(customers * min(total, cap), 3)}

def main():
    scenarios = [
        opening('住宅优先', [('house', 2000, 20, 0), ('tower', 2400, 20, 0)]),
        opening('箭塔优先', [('tower', 2400, 20, 0), ('house', 2000, 20, 0)]),
        opening('兵营优先', [('barracks', 3000, 30, 0), ('militia', 1200, 15, 30), ('house', 2000, 20, 0)]),
    ]
    iron = [{'mines': n, 'rate_per_mine': r, 'mills': m,
             'rate_per_minute': round(n*r*(1+2*(1-.75**m)), 3),
             'seconds_for_80': round(4800/(n*r*(1+2*(1-.75**m))), 2),
             'seconds_for_100': round(6000/(n*r*(1+2*(1-.75**m))), 2),
             'seconds_for_300': round(18000/(n*r*(1+2*(1-.75**m))), 2)}
            for n,r,m in [(1,10,0),(1,20,0),(2,20,0),(2,20,1),(3,20,2)]]
    shops = [consumption(40,[12,12]), consumption(40,[12,12,24]),
             consumption(40,[12,12,24,20]), consumption(40,[24,24,48],80)]
    thresholds = [{'population': p, 'types': t, 'combo_points': c, 'public_points': b,
                   'prosperity': p+8*t+c+b}
                  for p,t,c,b in [(20,1,5,0),(50,4,10,0),(110,6,35,10),(150,8,106,30),(220,10,140,60)]]
    results = {'status':'paper_simulation_not_playtest',
               'assumptions':['1秒离散结算；完工后每5秒入住1人；零赶路时间',
                              '初始3000金币、10人口、2开拓者；人口占用1人；维持费完工后开始',
                              '无击杀、无商店、无邻里/组合加成、无敌人及战损；按固定顺序买一次目标'],
               'openings':scenarios,'iron':iron,'consumption':shops,'prosperity_examples':thresholds,
               'break_even':{'bread_20_residents_minutes':2000/(12*20),
                             'bread_40_residents_minutes':2000/(12*40),
                             'cinema_50_free_residents_net':50*180*.3-300,
                             'cinema_50_free_residents_payback_minutes':8000/(50*180*.3-300),
                             'townhall_100_free_residents_net':100*180*.45-600,
                             'townhall_100_free_residents_payback_minutes':24000/(100*180*.45-600),
                             'iron_smith_40_residents_tax_loss':40*180*.1,
                             'iron_smith_40_residents_store_income':40*6}}
    results['round2_ledgers']=[ledger(r) for r in ('经济稳守','科技扩矿','魔法远征')]
    results['extended_stage_candidate']=[ledger(r,duration=3640) for r in ('经济稳守','科技扩矿','魔法远征')]
    results['S01_purchase_ledgers']=[ledger(r,duration=1800,crystal_drop_mode='zero') for r in ('S01科技','S01魔法')]
    results['house_slope_comparison']=[ledger(r,house_slope=slope) for slope in (900,1200) for r in ('经济稳守','科技扩矿','魔法远征')]
    results['zero_magic_loot_counterfactual']=ledger('魔法远征',crystal_drop_mode='zero')
    assert scenarios[0]['orders'][1]['start_second'] == 52
    assert scenarios[1]['orders'][1]['start_second'] == 72
    assert scenarios[2]['orders'][2]['start_second'] == 166
    assert shops[1]['total_income'] == shops[2]['total_income'] == 1600
    (OUT/'economy_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    with (OUT/'economy_openings.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['scenario','second','gold','population','occupied','net_per_minute'])
        writer.writeheader()
        for s in scenarios:
            for row in s['snapshots']:
                writer.writerow({'scenario':s['name'],**row})
    for result in results['round2_ledgers']:
        keys=sorted({key for row in result['events'] for key in row})
        with (OUT/f"economy_ledger_{result['route']}.csv").open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(result['events'])
    for result in results['extended_stage_candidate']+results['S01_purchase_ledgers']:
        keys=sorted({key for row in result['events'] for key in row})
        suffix='_延长阶段候选' if not result['route'].startswith('S01') else ''
        with (OUT/f"economy_ledger_{result['route']}{suffix}.csv").open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(result['events'])
    print(json.dumps({'status':'checks_passed','outputs':['economy_results.json','economy_openings.csv']},ensure_ascii=False))

if __name__ == '__main__':
    main()
