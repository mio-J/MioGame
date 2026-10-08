"""Round 3 independent, deterministic prototype. NOT an engine/playtest result.
Run with bundled Python. Only writes round3_combat_results.json.
"""
import json, math, ast
from pathlib import Path
ROOT=Path(__file__).parent
cfg=json.loads((ROOT/'survival_config.json').read_text(encoding='utf-8'))
POINTS=cfg['threat_points']; STAGES=cfg['stages']
HP={'green':200,'archer':100,'spore':240,'climber':120,'javelin':150,'immune':300,'iron':300,'boar':500,'mother':360,'giant':2000,'bud':150,'child':80,'tiny':60}
ARM={'immune':10,'iron':30,'boar':5,'giant':5}
def level(xp):
    n=1
    while xp>=40+20*n: xp-=40+20*n;n+=1
    return n
def dist(a,b):return math.hypot(a['x']-b['x'],a['y']-b['y'])
def move(a,b,speed,stop,dt):
    d=dist(a,b)
    if d>stop:
        m=min(speed*dt,d-stop);a['x']+=(b['x']-a['x'])*m/d;a['y']+=(b['y']-a['y'])*m/d
def camp(party,xp,chainphase=0,fronttank=False,greens=4):
    # Coordinates local metres. Hero approaches at range8, troops at1.
    for i,a in enumerate(party):a.update(x=(0 if a['hero'] else -3) if fronttank else (-6 if a['hero'] else -1),y=0 if a['hero'] else (i-2)*1.2,next=0)
    enemies=[dict(kind='green',hp=200,x=2,y=y,next=0) for y in [-3,-1,1,3][:greens]]+[dict(kind='archer',hp=100,x=7,y=0,next=0)]
    kills=[];shots=chainphase
    def hit(e,damage,a,t):
        nonlocal xp
        if e['hp']<=0:return
        e['hp']-=damage
        if e['hp']<=0:
            h=next(z for z in party if z['hero']);gain=POINTS[e['kind']]*(10 if a['hero'] else (5 if h['hp']>0 and dist(h,e)<=15 else 0))
            old=level(xp);xp+=gain
            if level(xp)>old:h['hp']=600+40*(level(xp)-1)
            kills.append(dict(time=round(t,2),kind=e['kind'],owner='hero' if a['hero'] else 'militia',xp=gain,hero_level=level(xp)))
    for tick in range(6001):
        t=tick*.05
        living=[e for e in enemies if e['hp']>0]; allies=[a for a in party if a['hp']>0]
        if not living:break
        if not allies:return dict(failed=True,seconds=t,kills=kills,xp=xp)
        for a in allies:
            choices=[e for e in enemies if e['hp']>0]
            if not choices:break
            target=min(choices,key=lambda e:dist(a,e));reach=8 if a['hero'] else 1
            move(a,target,3,reach,.05)
            if dist(a,target)<=reach+1e-6 and t>=a['next']:
                a['next']=t+1.5;hit(target,30+3*(level(xp)-1) if a['hero'] else 15,a,t)
                if a['hero']:
                    shots+=1
                    if shots%4==0:
                        prev=target;seen=[]
                        for _ in range(4):
                            choices=[e for e in enemies if e['hp']>0 and e not in seen and dist(prev,e)<=5]
                            if not choices:break
                            e=min(choices,key=lambda e:dist(prev,e));seen.append(e);hit(e,40,a,t);prev=e
        for e in living:
            if e['hp']<=0:continue
            allies=[a for a in party if a['hp']>0]
            if not allies:continue
            a=min(allies,key=lambda a:dist(e,a));r=9 if e['kind']=='archer' else 1
            move(e,a,3,r,.05)
            if dist(e,a)<=r+1e-6 and t>=e['next']:
                a['hp']-=(15 if e['kind']=='archer' else 20)*30/(35 if a['hero'] else 30+a.get('armor',0))
                e['next']=t+(2 if e['kind']=='archer' else 1.5)
    else:return dict(failed=True,seconds=300,kills=kills,xp=xp)
    # Building300HP/0armour, cannot attack/awardXP. Continuous DPS time
    # instead of extending troop movement simulation: separate lower bound.
    damage=sum((30+3*(level(xp)-1) if a['hero'] else 15) for a in party if a['hp']>0)
    demolition=math.ceil(300/damage)*1.5
    return dict(failed=False,guard_seconds=round(t,2),demolition_seconds=demolition,seconds=round(t+demolition,2),kills=kills,xp=xp,hero_level=level(xp),survivors=[dict(hero=a['hero'],hp=round(max(0,a['hp']),1)) for a in party])
