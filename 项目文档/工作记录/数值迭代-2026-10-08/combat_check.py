"""离线算式与离散事件校验；不是游戏实测。Python 标准库，输出同目录 JSON。"""
import json
import sys
from pathlib import Path
from normal_clock import normal_spawn_times

def ehp(hp, armor):
    return hp * (armor + 30) / 30

def duel_with_priest():
    # 零距离，双方第一击 t=0；牧师第一口 t=2.5，之后每2.5s。
    ally, enemy = 150., 200.
    for tick in range(2001):
        t = tick / 20
        if tick % 30 == 0:
            enemy -= 15
            if enemy <= 0:
                return {"winner":"militia", "time":t, "militia_hp":ally}
            ally -= 20
        if tick > 0 and tick % 50 == 0:
            ally = min(150, ally + 30)
        if ally <= 0:
            return {"winner":"green", "time":t, "green_hp":enemy}

def assassin_hits(hp, armor, cap=None):
    n=0
    while hp>0 and n<1000:
        extra=hp*.2
        if cap is not None: extra=min(extra,cap)
        hp-=(20+extra)*30/(armor+30)
        n+=1
    return n

rows = {
  "method":"analytic and discrete event assumptions; not playtest",
  "priest_duel":duel_with_priest(),
  "wall": {"ehp":ehp(2000,15),"old_repair_hp_s":2000/15,
     "ten_green_incoming_hp_s":10*(20/1.5)*30/45,
     "proposal_repair_hp_s":2000/60},
  "steel_vs_four_arrows": {"old_steel_dps":8*4,"four_arrows_dps":4*20/1.5,
     "proposal_steel_dps":16*4,"old_steel_first_3s_damage":8*(1+4)/2*3,
     "proposal_steel_first_3s_damage":16*(1+4)/2*3},
  "armor": {str(a):30/(a+30) for a in [-15,-12,-8,-4,0,5,10,30]},
  "assassin_giant": {"old_hits":assassin_hits(2000,5),"capped_80_hits":assassin_hits(2000,5,80)},
  "laser_continuous": {"tower_cycle_damage":2.4*40+2.4*60+1.2*80,
     "tower_cycle_dps":(2.4*40+2.4*60+1.2*80)/14,
     "ship_cycle_damage":6*20+6*30+3*40,
     "ship_cycle_dps":(6*20+6*30+3*40)/19},
  "scenario_first_flag": {"hp_budget":12*200+2*100,"defense_dps":2*20/1.5+40,
     "ideal_clear_seconds":(12*200+2*100)/(2*20/1.5+40)},
  "scenario_armored": {"three_iron_hp":900,"two_arrows_dps":2*20/1.5*.5,
     "two_arrows_clear_seconds":900/(2*20/1.5*.5),
     "arrow_frost_dps":20/1.5*.5+20/1.5,
     "arrow_frost_clear_seconds":900/(20/1.5*.5+20/1.5)},
  "scenario_immune": {"four_immune_hp":1200,"four_arrows_dps":4*20/1.5*.75,
     "clear_seconds":1200/(4*20/1.5*.75),"all_magic_dps":0},
  "scenario_final_giant": {"giant_ehp":ehp(2000,5),
     "steel_2_arrows_magic_total_dps":64*30/35+2*20/1.5*30/35+30,
     "ideal_giant_seconds":2000/(64*30/35+2*20/1.5*30/35+30)},
  "hero_new_xp": {"level5":sum(40+20*n for n in range(1,5)),
     "level10":sum(40+20*n for n in range(1,10)),
     "level15":sum(40+20*n for n in range(1,15))},
}
POINTS={'green':1,'archer':2,'spore':3,'climber':3,'javelin':3,'immune':4,'iron':4,'boar':5,'mother':7,'giant':18}
HP={'green':200,'archer':100,'spore':240,'climber':120,'javelin':150,'immune':300,'iron':300,'boar':500,'mother':360,'giant':2000}
ARM={'green':0,'archer':0,'spore':0,'climber':0,'javelin':0,'immune':10,'iron':30,'boar':5,'mother':0,'giant':5}
DROP={'green':.3,'archer':.3,'spore':.15,'climber':.2,'javelin':.3,'immune':.45,'iron':.45,'boar':1.,'mother':.375,'giant':4.}
def comp(budget, **special):
    left=budget-sum(POINTS[k]*v for k,v in special.items())
    assert left>=0,(budget,special)
    if left: special['green']=special.get('green',0)+left
    assert sum(POINTS[k]*v for k,v in special.items())==budget
    return special
