"""Round4 fixture audit. Read-only AST load of round3 functions (no old main).
Dynamic assets: no phase-preplaced towers/walls/repairers. Not an engine test.
"""
import ast,json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).parent
old=ast.parse((ROOT/'round3_combat_check.py').read_text(encoding='utf-8'))
cfg=json.loads((ROOT/'survival_config.json').read_text(encoding='utf-8'))
POINTS=cfg['threat_points'];STAGES=cfg['stages']
HP={'green':200,'archer':100,'spore':240,'climber':120,'javelin':150,'immune':300,'iron':300,'boar':500,'mother':360,'giant':2000,'bud':150,'child':80,'tiny':60}
ARM={'immune':10,'iron':30,'boar':5,'giant':5}
COORDS=[(350,0),(450,100),(550,0),(450,-100)]
readonly={'math':math,'POINTS':POINTS,'HP':HP,'ARM':ARM,'STAGES':STAGES,'COORDS':COORDS}
defs=[n for n in old.body if isinstance(n,ast.FunctionDef)]
exec(compile(ast.Module(body=defs,type_ignores=[]),'round3-readonly-definitions','exec'),readonly)
def level(xp):return min(15,readonly['level'](xp))
split=readonly['split'];points=readonly['points']
from normal_clock import normal_spawn_times

def camp_party(militia=4,guns=0,armor=3,hero=False,xp=0,carry=None):
    party=carry if carry is not None else [dict(kind='militia',hp=150,maxhp=150,armor=armor,dmg=15,range=1,interval=1.5) for _ in range(militia)]+[dict(kind='musket',hp=100,maxhp=100,armor=0,dmg=40,range=10,interval=2.5) for _ in range(guns)]+([dict(kind='hero',hp=600+40*(level(xp)-1),maxhp=600+40*(level(xp)-1),armor=5,dmg=30+3*(level(xp)-1),range=8,interval=1.5)] if hero else [])
    for i,a in enumerate(party):a.update(x=0 if a['kind']=='hero' else (-1 if a['kind']=='militia' else -7),y=(i%4-1.5)*2 if a['kind']!='hero' else 0,next=0)
    enemies=[dict(kind='green',hp=200,x=2,y=y,next=0) for y in [-3,-1,1,3]]+[dict(kind='archer',hp=100,x=7,y=0,next=0)]
    kills=[];hero_shots=0
    def hit(e,d,a,t):
        nonlocal xp
        e['hp']-=d
        if e['hp']<=0:
            h=next((z for z in party if z['kind']=='hero' and z['hp']>0),None)
            gain=POINTS[e['kind']]*(10 if a['kind']=='hero' else (5 if h and readonly['dist'](h,e)<=15 else 0))
            before=level(xp);xp+=gain
            if h and level(xp)>before:h['hp']=h['maxhp']=600+40*(level(xp)-1);h['dmg']=30+3*(level(xp)-1)
            kills.append(dict(second=round(t,2),kind=e['kind'],owner=a['kind'],hero_xp=gain))
    for tick in range(6001):
        t=tick*.05;live=[e for e in enemies if e['hp']>0]
        if not live:break
        if not any(a['hp']>0 for a in party):return dict(success=False,time=t,party=party,kills=kills,xp=xp)
        for a in party:
            choices=[e for e in enemies if e['hp']>0]
            if a['hp']<=0 or not choices:continue
            e=min(choices,key=lambda z:readonly['dist'](a,z));readonly['move'](a,e,3,a['range'],.05)
            if readonly['dist'](a,e)<=a['range']+.00001 and t>=a['next']:
                a['next']=t+a['interval'];hit(e,a['dmg'],a,t)
                if a['kind']=='hero':
                    hero_shots+=1
                    if hero_shots%4==0:
                        prev=e;seen=[]
                        for _ in range(4):
                            choices=[z for z in enemies if z['hp']>0 and z not in seen and readonly['dist'](prev,z)<=5]
                            if not choices:break
                            z=min(choices,key=lambda z:readonly['dist'](prev,z));seen.append(z);hit(z,40,a,t);prev=z
        for e in live:
            if e['hp']<=0:continue
            alive=[a for a in party if a['hp']>0]
            if not alive:break
            a=min(alive,key=lambda z:readonly['dist'](e,z));r=9 if e['kind']=='archer' else 1;readonly['move'](e,a,3,r,.05)
            if readonly['dist'](e,a)<=r+.00001 and t>=e['next']:
                a['hp']-=(15 if e['kind']=='archer' else 20)*30/(30+a['armor']);e['next']=t+(2 if e['kind']=='archer' else 1.5)
    else:return dict(success=False,timeout=300,party=party,kills=kills,xp=xp)
    demolition=math.ceil(300/sum(a['dmg'] for a in party if a['hp']>0))*1.5
    return dict(success=True,guard_seconds=round(t,2),demolition_seconds=demolition,time=round(t+demolition,2),party=party,kills=kills,xp=xp,hero_level=level(xp),no_free_healing=True)