COORDS=[(350,0),(450,100),(550,0),(450,-100)]
def route(indices,depart=657,xp=240,crystal=50,fronttank=False,greens=4,militia_count=4,militia_armor=0):
    party=[dict(hero=True,hp=600+40*(level(xp)-1))]+[dict(hero=False,hp=150,armor=militia_armor) for _ in range(militia_count)]
    now=depart;last=(0,0);events=[];dead=0
    for i in indices:
        xy=COORDS[i];leg=math.dist(last,xy)*1.25;now+=leg/3
        c=camp(party,xp,fronttank=fronttank,greens=greens);xp=c['xp'];now+=c['seconds'];events.append(dict(camp=i+1,coordinate=xy,path_candidate_m=round(leg,2),arrive_sec=round(now-c['seconds'],2),reward_sec=None if c['failed'] else round(now,2),crystal=0 if c['failed'] else crystal,combat=c))
        if c['failed']:break
        dead=sum(a['hp']<=0 for a in party);last=xy
    now+=math.dist(last,(0,0))*1.25/3
    return dict(depart_sec=depart,return_sec=None if events[-1]['combat']['failed'] else round(now,2),events=events,final_xp=xp,level=level(xp),dead_militia=dead,source='path multiplier1.25 geometric candidate, not navmesh; sequential HP; phase0 chains',fronttank=fronttank)

def lane(composition,towers,hero=False,repair=True,scheduled=None):
    enemies=[];pending=[];n=0;wall=2000.;lost=0.;hero_shots=0;min_wall=2000.;climber_unresolved=0
    if scheduled is None:scheduled=[(0,composition,4)]
    big_start=min((z[0] for z in scheduled if z[2]==4),default=None);big_clear=None
    for time,cohort,batches in scheduled:
        n=0
        for kind,count in cohort.items():
            for _ in range(count):pending.append((time+n%batches*(8 if batches==4 else 4),kind,'big' if batches==4 else 'other'));n+=1
    ts=[dict(kind=k,next=0) for k in towers]+([dict(kind='hero',next=0)] if hero else [])
    def add(k,x,lineage):enemies.append(dict(kind=k,hp=HP[k],x=x,next=0,slow=0,lineage=lineage))
    def hit(e,d,magic=False):
        if magic and e['kind']=='immune':return
        e['hp']-=d if magic else d*30/(30+ARM.get(e['kind'],0))
    for tick in range(9001):
        t=tick/10
        for p in pending[:]:
            if p[0]<=t:add(p[1],150,p[2]);pending.remove(p)
        for e in enemies:
            k=e['kind'];stop={'archer':9,'javelin':8}.get(k,1);speed={'giant':1.6,'iron':2.4,'immune':2.8,'boar':5.5,'climber':5,'child':3.4,'tiny':3.6}.get(k,3)
            e['x']=max(stop,e['x']-speed*(.6 if e['slow']>t else 1)*.1)
            if k=='climber' and e['x']<=1 and not e.get('wall_flag'):
                e['wall_flag']=True;climber_unresolved+=1
            if e['x']<=stop and t>=e['next']:
                d={'giant':80,'iron':25,'boar':25,'archer':15,'javelin':40,'climber':15,'spore':15,'mother':18,'child':10,'bud':12,'tiny':8}.get(k,20)*30/45
                wall-=d;lost+=d;e['next']=t+{'giant':2.5,'archer':2,'child':1.2,'bud':1.2,'tiny':1.2}.get(k,1.5)
        min_wall=min(min_wall,wall)
        if repair and wall>0:wall=min(2000,wall+2000/60*.1)
        for tower in ts:
            k=tower['kind'];r={'ring':6,'cannon':12,'storm':11,'furnace':10,'hero':8,'steel':12,'verdict':12}.get(k,10)
            targets=sorted([e for e in enemies if e['hp']>0 and e['x']+1<=r],key=lambda e:e['x'])
            if k=='cannon':targets=[e for e in targets if e['x']+1>=4]
            if k=='storm':targets=[e for e in targets if e['kind']!='immune']
            if not targets or t<tower['next']:continue
            first=targets[0];tower['next']=t+{'ring':.5,'storm':2.5,'steel':.25,'cannon':3,'verdict':30}.get(k,1.5)
            if k in ['ring','furnace','cannon']:
                for e in targets:
                    if k=='ring' or abs(e['x']-first['x'])<= (4 if k=='furnace' else 3):hit(e,{'ring':3,'furnace':80,'cannon':40}[k],k!='cannon')
            elif k=='storm':
                prev=first;seen=[]
                for i in range(5):
                    options=[e for e in targets if e not in seen and (i==0 or abs(e['x']-prev['x'])<=5)]
                    if not options:break
                    e=options[0];seen.append(e);hit(e,60*.8**i,True);prev=e
            elif k=='hero':
                hit(first,42,True);hero_shots+=1
                if hero_shots%4==0:
                    for e in targets[:4]:hit(e,40,True)
            elif k=='verdict':hit(first,600,True)
            else:
                hit(first,{'double':40,'steel':16,'four':80}.get(k,20),k=='frost')
                if k=='frost' and first['kind']!='immune':first['slow']=t+3
        for e in enemies[:]:
            if e['hp']<=0:
                enemies.remove(e)
                children={'spore':['child']*2,'mother':['bud']*2,'bud':['tiny']*2}.get(e['kind'],[])
                for c in children:add(c,e['x'],e['lineage'])
        if big_start is not None and t>=big_start and big_clear is None and not any(p[2]=='big' for p in pending) and not any(e['lineage']=='big' for e in enemies):big_clear=t
        if wall<=0:return dict(cleared=False,wall_break_sec=t,remaining=len(enemies)+len(pending),damage_received=round(lost,1))
        if not enemies and not pending:return dict(cleared=True,climber_bypass_unresolved=climber_unresolved,clear_sec=t,big_lineage_clear_sec=big_clear,after_big_start_sec=None if big_clear is None else round(big_clear-big_start,2),wall_hp=round(wall,1),minimum_wall_hp=round(min_wall,1),damage_received=round(lost,1),repair_gold=round(lost*.25,1))
    return dict(cleared=False,timeout=900)

