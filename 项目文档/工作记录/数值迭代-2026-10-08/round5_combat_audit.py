"""第五轮 · 数值策划B（战斗与难度）案头复核脚本。

性质声明：以下全部是解析式 / 离散事件算式，输入取自正式文档与 survival_config.json（只读）。
不是游戏实测、不是胜率、不是“已证明有趣”，也不含真实导航 / 二维碰撞 / 随机门户。

安全：
  * 绝不 import / 运行 combat_check.py（它会改写 combat_results.json、survival_config.json，
    加 --write-doc 时还会覆盖正式文档生存数值配置.md）。
  * 只写 round5_combat_audit.json；该文件已存在时拒绝覆盖，除非显式加 --force（仅覆盖本轮自己的输出）。
  * 不修改 项目文档/设计文档/ 下任何文件。

运行：  python -I round5_combat_audit.py
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1] / '设计文档'
OUT = HERE / 'round5_combat_audit.json'

if OUT.exists() and '--force' not in sys.argv:
    sys.exit('round5_combat_audit.json 已存在；为避免覆盖已有结果，未执行。需要重算请加 --force。')

R = {'_meta': {
    'nature': 'desk calculation under stated assumptions; not playtest, not engine, not win-rate',
    'inputs_read_only': ['survival_config.json', '设计文档/**/*.md'],
    'output_only': 'round5_combat_audit.json',
}}


# ---------------------------------------------------------------- 基础公式
def clamp_armor(a):
    return max(a, -15)


def red(a):
    """物理伤害系数 = 30/(30+A)，有效护甲最低 -15。"""
    return 30.0 / (30.0 + clamp_armor(a))


# 敌人数据来自各敌人正文（设计提案值）与 生存数值配置 威胁点
E = {
    'green':   dict(name='普通绿皮', hp=200, armor=0,  dmg=20, itv=1.5, spd=3.0, rng=1.0, pts=1, imm=False),
    'archer':  dict(name='绿皮弓手', hp=100, armor=0,  dmg=15, itv=2.0, spd=3.0, rng=9.0, pts=2, imm=False),
    'spore':   dict(name='孢囊怪',   hp=240, armor=0,  dmg=15, itv=1.5, spd=3.0, rng=1.0, pts=3, imm=False),
    'climber': dict(name='攀墙鬼',   hp=120, armor=0,  dmg=15, itv=1.2, spd=5.0, rng=1.0, pts=3, imm=False),
    'javelin': dict(name='投矛绿皮', hp=150, armor=0,  dmg=30, itv=1.5, spd=3.0, rng=1.0, pts=3, imm=False),
    'immune':  dict(name='破咒小子', hp=300, armor=10, dmg=20, itv=1.5, spd=2.8, rng=1.0, pts=4, imm=True),
    'iron':    dict(name='铁皮绿皮', hp=300, armor=30, dmg=25, itv=1.5, spd=2.4, rng=1.0, pts=4, imm=False),
    'boar':    dict(name='野猪骑手', hp=500, armor=5,  dmg=25, itv=1.5, spd=5.5, rng=1.5, pts=5, imm=False),
    'mother':  dict(name='孢巢母体', hp=360, armor=0,  dmg=18, itv=1.5, spd=3.0, rng=1.0, pts=7, imm=False),
    'giant':   dict(name='巨怪',     hp=2000, armor=5, dmg=80, itv=2.5, spd=1.6, rng=2.0, pts=18, imm=False),
}
CHILD = {  # 分裂子代
    'spore_c': dict(hp=80, armor=0, dmg=10, itv=1.2, spd=3.4),
    'big_c':   dict(hp=150, armor=0, dmg=12, itv=1.3, spd=3.2),
    'small_c': dict(hp=60, armor=0, dmg=10, itv=1.2, spd=3.4),
}
LINEAGE_COUNT = {'spore': 3, 'mother': 7}          # 含全部子代的个体数
LINEAGE_HP = {'spore': 240 + 2 * 80, 'mother': 360 + 2 * 150 + 4 * 60}   # 400 / 900

CFG = json.loads((HERE / 'survival_config.json').read_text(encoding='utf-8'))
PTS = CFG['threat_points']
KEYMAP = {'green': 'green', 'archer': 'archer', 'spore': 'spore', 'climber': 'climber', 'javelin': 'javelin',
          'immune': 'immune', 'iron': 'iron', 'boar': 'boar', 'mother': 'mother', 'giant': 'giant'}
for k, v in E.items():
    assert PTS[k] == v['pts'], (k, PTS[k], v['pts'])

# ---------------------------------------------------------------- 1. 战斗正文数字复算
claims = []


def add_claim(file, where, claimed, computed, note, tol=0.06):
    ok = False
    if isinstance(claimed, (int, float)) and isinstance(computed, (int, float)):
        ok = abs(claimed - computed) <= max(tol * abs(claimed), 1e-9)
    claims.append(dict(file=file, where=where, claimed=claimed, computed=computed,
                       match=bool(ok), note=note))


# 火枪手 40 伤害（火枪手.md 属性表）
M = 40
add_claim('敌人/铁皮绿皮.md', '强度检验·火枪手(30点)每发', 15, round(M * red(30), 2), '火枪手.md 为 40 点：对护甲30实为20/发')
add_claim('敌人/铁皮绿皮.md', '强度检验·火枪手需要发数', 20, math.ceil(300 / (M * red(30))), '300HP/20=15发')
add_claim('敌人/野猪骑手.md', '强度检验·火枪手(30点)每发', 25.7, round(M * red(5), 2), '40×30/35=34.29')
add_claim('敌人/野猪骑手.md', '强度检验·火枪手需要发数', 20, math.ceil(500 / (M * red(5))), '500/34.29=14.6→15发')
add_claim('敌人/破咒小子.md', '强度检验·火枪手每发', 30, round(M * red(10), 2), '40×0.75=30，原文一致')
add_claim('敌人/破咒小子.md', '强度检验·火枪手需要发数', 10, math.ceil(300 / (M * red(10))), '原文一致')
add_claim('敌人/绿皮弓手.md', '火枪手消灭一只弓手命中数', 3, math.ceil(100 / M), '原文一致')
# 刺客额外伤害对护甲
add_claim('敌人/破咒小子.md', '圣堂刺客对300血首击额外伤害', 60, round(0.2 * 300 * red(10), 2),
          '战斗与护甲规则/刺客基线：额外部分整体过护甲，破咒甲10→45；铁皮甲30→30')
# 凝霜塔 vs 箭塔价差
add_claim('建筑/军事建筑/凝霜塔.md', '设计意图·价格高出箭塔', 800, 3600 - 2400, '成本主表3600−2400=1200')
# 核弹对破咒
def nuke_raw(d):  # 中心1000，15m处300 线性
    return 1000 - (1000 - 300) * d / 15.0
d_kill = None
for i in range(0, 1500):
    d = i / 100.0
    if nuke_raw(d) * red(10) >= 300:
        d_kill = d
    else:
        break
add_claim('建筑/军事建筑/核弹发射井.md', '强度检验·破咒被消灭半径(m)', 11, round(d_kill, 2),
          '需原始伤害≥400：1000−46.67d≥400→d≤12.86m')
d_iron = max(i / 100 for i in range(0, 1500) if nuke_raw(i / 100) * red(30) >= 300)
claims.append(dict(file='建筑/军事建筑/核弹发射井.md', where='(新增)铁皮被消灭半径', claimed=None,
                   computed=round(d_iron, 2), match=None, note='铁皮甲30需原始≥600→d≤8.57m；巨怪最大857<2000不死'))
# 曙光清绿皮时间：6秒升温，0.5秒一跳，0-40%白20、40-80%橙30、80-100%红40
def laser_kill_time(hp, first_tick_at_zero=False):
    t = 0.0 if first_tick_at_zero else 0.5
    dealt = 0.0
    while t <= 14:
        heat = min(t / 6.0, 1.0)
        dmg = 20 if heat < 0.4 else (30 if heat < 0.8 else 40)
        dealt += dmg
        if dealt >= hp:
            return t
        t += 0.5
    return None
add_claim('建筑/军事建筑/曙光.md', '强度检验·消灭激光上的普通绿皮(秒)', 3.5, laser_kill_time(200), '0.5秒一跳，需到4.0秒；若首跳t=0也是4.0',
          tol=0.05)
# 孢囊怪金币合计
low1, high1 = 100 + 2 * 60, 160 + 2 * 100
low2, high2 = 160 + 2 * 80 + 4 * 40, 240 + 2 * 120 + 4 * 80
claims.append(dict(file='敌人/孢囊怪.md', where='金币合计·一阶', claimed='240–360', computed=f'{low1}–{high1}',
                   match=False, note='低端应为220'))
claims.append(dict(file='敌人/孢囊怪.md', where='金币合计·二阶', claimed='480–680', computed=f'{low2}–{high2}',
                   match=False, note='高端应为800'))
# 投矛近战
claims.append(dict(file='敌人/投矛绿皮.md', where='强度检验·转近战后', claimed='15点，弱于普通绿皮(20)',
                   computed='属性表近战30/次(1.5s)', match=False, note='同文档属性表写30，高于普通绿皮20'))
# 修理公式
for nm, hp, build in [('城墙', 2000, 30), ('箭塔', 300, 20), ('兵营', 200, 30), ('法师营地3本', 700, 60), ('曙光', 800, 45)]:
    f35 = max(build, hp / 35.0)
    f3333 = max(build, hp / 33.3333333)
    claims.append(dict(file='系统/建造与修理.md', where=f'4.3 满修时间公式 max(建造时间,HP/35)·{nm}',
                       claimed=60 if nm == '城墙' else None, computed=round(f35, 2),
                       match=(abs(f35 - 60) < 1e-6) if nm == '城墙' else None,
                       note=f'若除数改为33.33则={round(f3333, 2)}；城墙/主城都以33.33HP/s(60s)进入全部第三/四轮验算'))
claims.append(dict(file='系统/建造与修理.md', where='4.3/4.4 主城满修时间', claimed=120,
                   computed=round(2000 / 35.0, 2), match=False, note='公式给57.14；主城120秒是显式例外，应写成例外'))
R['claims_recheck'] = claims


# ---------------------------------------------------------------- 2. 箭塔 / 双重 / 多重 对 N 只绿皮（复算正文历史示例）
def tower_vs_greens(n, arrows, tower_hp, tower_armor, dmg=20, interval=1.5, dist=10.0, lock=True):
    """绿皮 200HP 在 t=dist/3 到达并每1.5秒打一次；塔 t=0 起每 interval 一次齐射。同刻塔先于敌。"""
    arrive = dist / 3.0
    hp = [200.0] * n
    t_hp = float(tower_hp)
    hit = 20 * 30.0 / (30.0 + tower_armor)
    events = []
    k = 0
    while True:
        events.append((k * interval, 0))
        if k * interval > 120:
            break
        k += 1
    ek = 0
    while arrive + ek * 1.5 <= 120:
        events.append((arrive + ek * 1.5, 1))
        ek += 1
    events.sort()
    for t, kind in events:
        alive = [i for i, h in enumerate(hp) if h > 0]
        if not alive:
            return dict(result='cleared', clear_sec=round(prev_t, 2), tower_hp_left=round(t_hp, 1))
        if kind == 0:
            if arrows == 1:
                tgt = [alive[0]]
            else:
                tgt = alive[:arrows]
                while len(tgt) < arrows:
                    tgt.append(alive[0])
            for i in tgt:
                hp[i] -= dmg
        else:
            t_hp -= hit * len(alive)
            if t_hp <= 0:
                return dict(result='tower_destroyed', destroyed_sec=round(t, 2),
                            enemies_alive=len([h for h in hp if h > 0]),
                            enemies_killed=n - len([h for h in hp if h > 0]))
        prev_t = t
    return dict(result='timeout')


tw = {}
for label, arrows, thp, tar in [('箭塔', 1, 300, 3), ('双重箭塔', 2, 400, 5), ('多重箭塔', 4, 500, 8)]:
    tw[label] = {f'vs{n}只绿皮': tower_vs_greens(n, arrows, thp, tar) for n in (1, 2, 3, 4)}
R['tower_vs_greens_resim'] = dict(
    method='塔t=0起每1.5秒齐射；绿皮3.33秒到塔下并每1.5秒攻击；同刻塔先行；锁定最近。',
    doc_claims={
        '箭塔': {'vs1': '剩约170', 'vs2': '约18秒被拆,消灭1只', 'vs3': '被拆'},
        '双重箭塔': {'vs2': '约15秒消灭2只,塔剩约130', 'vs3': '勉强同归于尽', 'vs4': '被拆'},
        '多重箭塔': {'vs2': '约7.5秒,塔剩约410', 'vs3': '约12秒,塔剩约270', 'vs4': '约15秒,塔仅剩约10'},
    }, resim=tw)

# ---------------------------------------------------------------- 3. 速度档位 / 距离约束
def tier(v):
    if v <= 1.8: return '很慢'
    if v <= 2.6: return '慢'
    if v <= 3.4: return '标准'
    if v <= 4.2: return '快'
    return '很快'


speed_claims = [('孢子', 3.4, '快档下沿'), ('破咒小子', 2.8, '标准档下沿'), ('圣堂刺客', 4.2, '快档上沿'),
                ('骑士', 4.0, '快档'), ('巨怪', 1.6, '很慢档'), ('铁皮绿皮', 2.4, '慢档'), ('攀墙鬼', 5.0, '很快档'),
                ('攀墙鬼(翻后)', 2.2, '慢档'), ('野猪骑手', 5.5, '很快档'), ('开拓者', 2.5, '慢档'),
                ('无人机', 6.0, '很快档'), ('运输舰', 4.0, '快档'), ('投矛(近战)', 3.4, '未标')]
R['speed_tiers'] = [dict(unit=n, speed=v, claimed=c, by_standard=tier(v)) for n, v, c in speed_claims]


def nums_m(text):
    return [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*m', text.replace('*', ''))]


def scan_ranges(folder):
    rows = []
    for p in sorted((DOCS / folder).glob('*.md')):
        txt = p.read_text(encoding='utf-8')
        vision = alert = attack = None
        for line in txt.splitlines():
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) < 2:
                continue
            key, val = cells[0].replace('*', ''), cells[1]
            if key == '视野 / 警戒':
                nn = nums_m(val)
                if len(nn) >= 2:
                    vision, alert = nn[0], nn[1]
            elif key == '视野' and vision is None:
                nn = nums_m(val)
                vision = nn[0] if nn else None
            elif key == '警戒距离' and alert is None:
                nn = nums_m(val)
                alert = nn[0] if nn else None
            elif key in ('攻击距离', '射程', '施法距离', '施法/治疗距离') and attack is None:
                nn = nums_m(val)
                attack = max(nn) if nn else None
            elif key == '远程攻击' and attack is None:
                m = re.search(r'射程\s*\*{0,2}(\d+(?:\.\d+)?)\s*m', val)
                attack = float(m.group(1)) if m else None
        issues = []
        if attack is not None and alert is not None and attack > alert:
            issues.append(f'攻击{attack}>警戒{alert}')
        if alert is not None and vision is not None and alert > vision:
            issues.append(f'警戒{alert}>视野{vision}')
        if attack is not None and vision is not None and attack > vision:
            issues.append(f'攻击/施法{attack}>视野{vision}')
        rows.append(dict(doc=f'{folder}/{p.name}', attack=attack, alert=alert, vision=vision, issues=issues))
    return rows


rng_rows = scan_ranges('敌人') + scan_ranges('单位') + scan_ranges('建筑/军事建筑')
R['range_constraint_scan'] = dict(
    rule='SYS-BHV-001 §2：攻击距离 ≤ 警戒距离 ≤ 视野（星象殿/塔无警戒项时只比攻击≤视野）',
    violations=[r for r in rng_rows if r['issues']],
    scanned=len(rng_rows))

# ---------------------------------------------------------------- 4. 成本 / 维持费 / 能源 交叉核对
def parse_cost(s):
    s = s.replace('**', '').replace(' ', '')
    out = {'gold': 0, 'steel': 0, 'crystal': 0}
    for part in re.split(r'\+', s):
        m = re.match(r'(\d+)(金币|钢铁|魔晶)?', part)
        if not m:
            continue
        n = int(m.group(1))
        u = m.group(2) or '金币'
        if u == '金币': out['gold'] += n
        elif u == '钢铁': out['steel'] += n
        elif u == '魔晶': out['crystal'] += n
    return out


cost_main = {}
for p in [DOCS / '系统' / '成本体系.md']:
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.startswith('|'):
            continue
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 4 and re.match(r'^\d', c[1].replace('**', '')) and re.match(r'^\d+$', c[2]) and re.match(r'^[\d总新增，, ]+', c[3]):
            name = c[0]
            try:
                cost_main.setdefault(name, []).append(dict(cost=parse_cost(c[1]), maint=int(c[2]), energy=int(re.match(r'\d+', c[3]).group(0))))
            except Exception:
                pass
cost_issues = []
for folder in ('建筑/军事建筑', '单位'):
    for p in sorted((DOCS / folder).glob('*.md')):
        name = p.stem
        if name not in cost_main:
            continue
        ref = cost_main[name][-1]
        txt = p.read_text(encoding='utf-8')
        m = re.search(r'(?:造价|成本)\s*\*\*(.+?)\*\*；维持费\s*\*\*(\d+)\s*金币/分钟\*\*(?:；能源占用\s*\*\*(\d+)\*\*)?', txt)
        if m:
            got = parse_cost(m.group(1))
            if got != ref['cost'] or int(m.group(2)) != ref['maint'] or (m.group(3) is not None and int(m.group(3)) != ref['energy']):
                cost_issues.append(dict(doc=f'{folder}/{p.name}', where='原型数值基线块', block=m.group(0), main=ref))
        seen_keys = set()          # 每个字段只取第一次出现（多重箭塔等升级后第二张表不比较）
        for line in txt.splitlines():
            if not line.startswith('|'):
                continue
            c = [x.strip().replace('*', '') for x in line.strip().strip('|').split('|')]
            if len(c) < 2:
                continue
            k = c[0]
            if k in seen_keys:
                continue
            if k in ('成本', '招募成本') and re.match(r'^\d', c[1]):
                seen_keys.add(k)
                got = parse_cost(c[1])
                if got != ref['cost']:
                    cost_issues.append(dict(doc=f'{folder}/{p.name}', where=f'属性表 {k}', value=c[1], main=ref['cost']))
            if k == '维持费':
                seen_keys.add(k)
                mm = re.search(r'(\d+)\s*金币', c[1])
                if mm and int(mm.group(1)) != ref['maint']:
                    cost_issues.append(dict(doc=f'{folder}/{p.name}', where='属性表 维持费', value=c[1], main=ref['maint']))
            if k == '能源占用':
                seen_keys.add(k)
                mm = re.match(r'\D*(\d+)', c[1])
                if mm and ref['energy'] != int(mm.group(1)) and folder.startswith('建筑'):
                    cost_issues.append(dict(doc=f'{folder}/{p.name}', where='属性表 能源占用', value=c[1], main=ref['energy']))
R['cost_cross_check'] = dict(main_rows=len(cost_main), issues=cost_issues,
                             note='空列表=对象文档的基线块与属性表同成本体系主表一致（只比较金币/钢铁/魔晶/维持费/能源）')

# ---------------------------------------------------------------- 5. 24 个集中波审计
NAMES = {'普': 'green', '弓': 'archer', '孢囊': 'spore', '攀墙': 'climber', '投矛': 'javelin', '破咒': 'immune',
         '铁皮': 'iron', '野猪': 'boar', '孢巢': 'mother', '巨怪': 'giant'}
doc_cfg = (DOCS / '系统' / '生存数值配置.md').read_text(encoding='utf-8')
doc_waves = {}
for line in doc_cfg.splitlines():
    m = re.match(r'^\|\s*([1-6])\s*\|(.+)\|\s*$', line)
    if not m:
        continue
    cells = [c.strip() for c in m.group(2).split('|')]
    if len(cells) != 4 or '点：' not in cells[0]:
        continue
    st = int(m.group(1))
    waves = []
    for c in cells:
        mm = re.match(r'(\d+)点：(.+)', c)
        comp = {}
        for part in mm.group(2).split('、'):
            nm, cnt = part.split('×')
            comp[NAMES[nm]] = int(cnt)
        waves.append((int(mm.group(1)), comp))
    doc_waves[st] = waves
mismatch = []
wave_rows = []
seen = set()
for si, stage in enumerate(CFG['stages'], start=1):
    for wi, comp in enumerate(stage):
        pts = sum(PTS[k] * n for k, n in comp.items())
        dpts, dcomp = doc_waves[si][wi]
        if pts != dpts or dcomp != comp:
            mismatch.append((si, wi + 1))
        indiv = sum(n * LINEAGE_COUNT.get(k, 1) for k, n in comp.items())
        hp = sum(n * (LINEAGE_HP.get(k, E[k]['hp'])) for k, n in comp.items())
        ehp_phys = 0.0
        for k, n in comp.items():
            if k in ('spore', 'mother'):
                ehp_phys += n * LINEAGE_HP[k]
            else:
                ehp_phys += n * E[k]['hp'] / red(E[k]['armor'])
        imm_hp = comp.get('immune', 0) * 300
        armor_hp = comp.get('iron', 0) * 300
        new = [k for k in comp if k not in seen]
        for k in comp:
            seen.add(k)
        wave_rows.append(dict(
            stage=si, wave=('大波' if wi == 3 else f'小波{wi + 1}'), points=pts, individuals_with_children=indiv,
            total_hp=hp, phys_ehp=round(ehp_phys), immune_hp=imm_hp, immune_hp_share=round(imm_hp / hp, 3),
            heavy_armor_hp_share=round(armor_hp / hp, 3),
            ranged=comp.get('archer', 0) + comp.get('javelin', 0), climbers=comp.get('climber', 0),
            fast=comp.get('boar', 0) + comp.get('climber', 0),
            species=len(comp), new_species=[E[k]['name'] for k in new],
            arrow_tower_seconds=round(sum(n * (math.ceil(LINEAGE_HP.get(k, E[k]['hp']) / (20 * red(E[k]['armor']))) * 1.5)
                                          for k, n in comp.items()), 1)))
R['wave_audit'] = dict(doc_vs_config_mismatch=mismatch, waves=wave_rows)
R['wave_multi_new_species'] = [dict(stage=w['stage'], wave=w['wave'], new=w['new_species'])
                               for w in wave_rows if len(w['new_species']) >= 2]
big_ratio = []
for si, stage in enumerate(CFG['stages'], start=1):
    pts = [sum(PTS[k] * n for k, n in c.items()) for c in stage]
    big_ratio.append(dict(stage=si, small=pts[:3], big=pts[3], big_over_small3=round(pts[3] / pts[2], 2)))
R['budget_curve'] = big_ratio
peak = []
normal_root = [1, 2, 3, 4, 4, 4]
for w in wave_rows:
    peak.append(dict(stage=w['stage'], wave=w['wave'], individuals=w['individuals_with_children'],
                     plus_two_normal_pulses=w['individuals_with_children'] + 2 * normal_root[w['stage'] - 1]))
R['concurrency_upper_bound_per_wave'] = dict(
    method='一波全部个体(含全部分裂子代同时存活的最坏)+其后2次普通出怪根预算(按1点=1只普通取)；不含上一波未清残余',
    max_individuals=max(p['individuals'] for p in peak), max_with_normals=max(p['plus_two_normal_pulses'] for p in peak),
    per_wave=peak)

# 每个敌人的 DPS / EHP / 对墙 对塔 / 箭塔秒每点
rows = []
for k, e in E.items():
    hp = LINEAGE_HP.get(k, e['hp'])
    wall = e['dmg'] * red(15) / e['itv']
    tower = e['dmg'] * red(3) / e['itv']
    shots = math.ceil(hp / (20 * red(e['armor'])))
    rows.append(dict(enemy=e['name'], points=e['pts'], lineage_hp=hp, phys_ehp=round(hp / red(e['armor']) if k not in ('spore', 'mother') else hp),
                     hp_per_point=round(hp / e['pts'], 1), dps_vs_wall15=round(wall, 2), dps_vs_wall_per_point=round(wall / e['pts'], 2),
                     dps_vs_arrowtower=round(tower, 2), arrow_tower_seconds_per_point=round(shots * 1.5 / e['pts'], 2),
                     kill_by_one_arrow_tower_sec=round(shots * 1.5, 1)))
R['enemy_cost_vs_points'] = rows

# 反应窗口：路径120–250m
reaction = []
for k in ('green', 'immune', 'iron', 'climber', 'boar', 'giant', 'archer'):
    e = E[k]
    stop = e['rng'] if k == 'archer' else 0
    lo, hi = (120 - stop) / e['spd'], (250 - stop) / e['spd']
    reaction.append(dict(enemy=e['name'], speed=e['spd'], arrive_min_sec=round(lo, 1), arrive_max_sec=round(hi, 1),
                         hero_cross_54m_sec=18, slack_vs_min_after_2s_reaction=round(lo - 2 - 18, 1)))
R['reaction_windows'] = dict(
    note='开门当刻提示后，敌人沿路径120–250m走到最近建筑的时间；英雄回援跨54m=18秒；假定2秒玩家反应',
    rows=reaction)

# 门户关闭窗口 vs 玩家可达
close_rows = []
for nm, v in [('古塞奇尤/民兵', 3.0), ('骑士', 4.0), ('圣堂刺客', 4.2), ('无人机(不可控,经集结点)', 6.0)]:
    close_rows.append(dict(unit=nm, speed=v, reach_120m_sec=round(120 / v, 1), reach_250m_sec=round(250 / v, 1)))
R['portal_destruction_feasibility'] = dict(
    small_wave_drop_window_sec=8, big_wave_last_batch_sec=24,
    rows=close_rows, note='玩家单位最快4.2m/s需≥28.6s才到最近的120m门，晚于大波末批24秒；门若可摧毁则几乎只剩无人机可触及')

# ---------------------------------------------------------------- 6. 腐蚀叠层时间表
def corrosion_table(base_armor, interval):
    rows_ = []
    a = base_armor
    n = 0
    while True:
        rows_.append(dict(hits=n, armor=clamp_armor(a), phys_mult=round(red(a) / red(base_armor), 2),
                          seconds=round(max(n - 1, 0) * interval, 1) if n else 0))
        if clamp_armor(a) <= -15:
            break
        n += 1
        a -= 4
    return rows_


R['corrosion'] = {
    '普通(0)': corrosion_table(0, 2.0),
    '野猪/巨怪(5)': corrosion_table(5, 2.0),
    '破咒(10,魔免但腐蚀是物理)': corrosion_table(10, 2.0),
    '铁皮(30)': corrosion_table(30, 2.0),
    '铁皮(30)·腐蚀塔2s+腐蚀无人机1.5s合并命中(每0.857s一次,共用同一累计池)': corrosion_table(30, 1.0 / (1 / 2.0 + 1 / 1.5)),
}
R['corrosion_exposure'] = [
    dict(enemy='铁皮绿皮', speed=2.4, seconds_in_12m_range_before_contact=round(11 / 2.4, 1), hits_by_one_corrosion_tower=int(11 / 2.4 / 2) + 1,
         seconds_to_break_one_wall=round(2000 / (25 * red(15) / 1.5), 1)),
    dict(enemy='普通绿皮', speed=3.0, seconds_in_12m_range_before_contact=round(11 / 3.0, 1), hits_by_one_corrosion_tower=int(11 / 3.0 / 2) + 1,
         seconds_to_break_one_wall=round(2000 / (20 * red(15) / 1.5), 1)),
]

# ---------------------------------------------------------------- 7. 战力 / 性价比：塔与单位
UNIT_TAX = 180   # 每名军人失税（成本体系：民兵100维护+180失税）


def dps_options():
    """返回 [(name, req, gold, steel, crystal, energy, maint, tax, fn)]；fn(enemy_key,k)->总HP去除速率"""
    def lin(per_hit, itv, magic=False, targets=lambda k: 1):
        def fn(ek, k):
            e = E[ek]
            if magic and e['imm']:
                return 0.0
            f = 1.0 if magic else red(e['armor'])
            return per_hit * f / itv * targets(k)
        return fn

    def cannon(ek, k):
        e = E[ek]
        return 40 * red(e['armor']) / 3.0 * min(k, 6)

    def steel(ek, k):
        return 16 * 4 * red(E[ek]['armor'])      # 满速

    def verdict(ek, k):
        e = E[ek]
        if e['imm']:
            return 0.0
        return min(LINEAGE_HP.get(ek, e['hp']) / (k if ek in ('spore', 'mother') else 1), 600) / 30.0

    def storm(ek, k):
        e = E[ek]
        if e['imm']:
            return 0.0
        seq = [60 * 0.8 ** i for i in range(5)][:max(1, min(k, 5))]
        return sum(seq) / 2.5

    def laser(ek, k):
        e = E[ek]
        per = 330.0 / 14.0
        return per * (0.5 * red(e['armor']) + (0.0 if e['imm'] else 0.5)) * k

    def assassin(ek, k, cap=80, base=20):
        e = E[ek]
        hp = e['hp']
        n = 0
        h = float(hp)
        while h > 0 and n < 200:
            extra = min(0.2 * h, cap) if cap else 0.2 * h
            h -= (base + extra) * red(e['armor'])
            n += 1
        return hp / (n * 1.25)

    def mage(ek, k):
        e = E[ek]
        if e['imm']:
            return 0.0
        return (42 + 0.25 * 100 * min(k, 3)) / 2.0

    def hero(ek, k):
        e = E[ek]
        if e['imm']:
            return 0.0
        return (30 + 0.25 * 40 * min(k, 4)) / 1.5

    return [
        ('箭塔', '基', 2400, 0, 0, 0, 200, 0, lin(20, 1.5)),
        ('箭塔Lv2(升级后合计)', '科2', 5400, 30, 0, 0, 300, 0, lin(32, 1.5)),
        ('双重箭塔', '科2', 4800, 40, 0, 50, 400, 0, lin(40, 1.5)),
        ('多重箭塔', '科3', 8800, 120, 0, 80, 600, 0, lin(80, 1.5)),
        ('凝霜塔', '基', 3600, 0, 0, 0, 260, 0, lin(20, 1.5, magic=True)),
        ('火炮塔', '科2', 5600, 60, 0, 50, 400, 0, cannon),
        ('钢雨(满速)', '科3', 10000, 120, 0, 100, 650, 0, steel),
        ('雷环塔', '魔2', 4800, 0, 30, 50, 400, 0, lin(6, 1.0, magic=True, targets=lambda k: k)),
        ('裁决', '魔2', 4600, 0, 30, 50, 400, 0, verdict),
        ('风暴尖塔', '魔3', 9000, 0, 70, 100, 600, 0, storm),
        ('灵魂熔炉', '魔3', 11000, 0, 100, 120, 700, 0, lin(80, 1.5, magic=True, targets=lambda k: k)),
        ('曙光', '混33', 18000, 180, 160, 300, 1000, 0, laser),
        ('民兵', '基', 1200, 0, 0, 0, 100, UNIT_TAX, lin(15, 1.5)),
        ('火枪手', '基+解锁', 2200, 5, 0, 0, 140, UNIT_TAX, lin(40, 2.5)),
        ('骑士(3本)', '科3', 3000, 12, 0, 0, 160, UNIT_TAX, lin(35, 1.5)),
        ('圣骑士', '混22', 3800, 15, 15, 0, 200, UNIT_TAX, lin(25, 1.5)),
        ('圣堂刺客(上限80)', '魔2+解锁', 3400, 0, 12, 0, 180, UNIT_TAX, lambda ek, k: assassin(ek, k)),
        ('法师(3本)', '魔3', 4200, 0, 15, 0, 220, UNIT_TAX, mage),
        ('古塞奇尤(Lv1)', '英雄', 0, 0, 0, 0, 0, 0, hero),
    ]


SCEN = [('1只普通绿皮', 'green', 1), ('8只普通挤在一起', 'green', 8), ('3只铁皮', 'iron', 3), ('3只破咒', 'immune', 3),
        ('1只巨怪', 'giant', 1), ('4只野猪(忽略躲避)', 'boar', 4), ('1只孢巢母体谱系(7体)', 'mother', 7)]
HOLD_MIN = 20
opts = dps_options()
table = []
for (name, req, g, st, cr, en, mt, tax, fn) in opts:
    hold = g + (mt + tax) * HOLD_MIN
    row = dict(option=name, req=req, gold=g, steel=st, crystal=cr, energy=en, maint=mt, tax=tax,
               hold_cost_20min=hold, dps={}, dps_per_1000_hold={})
    for label, ek, k in SCEN:
        d = fn(ek, k)
        row['dps'][label] = round(d, 2)
        row['dps_per_1000_hold'][label] = round(d / hold * 1000, 3) if hold else None
    table.append(row)
R['dps_efficiency'] = dict(
    assumptions=[
        '总HP去除速率(DPS)，不计射程/站位/弹道躲避/过量伤害(裁决除外)/建筑血量/占地/能源余量/施工时间',
        '持有成本=一次性金币+(维持费+军人失税180)×20分钟；材料与能源另列，不折算成金币',
        '火炮塔每发命中min(k,6)个目标；雷环/灵魂熔炉/曙光对k个目标全部命中；风暴尖塔最多链5个',
        '古塞奇尤Lv1无成本(英雄)；刺客上限80；钢雨取满速64',
    ],
    hold_minutes=HOLD_MIN, scenarios=[s[0] for s in SCEN], rows=table)

# 各场景在不同科技约束下的 DPS/持有成本 第一名
GROUPS = {
    '仅基础(无解锁)': {'基'},
    '基础+科技2本': {'基', '科2', '基+解锁'},
    '基础+魔法2本': {'基', '魔2', '魔2+解锁'},
    '科技全(含科3)': {'基', '科2', '科3', '基+解锁'},
    '魔法全(含魔3)': {'基', '魔2', '魔3', '魔2+解锁'},
}
winners = {}
for gname, reqs in GROUPS.items():
    winners[gname] = {}
    cand = [r for r in table if r['req'] in reqs and r['option'] != '古塞奇尤(Lv1)']
    for label, ek, k in SCEN:
        ranked = sorted(cand, key=lambda r: -(r['dps_per_1000_hold'][label] or 0))
        winners[gname][label] = [f"{r['option']}={r['dps_per_1000_hold'][label]}" for r in ranked[:3]]
R['dps_efficiency_top3_by_scenario'] = winners

# 钢雨 vs 多重箭塔 / 箭塔Lv2 vs 双重箭塔 对比
def find(n):
    return next(r for r in table if r['option'] == n)


cmp_rows = []
for a, b in [('钢雨(满速)', '多重箭塔'), ('箭塔Lv2(升级后合计)', '双重箭塔'), ('民兵', '箭塔'), ('灵魂熔炉', '雷环塔')]:
    A, B = find(a), find(b)
    cmp_rows.append(dict(a=a, b=b,
                         cost_ratio_hold=round(A['hold_cost_20min'] / B['hold_cost_20min'], 2),
                         dps_ratio={s[0]: round(A['dps'][s[0]] / B['dps'][s[0]], 2) if B['dps'][s[0]] else None for s in SCEN}))
R['pairwise_comparison'] = cmp_rows

# 钢雨预热 / 打击窗口
def steel_cum(t):
    if t <= 3:
        return 16 * (1 * t + 1.5 * t * t / 3.0)   # 速率 1→4 线性：r=1+t, 累积发数=t+t²/2? 修正如下
    return None


def steel_shots(t):
    # 速率 r(s)=1+s (0≤s≤3，3秒内线性到4发/秒)，之后恒4发/秒
    if t <= 3:
        return t + t * t / 2.0
    return 3 + 4.5 + 4 * (t - 3)  # 前3秒共7.5发


R['steel_rain_window'] = {f'{t}s': dict(shots=round(steel_shots(t), 1), dmg_vs_armor0=round(16 * steel_shots(t), 1),
                                      multi_arrow_tower=round(80 / 1.5 * t, 1)) for t in (3, 5, 10, 20, 60)}

# ---------------------------------------------------------------- 8. 近战单挑（离散，无走位，不是胜率）
def duel(unit, enemies, tmax=300.0, dt=0.01):
    """unit: dict(hp,armor,dmg,itv,pct=None(cap),regen_pct=0,hunter=False)
    enemies: list of dict(hp,armor,dmg,itv,ranged=False,children=[...]) 顺序=被攻击顺序；全体同时攻击unit。"""
    u_hp = float(unit['hp'])
    u_max = float(unit['hp'])
    foes = [dict(f, cur=float(f['hp']), nxt=0.0, alive=True) for f in enemies]
    u_next = 0.0
    t = 0.0
    kills = 0
    while t < tmax:
        # unit hit
        if t + 1e-9 >= u_next:
            tgt = next((f for f in foes if f['alive']), None)
            if tgt is None:
                return dict(winner='unit', sec=round(t, 2), unit_hp_left=round(u_hp, 1), kills=kills)
            extra = 0.0
            if unit.get('pct') is not None:
                cap = unit['pct']
                extra = 0.2 * tgt['cur']
                if cap:
                    extra = min(extra, cap)
            dmg = unit['dmg'] + extra
            if unit.get('hunter') and tgt.get('ranged'):
                dmg *= 1.5
            tgt['cur'] -= dmg * red(tgt['armor'])
            u_next += unit['itv']
            if tgt['cur'] <= 0:
                tgt['alive'] = False
                kills += 1
                for ch in tgt.get('children', []):
                    foes.insert(foes.index(tgt) + 1, dict(ch, cur=float(ch['hp']), nxt=t + 0.0, alive=True))
                if not any(f['alive'] for f in foes):
                    return dict(winner='unit', sec=round(t, 2), unit_hp_left=round(u_hp, 1), kills=kills)
        for f in foes:
            if f['alive'] and t + 1e-9 >= f['nxt']:
                u_hp -= f['dmg'] * red(unit['armor'])
                f['nxt'] += f['itv']
        if unit.get('regen_pct'):
            u_hp = min(u_max, u_hp + unit['regen_pct'] * u_max * dt)
        if u_hp <= 0:
            return dict(winner='enemy', sec=round(t, 2), enemy_hp_left=round(sum(max(f['cur'], 0) for f in foes if f['alive']), 1),
                        kills=kills)
        t += dt
    return dict(winner='timeout')


def mk(k, **kw):
    e = E[k]
    d = dict(hp=e['hp'], armor=e['armor'], dmg=e['dmg'], itv=e['itv'], ranged=(k in ('archer',)))
    d.update(kw)
    return d


spore_children = [dict(hp=80, armor=0, dmg=10, itv=1.2), dict(hp=80, armor=0, dmg=10, itv=1.2)]
mother_group = [mk('mother', children=[dict(hp=150, armor=0, dmg=12, itv=1.3, children=[dict(hp=60, armor=0, dmg=10, itv=1.2)] * 2)] * 2)]
foes = {
    '普通绿皮': [mk('green')], '铁皮绿皮': [mk('iron')], '破咒小子': [mk('immune')], '野猪骑手': [mk('boar')],
    '攀墙鬼': [mk('climber')], '孢囊怪(含2孢子)': [mk('spore', children=spore_children)],
    '2普通绿皮': [mk('green'), mk('green')], '3普通绿皮': [mk('green')] * 3, '巨怪': [mk('giant')],
}
units = {
    '民兵(1本)': dict(hp=150, armor=0, dmg=15, itv=1.5),
    '民兵(3本)': dict(hp=210, armor=0, dmg=21, itv=1.5),
    '圣堂刺客(1本,上限80)': dict(hp=150, armor=0, dmg=20, itv=1.25, pct=80),
    '圣堂刺客(1本,无上限)': dict(hp=150, armor=0, dmg=20, itv=1.25, pct=0),
    '圣堂刺客(3本,上限80)': dict(hp=210, armor=0, dmg=28, itv=1.25, pct=80),
    '骑士(3本)': dict(hp=350, armor=5, dmg=35, itv=1.5),
    '圣骑士(1本,含2%/s回血)': dict(hp=320, armor=10, dmg=25, itv=1.5, regen_pct=0.02),
}
dm = {}
for un, ud in units.items():
    dm[un] = {}
    for fn_, fl in foes.items():
        dm[un][fn_] = duel(ud, [dict(f) for f in fl])
R['duel_matrix'] = dict(note='1v1/1vN近战离散对战，双方t=0同时首击，无走位；用于看“谁克谁”，不是胜率', rows=dm)

# 刺客对不同目标的首击/终结
ass = {}
for k in ('green', 'iron', 'immune', 'boar', 'giant', 'mother'):
    e = E[k]
    row = {}
    for cap_label, cap in [('上限80', 80), ('无上限', None), ('上限40', 40)]:
        h = float(e['hp'])
        n = 0
        first = None
        while h > 0 and n < 200:
            extra = 0.2 * h if cap is None else min(0.2 * h, cap)
            d = (20 + extra) * red(e['armor'])
            first = d if first is None else first
            h -= d
            n += 1
        row[cap_label] = dict(first_hit=round(first, 1), hits_to_kill=n, seconds=round((n - 1) * 1.25, 1))
    ass[e['name']] = row
R['assassin_vs_enemy'] = ass

# ---------------------------------------------------------------- 9. 天气/夜间：塔的有效射程
TOWERS_RV = [('箭塔', 10, 12), ('双重/多重箭塔', 10, 12), ('凝霜塔', 10, 12), ('火炮塔', 12, 12), ('钢雨', 12, 12), ('腐蚀塔', 12, 12),
             ('裁决', 12, 12), ('风暴尖塔', 11, 11), ('雷环塔', 6, 10), ('灵魂熔炉', 4, 8), ('曙光', 20, 20), ('哨塔视野', 0, 20)]
VIS = [('晴', 1.0), ('降雨', 0.75), ('雷暴', 0.55), ('沙尘', 0.40), ('浓雾', 0.35)]
weather = []
for nm, rg, vi in TOWERS_RV:
    row = dict(tower=nm, base_range=rg, base_vision=vi)
    for wn, wm in VIS:
        row[f'{wn}(未照明)'] = round(min(rg, vi * wm), 2) if rg else round(vi * wm, 2)
    row['夜间候选×0.75(未照明)'] = round(min(rg, vi * 0.75), 2) if rg else round(vi * 0.75, 2)
    weather.append(row)
R['visibility_vs_range'] = dict(
    note='天气能见度乘数目前只在昼夜系统文档中定义、尚未被视野/射程读取；此处假设“有效射程=min(射程,视野×乘数)”以暴露风险；哨塔灯照明范围内按1.0',
    enemy_ranged={'绿皮弓手': 9, '投矛绿皮': 8}, rows=weather)

# ---------------------------------------------------------------- 10. 营地守卫：规模与奖励的玩具对照
def camp_fight(party, guards, tmax=240.0, dt=0.05):
    """party: list(dict hp,armor,dmg,itv,magic, ranged_rng) ; guards: greens n, archers m
    简化：民兵近战挡在最前，英雄(魔法30/1.5)从后方打；绿皮攻击最近民兵，弓手攻击最近存活友军；英雄不被近战目标直到民兵全灭。"""
    mil = [dict(hp=150.0, nxt=0.0, alive=True) for _ in range(party['militia'])]
    hero = dict(hp=600.0, nxt=0.0, alive=True)
    gs = [dict(hp=200.0, nxt=0.4, kind='g', alive=True) for _ in range(guards['green'])] + \
         [dict(hp=100.0, nxt=0.4, kind='a', alive=True) for _ in range(guards['archer'])]
    t = 0.0
    hero_shots = 0
    while t < tmax:
        living = [g for g in gs if g['alive']]
        if not living:
            return dict(sec=round(t, 1), militia_lost=sum(1 for m in mil if not m['alive']), hero_hp=round(hero['hp'], 1), result='cleared')
        for m in mil:
            if m['alive'] and t >= m['nxt'] and living:
                tgt = next((g for g in gs if g['alive'] and g['kind'] == 'g'), None) or next(g for g in gs if g['alive'])
                tgt['hp'] -= 15
                m['nxt'] += 1.5
                if tgt['hp'] <= 0:
                    tgt['alive'] = False
        if hero['alive'] and t >= hero['nxt']:
            tgts = [g for g in gs if g['alive']]
            if tgts:
                tg = tgts[0]
                tg['hp'] -= 30
                hero_shots += 1
                if hero_shots % 4 == 0:
                    for g in tgts[:4]:
                        g['hp'] -= 40
                for g in tgts:
                    if g['hp'] <= 0:
                        g['alive'] = False
            hero['nxt'] += 1.5
        for g in gs:
            if g['alive'] and t >= g['nxt']:
                dmg, itv = (20, 1.5) if g['kind'] == 'g' else (15, 2.0)
                alive_m = [m for m in mil if m['alive']]
                if alive_m:
                    alive_m[0]['hp'] -= dmg
                    if alive_m[0]['hp'] <= 0:
                        alive_m[0]['alive'] = False
                elif hero['alive']:
                    hero['hp'] -= dmg * red(5)
                    if hero['hp'] <= 0:
                        hero['alive'] = False
                g['nxt'] += itv
        t += dt
        if not hero['alive'] and not any(m['alive'] for m in mil):
            return dict(sec=round(t, 1), militia_lost=party['militia'], hero_hp=0, result='party_wiped')
    return dict(result='timeout')


def camp_fight2(party, guards, tmax=240.0, dt=0.05):
    """扩展玩具：民兵可3本(210HP/21伤)，英雄可Lv5(760HP/42魔法攻击)，可带牧师(每2.5秒治疗30最低血比例友军)。
    其余同 camp_fight：近战敌人先打最前民兵，民兵全灭后打英雄；弓手同。"""
    mh, md = (210.0, 21.0) if party.get('mil3') else (150.0, 15.0)
    hh, hd = (760.0, 42.0) if party.get('hero5') else (600.0, 30.0)
    mil = [dict(hp=mh, mx=mh, nxt=0.0, alive=True) for _ in range(party['militia'])]
    hero = dict(hp=hh, mx=hh, nxt=0.0, alive=True)
    priests = [dict(nxt=2.5) for _ in range(party.get('priests', 0))]
    gs = [dict(hp=200.0, nxt=0.4, kind='g', alive=True) for _ in range(guards['green'])] + \
         [dict(hp=100.0, nxt=0.4, kind='a', alive=True) for _ in range(guards['archer'])]
    t = 0.0
    shots = 0
    while t < tmax:
        living = [g for g in gs if g['alive']]
        if not living:
            lost = sum(1 for m in mil if not m['alive'])
            return dict(sec=round(t, 1), militia_lost=lost, hero_hp=round(hero['hp'], 1), result='cleared', gold_lost=lost * 1200)
        for m in mil:
            if m['alive'] and t >= m['nxt']:
                tgt = next((g for g in gs if g['alive'] and g['kind'] == 'g'), None) or next((g for g in gs if g['alive']), None)
                if tgt:
                    tgt['hp'] -= md
                    if tgt['hp'] <= 0:
                        tgt['alive'] = False
                m['nxt'] += 1.5
        if hero['alive'] and t >= hero['nxt']:
            tgts = [g for g in gs if g['alive']]
            if tgts:
                tgts[0]['hp'] -= hd
                shots += 1
                if shots % 4 == 0:
                    for g in tgts[:4]:
                        g['hp'] -= 40
                for g in tgts:
                    if g['hp'] <= 0:
                        g['alive'] = False
            hero['nxt'] += 1.5
        for pr in priests:
            if t >= pr['nxt']:
                cands = [x for x in mil + [hero] if x['alive'] and x['hp'] < x['mx']]
                if cands:
                    x = min(cands, key=lambda z: z['hp'] / z['mx'])
                    x['hp'] = min(x['mx'], x['hp'] + 30)
                pr['nxt'] += 2.5
        for g in gs:
            if g['alive'] and t >= g['nxt']:
                dmg, itv = (20, 1.5) if g['kind'] == 'g' else (15, 2.0)
                alive_m = [m for m in mil if m['alive']]
                if alive_m:
                    alive_m[0]['hp'] -= dmg
                    if alive_m[0]['hp'] <= 0:
                        alive_m[0]['alive'] = False
                elif hero['alive']:
                    hero['hp'] -= dmg * red(5)
                    if hero['hp'] <= 0:
                        hero['alive'] = False
                g['nxt'] += itv
        t += dt
        if not hero['alive'] and not any(m['alive'] for m in mil):
            return dict(sec=round(t, 1), militia_lost=party['militia'], hero_hp=0, result='party_wiped')
    return dict(result='timeout')


camp_rows = []
PARTIES = {
    'A:4民兵1本+英雄Lv1': dict(militia=4),
    'B:6民兵1本+英雄Lv1': dict(militia=6),
    'C:4民兵3本+英雄Lv5+1牧师': dict(militia=4, mil3=True, hero5=True, priests=1),
    'D:6民兵3本+英雄Lv5+2牧师': dict(militia=6, mil3=True, hero5=True, priests=2),
}
GUARDS = [(6, 4, 1), (7, 5, 1), (8, 6, 1), (9, 7, 1), (10, 8, 1), (12, 10, 1)]
for pname, party in PARTIES.items():
    for pts, g, a in GUARDS:
        assert g + 2 * a == pts
        camp_rows.append(dict(party=pname, guard_points=pts, greens=g, archers=a, **camp_fight2(party, dict(green=g, archer=a))))
R['camp_guard_toy'] = dict(
    note='合成玩具对照：无走位/碰撞/经验成长/营地拆除时间；绿皮先打最前民兵；只看守卫点数与损兵量级，不是营地可达证明，也不是胜率',
    rows=camp_rows,
    reward_reference={'S01固定': 50, '近带(300–700m)C': '30–50', '远带(>700m)C': '50–60', '损1名民兵(金币)': 1200,
                      '宝箱': '300HP/0甲，4民兵每1.5秒共60伤→约7.5秒'})

# ---------------------------------------------------------------- 10b. 2本阶段 箭塔Lv2 / 双重箭塔 / 箭塔 的金币×能源取舍（只比DPS，不含钢铁/空间/维护）
combos = []
for a in range(0, 13):
    for b in range(0, 13):
        for c in range(0, 13):
            gold = 2400 * a + 5400 * b + 4800 * c
            en = 50 * c
            dps = 13.333 * a + 21.333 * b + 26.667 * c
            combos.append((a, b, c, gold, en, dps))
KN = []
for G in (15000, 30000, 60000):
    for Esp in (0, 100, 300):
        feas = [x for x in combos if x[3] <= G and x[4] <= Esp]
        best = max(feas, key=lambda x: (x[5], -x[3]))
        KN.append(dict(gold_budget=G, spare_energy=Esp, arrow=best[0], arrow_lv2=best[1], double_arrow=best[2],
                       gold_used=best[3], dps=round(best[5], 1)))
R['arrow_family_knapsack'] = dict(
    note='只比较 箭塔(2400/0能) / 箭塔Lv2(5400+30钢/0能) / 双重箭塔(4800+40钢/50能) 的单目标DPS；不含钢铁、维护、占地、塔数上限',
    rows=KN)

# ---------------------------------------------------------------- 11. 升级窗口 vs 休整
upgrades = [('箭塔Lv2', 25), ('多重箭塔', 30), ('兵营1→2', 40), ('兵营2→3', 60), ('圣堂1→2', 40), ('圣堂2→3', 60), ('研究院/法师营地建成', 40),
            ('研究院/法师营地2→3', 60), ('火枪手解锁', 30), ('圣骑士解锁', 45), ('刺客解锁', 40), ('法师解锁', 45), ('无人机坞增机', 20)]
R['upgrade_vs_rest90'] = dict(rest_sec=90, rows=[dict(name=n, sec=s, fits_in_rest=s <= 90) for n, s in upgrades],
                              two_60s_sequential=120, note='单项都≤90秒；同一栋两次连续60秒升级=120秒>90')

# ---------------------------------------------------------------- 12. 词表 / 标签缺口
tag_txt = (DOCS / '系统' / '标签.md').read_text(encoding='utf-8')
missing_tags = [n for n in ('曙光', '无人机坞', '传送阵', '星象殿', '魔导护盾器', '风暴尖塔') if n not in tag_txt]
R['tag_gaps'] = dict(not_mentioned_in_标签md=missing_tags)

# ---------------------------------------------------------------- 12a. 战斗与护甲规则 数表复算 / 相邻两波叠加个体数
arm = {}
arm['main_city_hits_table'] = {str(d): math.ceil(2000 / (d * red(20))) for d in (10, 20, 50, 100, 200)}
arm['main_city_hits_doc'] = {'10': 334, '20': 167, '50': 67, '100': 34, '200': 17}
arm['main_city_ehp'] = round(2000 / red(20), 2)
arm['growth_ehp_per_1000hp'] = {str(a): round(1000 / red(a), 2) for a in (0, 10, 20, 30, 50, 70)}
arm['growth_reduction_pct'] = {str(a): round(100 * (1 - red(a)), 1) for a in (0, 10, 20, 30, 50, 70)}
arm['negative_armor_dmg_pct'] = {str(a): round(100 * red(a), 1) for a in (-4, -8, -12, -15)}
arm['all_equal_to_doc'] = (arm['main_city_hits_table'] == arm['main_city_hits_doc'])
R['armor_rule_tables_recheck'] = arm

pairs = []
for si in range(len(CFG['stages'])):
    rows_ = [w for w in wave_rows if w['stage'] == si + 1]
    for a, b in zip(rows_, rows_[1:]):
        pairs.append(dict(stage=si + 1, pair=f"{a['wave']}+{b['wave']}", individuals=a['individuals_with_children'] + b['individuals_with_children']))
R['consecutive_wave_overlap_worst_case'] = dict(
    note='假设上一波完全未清、下一波已全部刷出；不含普通出怪', max=max(p['individuals'] for p in pairs), rows=pairs)

# ---------------------------------------------------------------- 12b. 刺客一条命内对巨怪的输出；火炮/腐蚀弹的躲避
life = {}
for cap_label, cap in [('上限80', 80), ('无上限', None), ('上限40', 40)]:
    h = 2000.0
    total = 0.0
    for t_hit in (0.0, 1.25, 2.5):          # 1本刺客150HP：巨怪t=0与2.5秒各打一次80，刺客在2.5秒同刻死亡
        extra = 0.2 * h if cap is None else min(0.2 * h, cap)
        d = (20 + extra) * red(5)
        h -= d
        total += d
    life[cap_label] = dict(damage_in_life=round(total, 1), giants_equivalent=round(total / 2000.0, 3),
                           assassins_for_one_giant=round(2000.0 / total, 2))
R['assassin_life_vs_giant'] = dict(note='1本刺客(150HP)对1只巨怪：巨怪t=0与2.5s攻击，刺客共出手3次(t=0/1.25/2.5)', rows=life)

dodge = []
for nm, v in [('普通绿皮', 3.0), ('破咒小子', 2.8), ('铁皮绿皮', 2.4), ('巨怪', 1.6), ('野猪骑手', 5.5), ('攀墙鬼(翻前)', 5.0),
              ('攀墙鬼(翻后)', 2.2), ('孢子', 3.4)]:
    dodge.append(dict(enemy=nm, speed=v, cannon_shift_m=round(v * 1.0, 2), cannon_radius=2.5, cannon_target_escapes=v * 1.0 > 2.5,
                      acid_lob_shift_m=round(v * 0.8, 2), acid_radius=2.0, acid_lob_target_escapes=v * 0.8 > 2.0))
R['lobbed_projectile_dodge'] = dict(
    note='落点式弹道(火炮1.0s,半径2.5；腐蚀弹假设0.8s,半径2.0)按发射时位置落地：目标直线匀速移动时是否逃出爆心半径。队列中后续敌人可能落入范围，未计',
    rows=dodge)

# ---------------------------------------------------------------- 13. 候选：能见度只削减塔视野至射程的80%为止
floor_rows = []
for nm, rg, vi in TOWERS_RV:
    if not rg:
        continue
    row = dict(tower=nm, base_range=rg)
    for wn, wm in VIS:
        row[wn] = round(min(rg, max(vi * wm, 0.8 * rg)), 2)
    floor_rows.append(row)
R['visibility_floor_candidate'] = dict(
    rule='候选(设计提案)：建筑视野 = max(基础视野×能见度, 射程×0.8)；灯光/哨塔照明范围内恢复×1',
    enemy_ranged={'绿皮弓手': 9, '投矛绿皮': 8}, rows=floor_rows)

# ---------------------------------------------------------------- 14. 提示频次
R['notification_counts'] = dict(
    s02_big=6, s02_small=18, s02_total_open_events=24,
    avg_gap_between_open_events_min=round(56.6 / 24, 2),
    note='若小波开门当刻也提示，一局约24次提示事件（18小波+6大波）；普通出怪(S02名义6次/阶段×6阶段=36次)不提示')

OUT.write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding='utf-8')
print('written', OUT.name)