TOWER={'arrow':(300,3,20,1.5,10),'frost':(300,3,20,1.5,10),'double':(400,5,40,1.5,10),'cannon':(400,5,40,3,12),'steel':(500,8,16,1,12),'ring':(350,5,3,.5,6),'storm':(450,5,60,2.5,11),'corrosion':(350,5,10,2,12),'sentry':(300,5,0,1,0)}
def dynamic(scenario):
    events=sorted(scenario.get('events',[]),key=lambda z:z['second']);index=0;assets={};enemies=[];pending=[]
    hero=dict(id='HERO',kind='hero',lane='A',hp=600,maxhp=600,armor=5,dmg=30,interval=1.5,range=8,next=0,x=-4)
    xp=0;hero_shots=0;phase=0;start=120.;big_open=False;rest_until=None;phase_log=[];losses=[];external_losses=[];xp_log=[];repair_gold=0.;repair_seconds=0.;repair_payments={};wave_log=[];config_errors=[];climbers=0;transit_until=0.;arrival_lane=None;hero_moves=[]
    def queue_phase(at,i):
        for local,c in zip([60,150,240,310],STAGES[i]):
            if local!=310 and i<2:
                single=scenario.get('early_small_lane','B');a,b=(c,{}) if single=='A' else ({},c)
            else:a,b=split(c)
            for ln,comp in [('A',a),('B',b)]:
                n=0
                for k,count in comp.items():
                    for _ in range(count):pending.append(dict(at=at+local+n%(4 if local==310 else 2)*(8 if local==310 else 4),kind=k,lane=ln,phase=i+1,lineage='big' if local==310 else 'small',root=True));n+=1
        for local in normal_spawn_times([60,150,240,310]):
            for _ in range(min(i+1,4)):pending.append(dict(at=at+local,kind='green',lane='B',phase=i+1,lineage='normal',root=True))
    queue_phase(start,0)
    def present(t):return hero['hp']>0 and t>=transit_until and not any(a<=t<b for a,b in scenario.get('hero_absences',[]))
    def damage(e,d,source,t,magic=False):
        nonlocal xp
        if e['hp']<=0 or magic and e['kind']=='immune':return
        e['hp']-=d if magic else d*30/(30+e['armor'])
        if e['hp']<=0 and e['root']:
            eligible=present(t) and e['lane']==hero['lane'] and abs(e['x']-hero['x'])<=15
            gain=POINTS[e['kind']]*(10 if source is hero else 5) if eligible else 0
            before=level(xp);xp+=gain
            xp_log.append(dict(second=t,kind=e['kind'],points=POINTS[e['kind']],owner_id=source['id'],owner_kind=source['kind'],death_lane=e['lane'],hero_lane=hero['lane'],hero_present=present(t),hero_gain=gain,reason=('personal10' if source is hero else 'nearby15m5') if eligible else 'outside_or_transit0',cumulative=xp,level=level(xp)))
            if level(xp)>before:hero['hp']=hero['maxhp']=600+40*(level(xp)-1);hero['dmg']=30+3*(level(xp)-1)
    for tick in range(60001):
        t=tick/10
        if arrival_lane is not None and t>=transit_until:hero['lane']=arrival_lane;arrival_lane=None
        if scenario.get('hero_policy')=='respond_to_small' and phase<2 and rest_until is None and any(abs(t-(start+local))<.01 for local in [60,150,240]):
            targetlane=scenario.get('early_small_lane','B')
            if hero['lane']!=targetlane:
                travel=scenario.get('lane_separation_m',54)/3;transit_until=t+travel;arrival_lane=targetlane;hero_moves.append(dict(depart=t,arrive=transit_until,from_lane=hero['lane'],to_lane=targetlane,path_m=scenario.get('lane_separation_m',54),xp_while_transit=0))
        while index<len(events) and events[index]['second']<=t:
            ev=events[index];index+=1;typ=ev.get('type');k=ev.get('kind');uid=ev.get('id');ln=ev.get('lane','A')
            if typ in ['tower_complete','wall_complete','unit_complete','worker_complete']:
                if uid in assets and assets[uid]['hp']>0:config_errors.append(f'duplicate live asset {uid} at{t}')
                if typ=='tower_complete':
                    if k not in TOWER:config_errors.append(f'unsupported tower {k}');continue
                    hp,ar,d,interval,r=TOWER[k];asset=dict(hp=hp,maxhp=hp,armor=ar,dmg=d,interval=interval,range=r,x=-1)
                elif typ=='wall_complete':asset=dict(hp=ev.get('hp',2000),maxhp=ev.get('hp',2000),armor=15,dmg=0,range=0,x=0)
                elif typ=='worker_complete':k='worker';asset=dict(hp=100,maxhp=100,armor=0,dmg=0,range=0,x=-3,busy=ev.get('role')!='repair_only',role=ev.get('role'))
                else:
                    factor={1:1,2:1.2,3:1.4}.get(ev.get('facility_level',ev.get('level',1)),1)
                    hp,d,r,it={'militia':(150,15,1,1.5),'musket':(100,40,10,2.5),'knight':(250,25,1,1.5),'priest':(180,0,8,2.5)}.get(k,(0,0,0,1))
                    if hp==0:config_errors.append(f'unsupported unit{k}');continue
                    asset=dict(hp=hp*factor,maxhp=hp*factor,armor=ev.get('armor',0),dmg=d*factor,interval=it,range=r,x=0 if r==1 else -3)
                asset.update(id=uid,kind=k,lane=ln,next=t,created=t);assets[uid]=asset
            elif typ in ['tower_destroyed','wall_destroyed','unit_destroyed','worker_destroyed']:
                if uid in assets:
                    external_losses.append(dict(second=t,id=uid,kind=assets[uid]['kind'],type=typ,was_alive=assets[uid]['hp']>0));assets[uid]['hp']=0
            elif typ=='worker_state' and uid in assets:assets[uid]['busy']=ev.get('busy',True)
            elif typ in ['hero_move','hero_present']:hero['lane']=ln
            elif typ=='worker_task_start' and uid in assets:
                assets[uid].update(busy=True,lane=ln,job_kind=ev.get('kind'),work_begin=ev['second']+ev.get('walk_seconds',0),work_end=ev.get('until_second',ev['second']))
            elif typ=='worker_task_finish' and uid in assets:assets[uid]['busy']=assets[uid].get('role')!='repair_only';assets[uid]['lane']=ln;assets[uid]['work_end']=t
            elif typ=='unit_loss':
                victims=[a for a in assets.values() if a['hp']>0 and a['kind']==k]
                for a in victims[:ev.get('count',1)]:external_losses.append(dict(second=t,id=a['id'],kind=k,type='unit_loss'));a['hp']=0
            elif typ not in ['notes',None]:config_errors.append(f'unsupported event {typ}')
        for p in pending[:]:
            if p['at']<=t:
                e=dict(p,hp=HP[p['kind']],armor=ARM.get(p['kind'],0),x=150.,next=t,slow=0,shots=0);enemies.append(e);pending.remove(p);wave_log.append(dict(second=t,stage=p['phase'],kind=p['kind'],lineage=p['lineage'],lane=p['lane']))
        if t>=start+310 and rest_until is None:big_open=True
        for e in enemies:
            if e['hp']<=0:continue
            k=e['kind']
            if e.get('corrode_expiry',0)<=t:e['armor']=ARM.get(k,0)
            friends=[a for a in assets.values() if a['hp']>0 and a['lane']==e['lane'] and not(a['kind']=='worker' and a.get('job_kind')!='repair' and a.get('work_begin',1e9)<=t<a.get('work_end',-1))]
            if present(t) and hero['lane']==e['lane']:friends.append(hero)
            if not friends:continue
            target=max(friends,key=lambda a:a['x']);r={'archer':9,'javelin':8}.get(k,1)
            if k=='javelin' and e['shots']>=5:r=1
            speed={'giant':1.6,'iron':2.4,'immune':2.8,'boar':5.5,'climber':5,'child':3.4,'tiny':3.6}.get(k,3)
            e['x']=max(target['x']+r,e['x']-speed*(.6 if e['slow']>t else 1)*.1)
            if k=='climber' and target['kind']=='wall' and e['x']<=1:climbers+=1;config_errors.append('climber reached wall; bypass2D unresolved');break
            if e['x']<=target['x']+r and t>=e['next']:
                d={'giant':80,'iron':25,'boar':25,'archer':15,'javelin':40 if e['shots']<5 else 15,'climber':15,'spore':15,'mother':18,'child':10,'bud':12,'tiny':8}.get(k,20)
                target['hp']-=d*30/(30+target['armor']);e['shots']+=1;e['next']=t+{'giant':2.5,'archer':2,'climber':1.2,'child':1.2,'bud':1.2,'tiny':1.2}.get(k,1.5)
                if target['hp']<=0:losses.append(dict(second=t,id=target['id'],kind=target['kind'],lane=e['lane']))
        live=[a for a in assets.values() if a['hp']>0]+([hero] if present(t) else [])
        for a in live:
            if a['kind']=='priest':
                hurt=[b for b in live if b is not a and b['kind']!='wall' and b['kind'] not in TOWER and b['lane']==a['lane'] and abs(b['x']-a['x'])<=8 and b['hp']<b['maxhp']]
                if hurt and t>=a['next']:b=min(hurt,key=lambda b:b['hp']/b['maxhp']);b['hp']=min(b['maxhp'],b['hp']+30);a['next']=t+2.5
                continue
            if not a['dmg']:continue
            choices=sorted([e for e in enemies if e['hp']>0 and e['lane']==a['lane'] and abs(e['x']-a['x'])<=a['range']],key=lambda e:e['x'])
            if a['kind']=='cannon':choices=[e for e in choices if abs(e['x']-a['x'])>=4]
            if a['kind']=='storm':choices=[e for e in choices if e['kind']!='immune']
            if a['kind']=='corrosion':choices=sorted(choices,key=lambda e:(e['armor']<=-15,e['x']))
            if not choices or t<a['next']:continue
            k=a['kind']
            if k=='steel':
                if t-a.get('last_shot',-99)>2:a['warm_start']=t
                a['interval']=1/(1+min(3,t-a.get('warm_start',t)));a['last_shot']=t
            a['next']=t+a['interval'];first=choices[0]
            if k in ['cannon','ring']:
                for e in choices:
                    if k=='ring' or abs(e['x']-first['x'])<=3:damage(e,a['dmg'],a,t,k=='ring')
            elif k=='storm':
                prev=first;seen=[]
                for i in range(5):
                    opts=[e for e in choices if e not in seen and (i==0 or abs(e['x']-prev['x'])<=5)]
                    if not opts:break
                    e=opts[0];seen.append(e);damage(e,60*.8**i,a,t,True);prev=e
            elif k=='hero':
                damage(first,a['dmg'],a,t,True);hero_shots+=1
                if hero_shots%4==0:
                    for e in choices[:4]:damage(e,40,a,t,True)
            elif k=='double':
                damage(first,20,a,t)
                second=choices[1] if len(choices)>1 else first
                damage(second,20,a,t)
            else:
                damage(first,a['dmg']*(1.5 if k=='knight' and first['kind'] in ['archer','javelin'] else 1),a,t,k=='frost')
                if k=='frost' and first['kind']!='immune':first['slow']=t+3
                if k=='corrosion':first['armor']=max(-15,first['armor']-4);first['corrode_expiry']=t+8
        # Only explicit available repairers, same lane; no free construction
        # workers secretly repairing. Wall HP persists over all stages/rests.
        if scenario.get('repair_policy')=='available_workers':
            for ln in ['A','B']:
                ws=[a for a in assets.values() if a['hp']>0 and a['lane']==ln and a['kind']=='worker' and not a.get('busy',True)]
                walls=[a for a in assets.values() if 0<a['hp']<a['maxhp'] and a['kind']=='wall' and a['lane']==ln]
                for w,b in zip(ws,walls):
                    healed=min(2000/60*.1,b['maxhp']-b['hp']);b['hp']+=healed;repair_gold+=healed*.25;repair_seconds+=healed/(2000/60)
                    sec=math.ceil(t);repair_payments[sec]=repair_payments.get(sec,0)+healed*.25
        for e in enemies[:]:
            if e['hp']<=0:
                enemies.remove(e)
                for child in {'spore':['child']*2,'mother':['bud']*2,'bud':['tiny']*2}.get(e['kind'],[]):enemies.append(dict(e,kind=child,hp=HP[child],armor=0,root=False,next=t,slow=0))
        if config_errors:break
        if hero['hp']<=0:config_errors.append('hero_dead_no_free_revive');break
        if big_open and not any(e['phase']==phase+1 and e['lineage']=='big' for e in enemies) and not any(p['phase']==phase+1 and p['lineage']=='big' for p in pending):
            phase_log.append(dict(stage=phase+1,start_sec=start,big_spawn_sec=start+310,big_clear_sec=t,hero_xp=xp,hero_level=level(xp),remaining_non_big={ln:sum(e['hp']>0 and e['lineage']!='big' and e['lane']==ln for e in enemies) for ln in ['A','B']},walls={a['id']:round(a['hp'],1) for a in assets.values() if a['kind']=='wall'},repair_gold=round(repair_gold,2),repair_worker_seconds=round(repair_seconds,2),alive_assets={k:sum(a['hp']>0 and a['kind']==k for a in assets.values()) for k in TOWER}))
            big_open=False
            if phase==5:break
            rest_until=t+90
        if rest_until is not None and t>=rest_until:
            phase+=1;start=rest_until;rest_until=None;queue_phase(start,phase)
        # If there are live enemies but zero defending entities, stop rather
        # than silently letting them stand beyond the map until future towers.
        for ln in ['A','B']:
            if any(e['hp']>0 and e['lane']==ln and e['x']<=10 for e in enemies) and not any(a['hp']>0 and a['lane']==ln for a in assets.values()) and not(present(t) and hero['lane']==ln):config_errors.append(f'undefended_lane_{ln}');break
        if config_errors:break
    return dict(status='conditional_fixture_survived' if len(phase_log)==6 and not config_errors else 'not_closed',stop_sec=t,phases=phase_log,losses=losses,external_losses=external_losses,repair_gold=round(repair_gold,2),repair_worker_seconds=round(repair_seconds,2),repair_spend_events=[dict(second=s,gold=round(g,6)) for s,g in sorted(repair_payments.items())],hero_xp=xp,hero_level=level(xp),hero_xp_log=xp_log,hero_movements=hero_moves,errors=config_errors,wall_hp_persisted=True,normal_all_laneB=True,early_small_single_lane=scenario.get('early_small_lane','B'),map_scope='synthetic_1D_two_lane_fixture; positions converted by economic author; not random portals/navmesh',limitations=['all lane assets collinear; melee guard at gate gap','construction sites absent before completion: unsafe build vulnerability not verified','no free initial wall or repairer','workers survive only if nearest defenders protect them','random portal directions not sampled; labelled legal one-door extremes'],asset_event_count=len(events))