def split(c):
    a={};b={};pa=pb=0
    for k in sorted(c,key=lambda k:POINTS[k],reverse=True):
        for _ in range(c[k]):
            d=a if pa<=pb else b;d[k]=d.get(k,0)+1
            if d is a:pa+=POINTS[k]
            else:pb+=POINTS[k]
    return a,b
def points(c):return sum(POINTS[k]*n for k,n in c.items())
def independent_squad(camps=10,priests=1,travel_seconds=60):
    # Four newly recruited barracks2(+20%) armour3 militia, one priest.
    # No hero, no hero campXP. Healing only30/2.5s within8m, no potions.
    party=[dict(hp=180,maxhp=180,armor=3,priest=False) for _ in range(4)]+[dict(hp=180,maxhp=180,armor=0,priest=True) for _ in range(priests)]
    out=[]
    for campid in range(camps):
        for i,a in enumerate(party):a.update(x=-1 if i<4 else -6,y=[-3,-1,1,3][i] if i<4 else (i-4)*2,next=2.5 if a['priest'] else 0)
        enemies=[dict(hp=200,x=2,y=y,next=0,archer=False) for y in [-3,-1,1,3]]+[dict(hp=100,x=7,y=0,next=0,archer=True)]
        for tick in range(6001):
            t=tick*.05;living=[e for e in enemies if e['hp']>0]
            if not living:break
            if not any(a['hp']>0 and not a['priest'] for a in party):return {'completed':len(out),'failed_camp':campid+1,'failed_second':round(t,2),'remaining_hp':[round(max(0,a['hp']),1) for a in party],'events':out}
            for a in party:
                if a['hp']<=0:continue
                if a['priest']:
                    hurt=[z for z in party if z is not a and z['hp']>0 and z['hp']<z['maxhp'] and dist(a,z)<=8]
                    if hurt and t>=a['next']:
                        z=min(hurt,key=lambda z:z['hp']/z['maxhp']);z['hp']=min(z['maxhp'],z['hp']+30);a['next']=t+2.5
                else:
                    choices=[e for e in enemies if e['hp']>0]
                    if not choices:break
                    e=min(choices,key=lambda e:dist(a,e));move(a,e,3,1,.05)
                    if dist(a,e)<=1.00001 and t>=a['next']:e['hp']-=18;a['next']=t+1.5
            for e in living:
                if e['hp']<=0:continue
                alive=[a for a in party if a['hp']>0]
                if not alive:break
                a=min(alive,key=lambda a:dist(e,a));r=9 if e['archer'] else 1;move(e,a,3,r,.05)
                if dist(e,a)<=r+.00001 and t>=e['next']:
                    a['hp']-=(15 if e['archer'] else 20)*30/(30+a['armor']);e['next']=t+(2 if e['archer'] else 1.5)
        damage=sum(18 for a in party if a['hp']>0 and not a['priest']);demolition=math.ceil(300/damage)*1.5
        before=[round(max(0,a['hp']),1) for a in party]
        # Explicit60s travelling heal budget=24*30=720; same squad remains
        # within8m, priest must be alive. No revivals, only living damaged.
        living_priests=sum(a['hp']>0 and a['priest'] for a in party)
        if living_priests:
            for _ in range(int(travel_seconds/2.5)*living_priests):
                hurt=[a for a in party if 0<a['hp']<a['maxhp']]
                if hurt:a=min(hurt,key=lambda a:a['hp']/a['maxhp']);a['hp']=min(a['maxhp'],a['hp']+30)
        out.append(dict(camp=campid+1,guard_seconds=round(t,2),demolition_seconds=demolition,hp_before_travel_heal=before,hp_after_travel_heal=[round(max(0,a['hp']),1) for a in party],travel_heal_seconds=travel_seconds,hero_xp=0))
    return dict(completed=len(out),events=out,conditions='every camp4green+1archer; during travel within8m priest, line formation; upgrade/armour before new recruitment paid by economy')
