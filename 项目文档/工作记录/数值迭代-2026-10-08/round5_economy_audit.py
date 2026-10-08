"""Round 5 numeric A: economy audit calculations (stdlib only, read-only inputs).

Inputs (never modified): round4_economy_results.json (final candidate
'经济稳守工业延住宅保险'), round5_map_supply.json.
Output: round5_economy_audit.json only. Hard-coded prices below are copied from the
master table 成本体系.md v0.8 and the object documents; round5_doc_audit.py checks
that table against the documents.

NOT a playtest, NOT proof of fun. The round-4 plan is one scripted synthetic route;
numbers drawn from it describe THAT route only.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "round5_economy_audit.json"
assert OUT.name.startswith("round5_")
r4 = json.loads((HERE / "round4_economy_results.json").read_text(encoding="utf-8"))
S = r4["scenarios"]["经济稳守工业延住宅保险"]
snaps = {s["second"]: s for s in S["snapshots"]}
events = S["events"]
out = {"schema": "round5_economy_audit_v1",
       "scope": "desk calculation on one scripted synthetic route; not playtest evidence"}

# ---------------------------------------------------------------- 1 energy
SRC = {  # gold, steel, upkeep/min, supply (before distance multiplier), distance_multiplier_applies
    "coal": (3000, 0, 100, 300, True), "oil": (5000, 40, 200, 400, True),
    "offshore": (10000, 100, 300, 800, True), "solar": (10000, 0, 0, 300, False)}
STEEL_GOLD = 60  # alchemy: 1 steel sells for 60; used only to show steel is minor here
en = {"cost_per_energy_by_horizon_min": {}, "per_site_supply": {}, "upkeep_per_energy_per_min": {}}
for name, (g, st, up, sup, _) in SRC.items():
    en["upkeep_per_energy_per_min"][name] = round(up / sup, 4)
    for H in (20, 30, 50):
        en["cost_per_energy_by_horizon_min"].setdefault(str(H), {})[name] = round((g + up * H) / sup, 2)
# per-E cost equal when: 10000/300 = (3000+100H)/(300m)  -> H = (10000*m - 3000)/100
en["solar_vs_coal_breakeven_minutes_at_multiplier"] = {
    str(m): round((10000 * m - 3000) / 100, 1) for m in (1.0, 1.15, 1.3, 1.5)}
en["oil_vs_coal_breakeven_same_multiplier_note"] = (
    "oil upkeep/E=0.50 vs coal 0.333 vs offshore 0.375: oil is the dearest to run per energy; "
    "its only edge is +33% energy per scarce site and no steel-free alternative if coal sites are taken")
en["oil_upkeep_if_set_to_120_cost_per_E_50min"] = round((5000 + 120 * 50) / 400, 2)
en["coal_cost_per_E_50min"] = round((3000 + 100 * 50) / 300, 2)
# energy as a constraint on the round-4 route
en["round4_route"] = {
    "final_supply": snaps[max(snaps)]["energy_supply"], "final_used": snaps[max(snaps)]["energy_used"],
    "energy_wait_seconds_total": sum(v.get("energy", 0) for v in S["wait_reasons_seconds"].values()),
    "solar_orders": [(e["second"], e["energy_supply"], e["energy_used_reserved"]) for e in events
                     if e["event"] == "order" and e["kind"] == "solar"],
    "note": "supply minus reserved at each solar order = spare energy already present when solar was bought"}
# deluxe both-route demand (copied from 成本体系 energy column); one plausible build, not a requirement
deluxe = {"研究院3本": 400, "法师营地3本": 400, "兵营3本": 50, "圣堂3本": 100, "星象殿": 100, "市政厅": 200, "电影院": 100,
          "炼钢厂x2": 200, "电器行": 50, "炼金坊": 50, "塔灯x8": 160, "双重箭塔x4": 200, "火炮塔x4": 200, "腐蚀塔x3": 150,
          "钢雨x6": 600, "风暴尖塔x2": 200, "灵魂熔炉": 120, "雷环塔x2": 100, "核弹发射井": 200, "曙光": 300,
          "无人机坞": 100, "缚灵塔": 100}
en["deluxe_both_route_demand"] = {"items": deluxe, "total": sum(deluxe.values())}
for m in (1.0, 1.15, 1.3):
    en["deluxe_both_route_demand"][f"coal_sites_needed_at_x{m}"] = math.ceil(sum(deluxe.values()) / (300 * m))
    en["deluxe_both_route_demand"][f"oil_sites_needed_at_x{m}"] = math.ceil(sum(deluxe.values()) / (400 * m))
out["energy"] = en

# ---------------------------------------------------------------- 2 cash binding
times = sorted(snaps)
first_ge = {}
for thr in (10000, 20000, 50000, 100000, 200000):
    first_ge[str(thr)] = next((t for t in times if snaps[t]["gold"] >= thr), None)
ordr = {}
for e in events:
    if e["event"] == "order" and e["id"] not in ordr:
        ordr[e["id"]] = e["second"]
eras = {"0-600": (0, 600), "600-1200": (600, 1200), "1200-1800": (1200, 1800), "1800-end": (1800, 4000)}
bind = {k: {} for k in eras}
for ident, reasons in S["wait_reasons_seconds"].items():
    t = ordr.get(ident)
    if t is None:
        continue
    for era, (a, b) in eras.items():
        if a <= t < b:
            for r, x in reasons.items():
                bind[era][r] = bind[era].get(r, 0) + x
spent = S["total_spent"]
income = spent["gold"] + spent["upkeep_gold"] + snaps[max(snaps)]["gold"] - 3000
cash = {"first_snapshot_second_with_gold_at_least": first_ge,
        "wait_seconds_by_reason_and_order_era": bind,
        "gold_spent_purchases": spent["gold"], "upkeep": spent["upkeep_gold"], "repair": spent["repair_gold"],
        "final_gold": snaps[max(snaps)]["gold"], "lifetime_income_estimate": round(income, 1),
        "unspent_share_of_lifetime_income": round(snaps[max(snaps)]["gold"] / income, 3),
        "largest_single_gold_price_in_route": 16000,
        "gold_snapshots": {str(t): [snaps[t]["gold"], snaps[t]["net_per_minute"]] for t in times if t % 300 == 0 or t == max(times)}}
# idle cash in units of "most expensive single order seen in route (research3 16000)"
cash["balance_over_16000_by_snapshot"] = {str(t): round(snaps[t]["gold"] / 16000, 2) for t in times if t % 600 == 0 or t == max(times)}
out["cash"] = cash

# ---------------------------------------------------------------- 3 workers
by_w = {}
for e in events:
    if e["event"] == "order" and e.get("worker_id"):
        by_w.setdefault(e["worker_id"], []).append((e["second"], e["finish_second"], e["walk_seconds"], e["build_seconds"]))
dur = S["duration_seconds"]
wk = {}
for w, rows in by_w.items():
    busy = sum(f - s for s, f, *_ in rows)
    wk[w] = {"tasks": len(rows), "busy_seconds": busy, "utilization": round(busy / dur, 3)}
out["workers"] = {
    "per_worker_cost_per_min": 60 + 180, "hire_gold": 1000,
    "construction_workers_in_route": len([w for w in wk]),
    "per_worker": wk,
    "total_worker_wait_seconds_in_orders": sum(v.get("worker", 0) for v in S["wait_reasons_seconds"].values()),
    "worker_wait_after_1800_seconds": bind["1800-end"].get("worker", 0),
    "late_worker_cost_vs_net_per_min_at_2400": round(240 / snaps[2400]["net_per_minute"], 4) if 2400 in snaps else None,
    "note": "the plan keeps worker count fixed; a rational player buys one more worker for 1000 gold, so worker wait is a plan artefact, not a design constraint"}

# ---------------------------------------------------------------- 4 commerce / tax boosters
POOL, TAX = 40.0, 180.0


def per_resident(stores_w, boost):
    T = TAX * min(2.0, max(0.7, 1 + boost))
    C = min(POOL, max(0.0, 360 - T))
    sw = sum(stores_w)
    q = sum(stores_w) * min(1.0, C / sw) if sw else 0.0
    return T, q, T + q

shop_w = {"面包房": 12, "杂货铺": 12, "酒馆(日均)": (6 * 6 + 24 * 4) / 10, "铁匠铺": 6, "药水铺": 12, "集市": 12, "旅馆(日均)": (8 * 6 + 16 * 4) / 10}
price = {"面包房": 2000, "杂货铺": 2000, "酒馆(日均)": 3000, "铁匠铺": 3000, "药水铺": 4000, "集市": 5000, "旅馆(日均)": 6000}
N = 40
order = ["面包房", "杂货铺", "酒馆(日均)", "药水铺", "集市", "铁匠铺", "旅馆(日均)"]
seq, prev_tot, ws = [], per_resident([], 0)[2], []
for name in order:
    ws.append(shop_w[name])
    tot = per_resident(ws, 0)[2]
    gain = (tot - prev_tot) * N
    seq.append({"shop": name, "price": price[name], "marginal_gold_per_min_for_40_residents": round(gain, 1),
                "payback_minutes": round(price[name] / gain, 1) if gain > 0 else None,
                "sum_of_client_prices_after": round(sum(ws), 1)})
    prev_tot = tot
boost = {}
for label, cost, up, pct in (("电影院", 8000, 300, 0.30), ("市政厅", 24000, 600, 0.45)):
    boost[label] = {str(n): {"gain_per_min": round(180 * pct * n - up, 1),
                             "payback_min": round(cost / (180 * pct * n - up), 1) if 180 * pct * n > up else None}
                    for n in (30, 60, 100, 150)}
caps = {}
for label, b in (("无加成", 0), ("电影院", .30), ("电影院+市政厅", .75), ("电影院+市政厅+大杂院", .85), ("再加小村落不可同成员", .85)):
    T, q, tot = per_resident([36], b)
    caps[label] = {"tax": round(T, 1), "commerce": round(q, 1), "total_per_resident": round(tot, 1)}
out["commerce"] = {"shop_sequence_for_40_residents": seq, "booster_payback_by_covered_residents": boost,
                   "per_resident_with_three_12_shops_vs_boosters": caps,
                   "note": "pool 40 and shared +100% cap from 城镇经营 5.1.1; tax is >=80% of per-resident income, so shops are economically a 3-kind business; later kinds pay for effects/prosperity/combos"}

# ---------------------------------------------------------------- 5 houses
houses = {"new_house_price_with_n_existing": {str(n): 2000 + 300 * n for n in (0, 5, 10, 15, 20, 30)},
          "upgrade_to_tile_roof": "3000 gold + 80 steel (+10 pop)", "upgrade_to_apartment": "5000 gold (+10 pop)",
          "new_house_cheaper_than_tile_upgrade_for_n_at_most": 3,
          "new_house_dearer_than_apartment_upgrade_for_n_at_or_above": 10,
          "gold_per_new_pop_at_n15": (2000 + 300 * 15) / 10, "payback_min_at_n15": round((2000 + 300 * 15) / 10 / 180, 2)}
out["housing"] = houses

# ---------------------------------------------------------------- 6 cards / quest / hero revive vs income
net = {t: snaps[t]["net_per_minute"] for t in (600, 1200, 1800, 2400) if t in snaps}
card = {}
for label, amount in (("高利贷立即金币", 30000), ("清场奖金封顶", 4000), ("余粮生息封顶(15屋)", 15 * 140), ("英雄复活费", 10000)):
    card[label] = {str(t): round(amount / (n / 60), 1) for t, n in net.items()}
free_pop = 240 - 26
card["丰饶之种(+20/空闲人/分)_每分钟"] = {"at_final_free_pop_214": 20 * free_pop,
                                           "share_of_net_per_min_at_2997": round(20 * free_pop / snaps[2997]["net_per_minute"], 3) if 2997 in snaps else None}
card["unit_note"] = "values are SECONDS of that moment's net income (rows) / gold per minute (丰饶之种)"
out["fixed_gold_rewards_vs_income_seconds"] = card

# ---------------------------------------------------------------- 7 town timeline vs target
tgt = {"2": (3, 5), "3": (8, 14), "4": (16, 24), "5": (25, 35)}
tl = {}
for lv, sec in S["town_level_first_seconds"].items():
    if lv in tgt:
        tl[lv] = {"first_seconds": sec, "minutes": round(sec / 60, 1), "target_minutes": tgt[lv],
                  "inside_target": tgt[lv][0] <= sec / 60 <= tgt[lv][1]}
out["town_level_timeline_vs_doc_target"] = tl
out["prosperity_arithmetic"] = {"people_incl_city": 240, "six_shop_kinds": 48, "legal_combos": 40, "cinema": 10, "sum": 338,
                                "town_hall_would_add": 20, "sum_with_town_hall": 358, "lv6_threshold": 340,
                                "note": "town hall is a Lv5 public building (+20); the 'Lv6 unreachable' statement holds only if it is excluded"}

# ---------------------------------------------------------------- 8 steel mills on the route
out["steel_mills"] = {"mills_built_in_route": S["final_force_counts"].get("mill"), "mines_built": S["final_force_counts"].get("mine"),
                      "extra_mill_marginal_steel_per_min_per_mine_from_base20": {"2nd": 7.5, "3rd": 5.625, "4th": 4.219},
                      "iron_wait_seconds": sum(v.get("iron", 0) for v in S["wait_reasons_seconds"].values()),
                      "extra_mill_cost": "7000 gold + 40 steel + 200/min upkeep + 100 energy"}


# ---------------------------------------------------------------- 9 card value / crystals
ups = [e for e in events if e["event"] == "order" and e["kind"] == "upgrade"]
steel_total = spent["iron"]
night_cov = 60            # assumed covered residents, an assumption not a route fact
night_shop_per_res = (24 + 16) / 2   # tavern 24 + inn 16 at night, only if both exist; average used as optimistic bound
night_avg = night_cov * night_shop_per_res * (4 / 10)   # 4 of 10 minutes are night
cards = {"旧房翻新": {"upgrades_in_route": len(ups), "steel_saved_if_steel_also_-40pct": round(0.4 * 80 * len(ups), 1),
                       "gold_saved_if_gold_only": round(0.4 * 3000 * len(ups), 1),
                       "steel_saved_share_of_route_steel": round(0.4 * 80 * len(ups) / steel_total, 3),
                       "gold_saved_seconds_of_net_at_2400": round(0.4 * 3000 * len(ups) / (snaps[2400]["net_per_minute"] / 60), 1),
                       "ruling_needed": "card text says 费用 -40%; if steel is not discounted the card is worth ~0 in a gold-glut game"},
         "夜市灯火": {"assumed_covered_residents": night_cov, "average_extra_gold_per_min": round(0.3 * night_avg, 1),
                      "share_of_net_at_1200": round(0.3 * night_avg / snaps[1200]["net_per_minute"], 4),
                      "share_of_net_at_2400": round(0.3 * night_avg / snaps[2400]["net_per_minute"], 4),
                      "note": "upper-ish bound (both tavern and inn assumed present); pool cap 40/resident also applies"}}
out["economy_pool_card_value"] = cards
plain_per_stage = [33, 32, 47, 28, 36, 36]   # 普通绿皮 counts inside small+big waves, 生存数值配置 section 2
normal_points = [6 * b for b in (1, 2, 3, 4, 4, 4)]   # 6 normal spawns/stage x root budget, ONE door
out["crystal_from_drops_estimate"] = {
    "plain_in_small_big_waves": sum(plain_per_stage), "expected_crystal_per_plain": 0.3,
    "wave_plain_drops": round(sum(plain_per_stage) * 0.3, 1),
    "normal_spawn_points_one_door": sum(normal_points), "normal_spawn_points_two_doors_upper": 2 * sum(normal_points),
    "normal_spawn_drops_if_all_plain_one_door": round(sum(normal_points) * 0.3, 1),
    "normal_spawn_drops_if_all_plain_two_doors": round(2 * sum(normal_points) * 0.3, 1),
    "total_expected_range": [round(sum(plain_per_stage) * 0.3 + sum(normal_points) * 0.3, 1),
                             round(sum(plain_per_stage) * 0.3 + 2 * sum(normal_points) * 0.3, 1)],
    "magic_route_need_for_two_hubs": 100 + 300,
    "alchemy_cap_over_50min_after_hub_at_10min": "15/day x 4-5 days = 60-75",
    "note": "all kills assumed and every normal-spawn point assumed a plain goblin; real kills/leaks/other types lower it"}


# ---------------------------------------------------------------- 10 opening replay (成本体系 section 8)
def opening(buy_tower_at_first_affordable=True):
    gold = 3000 - 2000            # house H1 paid at t=0
    residents, tower_paid, rows = 0, False, {}
    for t in range(1, 121):
        free = 8 + residents       # city 10 pop - 2 workers + residents of H1
        gold += free * 3 - 2       # 180/min per free pop, 2 workers x 60/min
        if t >= 25 and (t - 25) % 5 == 0 and residents < 10:
            residents += 1
        if buy_tower_at_first_affordable and not tower_paid and gold >= 2400:
            gold -= 2400; tower_paid = True; rows["tower_paid_second"] = t
        if t in (52, 60, 70, 120):
            rows[f"gold_at_{t}"] = round(gold, 1); rows[f"residents_at_{t}"] = residents
    return rows
out["opening_replay_vs_成本体系_section8"] = {
    "tower_first_affordable": opening(True), "no_tower": opening(False),
    "doc_claims": {"tower_paid_second": 52, "balance_at_60": 340, "no_tower_balance_at_60": 2740}}

# ---------------------------------------------------------------- 11 affordability of round-5 proposals
net1800 = snaps[1800]["net_per_minute"]
prop = {}
for label, gold in (("魔力护盾", 3500), ("雷电强化", 3000), ("星象殿1→2", 7000), ("星象殿2→3", 12000), ("法师营地被毁后重建到3本", 24000)):
    prop[label] = {"gold": gold, "seconds_of_net_income_at_1800": round(gold / (net1800 / 60), 1)}
prop["星象殿升本回本单位数(每单位约+20%×均价)"] = {
    "avg_unit_gold_4800to6000": 5400, "value_per_unit_20pct": 1080, "break_even_units_1to2": round(7000 / 1080, 1),
    "兵营1to2_for_reference": round(3000 / (0.2 * 2000), 1), "圣堂1to2_for_reference": round(4000 / (0.2 * 3400), 1)}
prop["油井维持费200→120_每50分钟每座省"] = 80 * 50
out["proposal_affordability"] = prop


# ---------------------------------------------------------------- 12 does the unit soft-cap bite? (desk arithmetic only)
sn = snaps[1800]
free_now = sn["population"] - sn["occupied"]
mil_price, mil_up, tax = 1200, 100, 180
soft = {}
for n in (20, 40, 80):
    n = min(n, free_now)
    soft[str(n)] = {"purchase_gold": n * mil_price, "affordable_from_1800_balance": n * mil_price <= sn["gold"],
                    "net_per_min_after": round(sn["net_per_minute"] - n * (mil_up + tax), 1),
                    "net_drop_share": round(n * (mil_up + tax) / sn["net_per_minute"], 3),
                    "pop_free_after": free_now - n}
out["unit_soft_cap_arithmetic_at_1800"] = {"free_pop": free_now, "net_per_min": sn["net_per_minute"], "gold": sn["gold"],
                                            "militia_only_cases": soft,
                                            "note": "produces no combat claim; shows that extra units are paid by lost tax, so late idle gold is a property of the light-army scripted route, not proof that gold has no use"}

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: out[k] for k in ("cash", "workers", "town_level_timeline_vs_doc_target")}, ensure_ascii=False)[:3000])
print(json.dumps(out["energy"], ensure_ascii=False)[:2500])
print(json.dumps(out["commerce"], ensure_ascii=False)[:3000])
print(json.dumps(out["fixed_gold_rewards_vs_income_seconds"], ensure_ascii=False))