STAGES=[
 [comp(6),comp(9,archer=1),comp(12,archer=2),comp(16,archer=2)],
 [comp(12,iron=1,archer=1),comp(16,spore=1,archer=3),comp(20,spore=1,archer=2,javelin=1,climber=1),comp(36,iron=2,spore=2,javelin=2,archer=2)],
 [comp(20,immune=1,boar=1,archer=2),comp(26,immune=2,iron=1,climber=2),comp(32,immune=2,iron=2,javelin=2),comp(64,giant=1,immune=2,iron=2,archer=1,spore=1,javelin=1)],
 [comp(36,immune=2,iron=2,boar=2,javelin=2),comp(44,mother=1,iron=3,archer=3,climber=2),comp(52,immune=3,boar=3,spore=3,javelin=3),comp(96,giant=1,immune=4,iron=4,spore=3,boar=3,javelin=4,archer=3)],
 [comp(52,mother=2,iron=4,boar=3),comp(64,immune=4,boar=4,javelin=4,archer=4),comp(76,mother=3,iron=5,climber=4,javelin=4),comp(132,giant=2,immune=4,iron=4,mother=2,boar=4,javelin=4,archer=4)],
 [comp(72,immune=4,iron=4,mother=2,boar=4),comp(88,mother=4,javelin=6,archer=6,climber=6),comp(104,immune=6,iron=6,boar=6,javelin=6),comp(180,giant=3,immune=6,iron=6,mother=4,boar=4,javelin=4,archer=4)],
]
def schedule(local_times, stages):
    result=[];start=120;xp=0;crystal=0
    # 清场预测含门分批、真实路径40–156秒、交战；范围另列。
    clear_after=[110,120,165,175,185,210]
    for i,stage in enumerate(stages):
        normal=len(normal_spawn_times(local_times))*min(i+1,4)
        for j,c in enumerate(stage):
            if j==3:xp+=normal*5;crystal+=normal*.3
            b=sum(POINTS[k]*v for k,v in c.items());xp+=b*5
            crystal+=sum(DROP[k]*v for k,v in c.items())
            result.append({'stage':i+1,'type':'big' if j==3 else 'small','spawn_sec':start+local_times[j],
               'budget':b,'composition':c,'cumulative_nearby_xp':xp,'cumulative_expected_drop_crystals':round(crystal,3)})
        start+=local_times[-1]+clear_after[i]+(90 if i<len(stages)-1 else 0)
    return {'waves':result,'predicted_end_sec':start,
            'normal_local_spawn_seconds':normal_spawn_times(local_times),
            'normal_root_budget_per_stage':[len(normal_spawn_times(local_times))*min(i+1,4) for i in range(len(stages))]}
rows['s01']=schedule([60,140,220,280],STAGES[:3])
rows['s02']=schedule([60,150,240,310],STAGES)