# Proposed zero-random-drop magic route: no verdict/holy/assassin until materials
# allocated. Physical bases are deliberately preserved for spell immunity.
ARMIES=[(['arrow']*2+['frost'],['arrow']*2),(['arrow']*3+['frost'],['arrow']*3+['frost']),(['arrow']*4+['frost']*2+['ring'],['arrow']*4+['frost']*2),(['arrow']*5+['frost']*2+['ring'],['arrow']*5+['frost']*2),(['arrow']*5+['frost']*2+['ring','storm','cannon'],['arrow']*4+['double']*2+['frost']*2+['cannon']),(['arrow']*5+['frost']*2+['ring','storm','cannon','cannon'],['arrow']*4+['double']*2+['frost']*2+['cannon'])]
rows={'method':'0.05s camp nearest-target geometry +0.1s one-dimensional lane. NOT engine or playtest. Hero camp chain every4attacks fixed phase; no cards, no random crystals, no enemy rewards assumed. Workers assumed alive and continuous repairs; soldiers omitted from home DPS.','camp_prototype':{'building_hp':300,'building_armor':0,'building_attack':0,'building_xp':0,'guards':{'green':4,'archer':1},'coords':COORDS,'path_multiplier':1.25,'min_city_distance':min(math.hypot(*x) for x in COORDS),'min_pair_distance':min(math.dist(a,b) for i,a in enumerate(COORDS) for b in COORDS[i+1:])},'routes':{'four':route([0,1,2,3]),'three':route([0,1,3]),'two_fixed50':route([0,3]),'two_candidate65':route([0,3],crystal=65)},'s02_stages':[]}
for i,(stage,army) in enumerate(zip(STAGES,ARMIES)):
    a,b=split(stage[-1]);checks=[lane(a,army[0],hero=True),lane(b,army[1],hero=False)]
    rows['s02_stages'].append(dict(stage=i+1,big_budget=points(stage[-1]),laneA=a,laneB=b,hero_only_laneA=True,towersA=army[0],towersB=army[1],conditional_results=checks,base_normal_count=6,normal_point_budget=6*min(i+1,4),near_xp_from_all_home_roots_if_present=sum(points(c) for c in stage)*5+6*min(i+1,4)*5))
rows['s02_full_stage_pressure']=[]
for i,(stage,army) in enumerate(zip(STAGES,ARMIES)):
    schedules=[[],[]]
    for time,c in zip([60,150,240,310],stage):
        a,b=split(c)
        schedules[0].append((time,a,4 if time==310 else 2));schedules[1].append((time,b,4 if time==310 else 2))
    # Every ordinary cohort goesB worst local accumulation, no hero.
    for time in [40,100,140,200,260,300]:schedules[1].append((time,{'green':min(i+1,4)},1))
    rows['s02_full_stage_pressure'].append(dict(stage=i+1,normal_all_laneB=True,A=lane({},army[0],hero=True,scheduled=schedules[0]),B=lane({},army[1],scheduled=schedules[1]),total_root_budget=sum(points(c) for c in stage)+6*min(i+1,4)))