def main():
    prior=ROOT/'round4_combat_results.json';checkpoint=ROOT/'round4_combat_prior_failure.json'
    if prior.exists() and not checkpoint.exists():
        previous=json.loads(prior.read_text(encoding='utf-8'))
        if previous.get('dynamic_hero_response',{}).get('经济稳守工业保险',{}).get('status')=='not_closed':checkpoint.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
    cases={}
    for m,g,h,x in [(4,0,False,0),(4,2,False,0),(4,4,False,0),(2,4,False,0),(4,0,True,370)]:
        name=f'militia{m}_guns{g}_hero{h}'
        c=camp_party(m,g,hero=h,xp=x);cases[name]=c
        if c['success'] and not h:
            cases[name+'_second_no_heal']=camp_party(carry=[dict(a) for a in c['party']],hero=False,xp=0)
    path=ROOT/'round4_economy_events.json'
    inputs=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    scenarios=inputs.get('scenarios',inputs)
    results={'schema':'round4_fixture_v1','method':'read-only round3 definitions; actual completion/death events; no preplaced phase army','camp_bootstrap':cases,'dynamic':{},'dynamic_smallA':{},'dynamic_hero_response':{},'economic_input_present':path.exists(),'economic_input_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,'economic_input_snapshot':inputs}
    for name,s in scenarios.items():
        if isinstance(s,dict) and 'events' in s:
            results['dynamic'][name]=dynamic(s)
            results['dynamic_smallA'][name]=dynamic(dict(s,early_small_lane='A'))
            results['dynamic_hero_response'][name]=dynamic(dict(s,hero_policy='respond_to_small',lane_separation_m=54))
    (ROOT/'round4_combat_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    feedback={}
    for name,r in results['dynamic_hero_response'].items():
        feedback[name]=dict(clock={'big_seconds':[p['big_spawn_sec'] for p in r['phases']],'end_second':r['stop_sec']},defeat_second=None if len(r['phases'])==6 and not r['errors'] else r['stop_sec'],repair_spend_events=r['repair_spend_events'],hero_movements=r['hero_movements'],actual_losses=r['losses'],economic_input_sha256=results['economic_input_sha256'],hero_policy='respond_to_small, first2 singleB; third+ split',map_scope='synthetic_fixture_only')
    (ROOT/'round4_combat_feedback.json').write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'camp_bootstrap':{k:{a:b for a,b in v.items() if a not in ['party','kills']} for k,v in cases.items()},'dynamic':results['dynamic']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