def lane_sim(composition, towers, wall_layers=1, hero=False, repair=True):
    # 0.1s固定步长。150m同一通道；塔距墙1.0m，分批每8秒。
    enemies=[];pending=[];number=0
    for kind,n in composition.items():
        for _ in range(n):
            pending.append((number%4*8,kind));number+=1
    walls=wall_layers*2000.;lost=0.;spawns=0;first_contact=None;hero_hit=0
    ts=[dict(kind=k,next=0.) for k in towers]+([dict(kind='hero',next=0.)] if hero else [])
    def add(k,x):
        nonlocal spawns
        spawns+=1
        enemies.append(dict(kind=k,hp=HP.get(k,80),armor=ARM.get(k,0),x=x,next=0.,slow=0.))
    def hit(e,d,magic=False):
        if magic and e['kind']=='immune':return
        e['hp']-=d if magic else d*30/(30+e['armor'])
    for step in range(4200):
        t=step/10
        while pending and min(z[0] for z in pending)<=t:
            z=min(pending,key=lambda z:z[0]);pending.remove(z);add(z[1],150.)
        for e in enemies:
            kind=e['kind'];v={'giant':1.6,'iron':2.4,'immune':2.8,'boar':5.5,'climber':5.}.get(kind,3.)
            stop={'archer':9.,'javelin':8.}.get(kind,1.)
            e['x']=max(stop,e['x']-v*(.6 if e['slow']>t else 1)*.1)
            if e['x']<=stop and t>=e['next'] and e['hp']>0:
                if first_contact is None:first_contact=t
                dmg={'giant':80,'iron':25,'boar':25,'archer':15,'javelin':40,'spore':15,'mother':18,'child':10}.get(kind,20)
                interval={'giant':2.5,'archer':2.,'child':1.2}.get(kind,1.5)
                dealt=dmg*30/45;walls-=dealt;lost+=dealt;e['next']=t+interval
        if repair and walls>0:walls=min(wall_layers*2000,walls+33.333333*.1)
        for tower in ts:
            k=tower['kind'];radius={'ring':6,'cannon':12,'verdict':12,'hero':8}.get(k,10)
            targets=sorted((e for e in enemies if e['hp']>0 and e['x']+1.0<=radius),key=lambda e:e['x'])
            if k=='cannon':targets=[e for e in targets if e['x']+1.0>=4]
            if not targets or t<tower['next']:continue
            first=targets[0]
            interval={'cannon':3.,'ring':.5,'verdict':30}.get(k,1.5)
            tower['next']=t+interval
            if k=='cannon':
                for e in targets:
                    if abs(e['x']-first['x'])<=3:hit(e,40)
            elif k=='ring':
                for e in targets:hit(e,3,True)
            elif k=='hero':
                hit(first,36,True) # 至少Lv3；周期闪电取确定性每4击一次。
                hero_hit+=1
                if hero_hit%4==0:
                    for e in targets[:4]:hit(e,40,True)
            elif k=='verdict':hit(first,600,True)
            else:
                hit(first,40 if k=='double' else 20,k=='frost')
                if k=='frost' and first['kind']!='immune':first['slow']=t+3
        dead=[e for e in enemies if e['hp']<=0]
        for e in dead:
            enemies.remove(e)
            if e['kind']=='spore':
                add('child',e['x']);add('child',e['x'])
            if e['kind']=='mother':
                # 母体三级谱系在S01未用；后续全局S02仅做预算/资源校验。
                raise ValueError('lane model only supports S01 lineage')
        if walls<=0:return {'cleared':False,'wall_broken_sec':round(t,1),'remaining_entities':len(enemies)+len(pending),'damage_received':round(lost,1)}
        if not enemies and not pending:
            return {'cleared':True,'clear_sec':round(t,1),'wall_remaining_hp':round(walls,1),'damage_received':round(lost,1),'spawned_entities_including_children':spawns,'first_contact_sec':first_contact}
    return {'cleared':False,'timeout':420}