growth=[[],[]]
for time,c in zip([60,150,240,550],STAGES[3]):
    a,b=split(c)
    for j,d in enumerate([a,b]):growth[j].append((time,d,4 if time==550 else 2))
for j in range(2):growth[j].append((390,{'iron':2,'green':4},1));growth[j].append((394,{'archer':2},1))
# Clock log verified by normal_clock.py: obtain exact local times without
# rewriting/importing combat_check.py or any old script side effects.
from normal_clock import normal_spawn_times
gclock=normal_spawn_times([60,150,240,390,550])
assert len(gclock)==11
for time in gclock:growth[1].append((time,{'green':4},1))
rows['s02_growth_full_stage4']=dict(normal_times=gclock,A=lane({},ARMIES[3][0],hero=True,scheduled=growth[0]),B=lane({},ARMIES[3][1],scheduled=growth[1]),total_root_budget=sum(points(c) for c in STAGES[3])+44+32)
rows['conditional_clock_rederived']={}
for mode in ['S02','S02-G']:
    start=120;timeline=[]
    for i,s in enumerate(rows['s02_full_stage_pressure']):
        q=rows['s02_growth_full_stage4'] if mode=='S02-G' and i==3 else s
        localbig=550 if mode=='S02-G' and i==3 else 310
        clear=max(q[k]['big_lineage_clear_sec'] for k in ['A','B'])
        timeline.append(dict(stage=i+1,start_sec=round(start,2),big_spawn_sec=round(start+localbig,2),big_lineage_clear_sec=round(start+clear,2),local_lineage_clear_sec=clear,after_big_start_sec=round(clear-localbig,2)))
        start+=clear+(90 if i<5 else 0)
    rows['conditional_clock_rederived'][mode]=dict(stages=timeline,finish_sec=round(start,2),not_same_as_economy_nominal_clock=True)
rows['s01_home_hero_absent']={}
for i in range(2):
    a,b=split(STAGES[i][-1]);army=ARMIES[i]
    rows['s01_home_hero_absent'][str(i+1)]={'A':lane(a,army[0]),'B':lane(b,army[1])}
rows['s01_low_crystal_final']={'A':lane({'giant':1,'green':8,'iron':2,'spore':1},['arrow']*5+['frost']*2+['ring'],hero=True),'B':lane({'green':14,'immune':2,'archer':1,'javelin':1},['arrow']*5+['frost']*2)}
rows['growth_addition']={'extra_small':{'iron':4,'archer':4,'green':8},'extra_small_points':32,'extra_normals':5,'extra_normal_points':20,'extra_root_pressure':52,'extra_possible_nearby_xp':260,'extra_minutes':4,'no_random_material_credit':True,'lane_no_hero':lane({'iron':2,'archer':2,'green':4},ARMIES[3][1])}
rows['camp_chain_phase_sensitivity']=[]
for phase in range(4):
    party=[dict(hero=True,hp=720)]+[dict(hero=False,hp=150) for _ in range(4)]
    rows['camp_chain_phase_sensitivity'].append(camp(party,240,phase))
rows['routes']['four_fronttank']=route([0,1,2,3],fronttank=True)
rows['routes']['two_fronttank65']=route([0,3],crystal=65,fronttank=True)
rows['camp_initial_xp_sensitivity']={str(x):route([0,1,2,3],xp=x,fronttank=True) for x in [255,260,300,360]}
rows['teaching_guard_variants']={'four_guard_armor3':route([0,3],crystal=65,fronttank=True,militia_armor=3),'three_green_four_militia':route([0,3],crystal=65,fronttank=True,greens=3),'three_green_four_armored':route([0,3],crystal=65,fronttank=True,greens=3,militia_armor=3),'three_green_two_armored':route([0,3],crystal=65,fronttank=True,greens=3,militia_count=2,militia_armor=3)}
rows['independent_camp_squad']=independent_squad()
rows['independent_camp_squad_two_priests']=independent_squad(priests=2)
rows['independent_camp_squad_30s_heal']=independent_squad(priests=2,travel_seconds=30)
rows['independent_camp_squad_20s_heal']=independent_squad(priests=2,travel_seconds=20)
rows['s02_minimal_550_final']={'A':lane(split(STAGES[5][-1])[0],['arrow']*5+['frost']*2+['ring','storm','cannon','cannon'],hero=True),'B':lane(split(STAGES[5][-1])[1],['arrow']*4+['double']*2+['frost']*2+['cannon'])}
PRICE={'arrow':(2400,200,0,0),'frost':(3600,260,0,0),'ring':(4800,400,50,30),'storm':(9000,600,100,70),'double':(4800,400,50,0),'cannon':(5600,400,50,0)}
rows['s02_cost_cumulative']=[]
owned={}
for i,army in enumerate(ARMIES):
    now={k:sum(a.count(k) for a in army) for k in PRICE}
    for k,v in now.items():owned[k]=max(owned.get(k,0),v)
    rows['s02_cost_cumulative'].append(dict(stage=i+1,owned=owned.copy(),active=now,spare_arrows=owned['arrow']-now['arrow'],tower_count=sum(owned.values()),tower_gold=sum(PRICE[k][0]*v for k,v in owned.items()),tower_maintenance=sum(PRICE[k][1]*v for k,v in owned.items()),tower_energy=sum(PRICE[k][2]*v for k,v in owned.items()),tower_crystal=sum(PRICE[k][3]*v for k,v in owned.items()),tower_iron=owned['double']*40+owned['cannon']*60,not_included='research centres magic400crystal+tech100iron, army20, barracks upgrades, shrine40, priests10, alchemy25 upfront/75 quota, wall repair, energy producers'))
rows['camp_coverage_sensitivity']={str(r):route([0,3],xp=int(240*r),crystal=65,fronttank=True,greens=3,militia_armor=3) for r in [.6,.75,1.]}
# Machine economic input only accepts successfully cleared camps. The default
# four-camp route is not claimed completed. S01-L is explicitly a new candidate.
candidate=rows['routes']['two_fronttank65']
events=[dict(second=510,xp=240,source='stage1 full nearby coverage conditional; 48 root points*5')]
for e in candidate['events']:
    for kill in e['combat']['kills']:events.append(dict(second=round(e['arrive_sec']+kill['time'],2),xp=kill['xp'],source=f"camp{e['camp']} {kill['kind']} {kill['owner']}"))
camps=[dict(id=e['camp'],pos=e['coordinate'],clear_second=e['reward_sec'],crystal=e['crystal'],guard_points=6,teaching_candidate=True) for e in candidate['events'] if e['reward_sec'] is not None]
normal=lane({'green':3},['arrow']*3+['frost'])
# First stage3 normal spawn1130; hero has returned1094.43, stays15m from
# these deaths. Credit conservative near5 even if hero could last-hit10.
normal_death=1130+normal['clear_sec']
events.append(dict(second=normal_death,xp=15,source='first stage3 normal3green; home hero15m, three nearby allykills; candidate lane clock'))
events.append(dict(second=normal_death+60,xp=15,source='second stage3 normal3green; home hero15m, three nearby allykills; candidate lane clock'))
rows['s01_return_normal']=dict(spawn_second=1130,hero_return_second=candidate['return_sec'],near_xp=15,all_clear_second=normal_death,model=normal,level_after_first=level(candidate['final_xp']+15),level_after_second=level(candidate['final_xp']+30))
econ={'S01魔法':{'configuration':'S01-L candidate only; camp65+heroLv4gate not adopted formal', 'camps':camps,'xp_events':events,'absences':[[657,candidate['return_sec']]],'losses':[{'second':902.36,'type':'militia','count':2,'replacement_gold':2400}], 'hero_home_return_hp':candidate['events'][-1]['combat']['survivors'][0]['hp'],'base_190_route_not_closed':True},'经济稳守':{'camps':[],'xp_events':[],'absences':[],'camp_schedule_status':'not validated; not assumed to collect crystals'},'科技扩矿':{'camps':[],'xp_events':[],'absences':[],'camp_schedule_status':'not validated; not assumed to collect crystals'},'魔法远征':{'camps':[],'xp_events':[],'absences':[],'camp_schedule_status':'not validated; 500/680 cumulative crystal remains conditional, cannot claim hero simultaneously at home'}}
econ['S01魔法']['configuration']='S01-L candidate only: two camps65, original heroLv5 gate, reached after returning home; not adopted formal'
econ['S01魔法']['losses'][0]['second']=candidate['events'][-1]['reward_sec']
(ROOT/'round3_combat_events.json').write_text(json.dumps(econ,ensure_ascii=False,indent=2),encoding='utf-8')
assert rows['growth_addition']['extra_root_pressure']==52
assert all(points(s[-1])==n for s,n in zip(STAGES,[16,36,64,96,132,180]))
(ROOT/'round3_combat_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in rows.items() if k not in ['camp_chain_phase_sensitivity']},ensure_ascii=False,indent=2))