LANEA={'giant':1,'green':8,'iron':2,'spore':1}
LANEB={'green':14,'immune':2,'archer':1,'javelin':1}
assert sum(POINTS[k]*n for c in [LANEA,LANEB] for k,n in c.items())==64
rows['s01_final_lanes']={
 'tech_A':lane_sim(LANEA,['double','double','cannon','frost'],hero=True),
 'tech_B':lane_sim(LANEB,['double','cannon','arrow','arrow']),
 'magic_A':lane_sim(LANEA,['ring','ring','verdict','frost'],hero=True),
 'magic_B':lane_sim(LANEB,['arrow']*4+['frost']),
}
rows['portal_cases']=[{'case':name,'route_m':d,'green_response_sec':d/3,'boar_response_sec':d/5.5,'valid':valid} for name,d,valid in [('main',150,True),('remote_mine',150,True),('coast_long_detour',430,False),('wide_vision_no_candidate',0,False)]]
Path(__file__).with_name('combat_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
Path(__file__).with_name('survival_config.json').write_text(json.dumps({'threat_points':POINTS,'stages':STAGES,'s01_clock':[60,140,220,280],'s02_clock':[60,150,240,310],'initial_prepare':120,'rest':90,'normal_interval':40,'small_normal_clock_pause_seconds':20,'same_tick_priority':'concentrated_before_normal','normal_nominal_count_per_stage':{'S01':5,'S02':6},'camp_guard_s01':{'green':4,'archer':1},'camp_reward_modes':{'S01':{'mode':'fixed_crystal','amount':50},'S02':{'mode':'choose_crystal_or_steel','steel_multiplier':2}}},ensure_ascii=False,indent=2),encoding='utf-8')
names={'green':'普','archer':'弓','spore':'孢囊','climber':'攀墙','javelin':'投矛','immune':'破咒','iron':'铁皮','boar':'野猪','mother':'孢巢','giant':'巨怪'}
def wave_md(stages):
    out=['| 阶段 | 小波1 | 小波2 | 小波3 | 大波 |','|---|---|---|---|---|']
    for i,st in enumerate(stages):
        cells=[]
        for c in st:
            b=sum(POINTS[k]*n for k,n in c.items())
            cells.append(str(b)+'点：'+'、'.join(names[k]+'×'+str(n) for k,n in c.items()))
        out.append('| '+str(i+1)+' | '+' | '.join(cells)+' |')
    return '\n'.join(out)
config_doc='''# 生存数值配置（原型基线）

版本 v0.1 · 2026-10-08。第二轮数值基线，尚未真人试玩通过。冒险关卡仍由用户设计，本页不替代冒险第一关。配置机器源：[survival_config.json](../../工作记录/数值迭代-2026-10-08/survival_config.json)，验算：[combat_check.py](../../工作记录/数值迭代-2026-10-08/combat_check.py)。

[返回文档目录](../../游戏设计文档.md) · [出怪系统](出怪系统.md)

## 1. 共同计时与清场

初始准备120秒。每阶段3小波（一般2–4规则的固定样例），普通出怪独立，不计小波。普通每40秒一次，根预算随阶段为1/2/3/4/4/4；最多2门。小波开启的20秒内不再投放普通，该普通时钟顺延而不补发；小波结束后照常普通，没有休整。大波刷出后暂停新普通至自身清场；已有普通不移除。每阶段普通6次仅为资源验算基准，运行实际按时钟日志统计，不写死成额外隐藏波。

小波1门（阶段3后可2），8秒内刷完；大波1–2门，0/8/16/24秒分4批，总预算分摊，不额外加兵；大波开启当刻提示方向，不新增提前预警。首次特殊怪以少量、单种为教学；首次破咒需明显魔免标记。大波自身根谱系、分裂/召唤子代和生成队列全部清零，tick末进入90秒休整，普通/小/大全部停止新刷；经营、建筑、研究、日夜继续，不积累下一轮计时。原有普通怪保留，营地守卫不阻塞休整。最终大波同判定立即胜利，不发无法使用的本局卡/礼物，不等休整。

## 2. 点数与完整构成

普1、弓2、孢囊3、攀墙3、投矛3、破咒4、铁皮4、野猪5、孢巢7、巨怪18。分裂子代不另花预算。该点数是原型威胁估计，仍需试对照阵容，不能宣称精确难度。

''' + wave_md(STAGES)+'''

第一轮曾把54点构成写成64，现已纠正：终64是22普+1巨怪+2破咒+2铁皮+1弓+1孢囊+1投矛，所有24个集中波已由脚本逐项sum断言，不只核总点。

## 3. S01与S02时钟

S01用上表前3阶段；阶段本地小波60/140/220秒、大波280秒。三段大波名义开启6:40/14:40/22:50，清场预测25:35，目标24–30分钟。预测包含分别110/120/165秒行军+分批+战斗，不保证固定时间。

S02用完整6阶段；阶段本地小波60/150/240秒、大波310秒。六段大波名义开启7:10/15:40/24:20/33:45/43:20/53:05，最终清场预测56:35，目标45–60分钟。清场预测110/120/165/175/185/210秒，实际每次清场不同会让后面整体顺移。首2本目标8–14分钟，主路线3本需第4波之前，以便至少第4/5/6波能用；不能拿“预计时间”冒充资源满足证明。短S01只验证2本，不要求满城镇或双3本。

## 4. S01两条终64的条件验算

科技阵容：双箭3、炮2、霜1、箭2、民兵4、英雄，防军38800金币+240钢铁，另兵营/研究院/能源/墙。魔法阵容：环2、裁1、霜2、箭4、民兵4、英雄，防军35800金币+90魔晶，另法师营地100魔晶/能源/兵营/墙。材料产出与建造先后见[第二轮数值A报告](../../工作记录/数值迭代-2026-10-08/第二轮-数值策划A.md)。

终波两口：A巨怪+8普+2铁+孢囊=37；B14普+2破+弓+投矛=27。英雄留A，B不能用全魔输出冒充解魔免。每口一段2000HP/15甲墙、1工人33.33修/秒；塔距墙后前沿1米。科技A双2/炮1/霜1，B双1/炮1/箭2；魔法A环2/裁1/霜1，B箭4/霜1；本模型不计4民兵输出，作为额外调位/应急。门距150m、4批、物理过甲、霜减速、孢囊谱系离散0.1秒；英雄周期4击1闪仅为固定期望近似，不是随机胜率。

结果：科技A109.1秒清/墙1956.7，B101秒清/墙1810；魔法A114.2秒清/墙1960，B107秒清/墙1070。不是无损上界HP/DPS：包含进场移动、分批、攻击冷却、敌人反打墙与真实修复。但没有真实二维碰撞/索敌/侧翼/工人受击/寻路，属于有条件原型通过。弓手9米+塔在墙后1.5米超出箭塔10米，原模型确实超时；需塔前沿≤1米或民兵出门处理后排，部署距离是实质选择。

S01四个教学营地各固定50魔晶（原30–60范围），共200保底满足100升本+90塔，零星掉落作为余量；两个最低30营地只有60，不是100保底。每营地4普+1弓守卫（6点）候选，需带4民兵和英雄实际清理；离城≥300米、相邻≥100米，四营地串联路线至少300+3×100+600=1200米行军约400秒，另清理每营地20–40秒、回家与修补时间，至少8–10分钟外出。不能瞬时领全部奖励。若地图不能支持这个合法路线，应配置校验失败，不暗加资源。

## 5. 合法随机门户与失败处理

合法集合同时满足视野外、同大陆可达、离最近建筑直线120–250米，以及真实可行地面路径120–250米（到目标最近可攻击边缘，不穿墙/海岸）。从全部合法候选中纯随机选，不做方向轮换、不按已选方向补偿。路径范围限制曲折窄路不能藏成143秒的“120米”门。

搜索逐层扩大候选采样密度/搜索网格覆盖到整个合法环带，不能把距离窗缩近、把路径窗扩大或越过视野边界。仍零候选时：不扣预算、不推进小波计数/大波进度、不视为清场；暂停这一关卡的出怪时钟并显示“出怪配置无合法落点”，保存种子/地图/目标/视野调试信息，进入可恢复配置错误状态。经营可继续，不能据此胜利；开发者需修合法布局或配置。不是静默取消预算、随机强刷玩家脸上或奖励玩家铺视野逃课。

例：主城合法150米门，普到达50秒、野猪27.27秒；近城60米远矿周边合法150米门，英雄走60米/3=20秒可回援普通，野猪仅7.27秒余量，需当地守军；远矿离城300米英雄回援100秒赶不上，矿收入必须承担预置驻防/失矿机会成本。海岸直线150实际绕路430米拒绝；广视野覆盖全部环带零候选进入配置错误，不吞64点。大波只有开门当刻方向提示，以上回应不能依赖新加提前预警。

## 6. 原型验收边界

S02实际现金/钢铁/魔晶/能源/繁荣账本仍须与阶段编制核对。仅当前离线预算与S01前沿模型成立；若50分钟收入百万而没有有价值的决策约束，应保留未通过阻断，不能以耗钱无用建筑装饰通过分。所有新价格与规则为本轮原型基线，需两主策独立复核后进入真人试玩，案头分不等于已证明有趣。
'''
docpath=Path(__file__).resolve().parents[2]/'设计文档'/'系统'/'生存数值配置.md'
if '--write-doc' in sys.argv:
    docpath.write_text(config_doc,encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
