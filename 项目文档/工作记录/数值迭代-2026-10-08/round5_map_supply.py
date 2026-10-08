"""Round 5 numeric A: resource-point supply on the ACTUAL generated seed 20260918.

Read-only. Inputs: round3_map_results.json (actual generator deposits + candidate
walk-grid path lengths), AlienFrontier/scripts/world/resource_types.gd and
resource_generator.gd (parsed by regex). Output: round5_map_supply.json only.

What it answers
  * Expected world totals per resource from the generator's province rules.
  * On the one real seed: counts per kind, per yield band, reachable subset.
  * First-mine reality check versus the finite synthetic map used by round3/4
    economy models (mines at 120/180 m, x1.00).
  * How many reachable iron points one 100 m steel-mill disc can cover.
  * Energy supply that the reachable points could offer (upper bound, no defence cost).
Limits: one seed, candidate grid (slope tan<=0.6, water<=0.15 m), no unit collision,
no foundation test. Not a statement about all seeds, not engine navigation.
"""
import json
import math
import re
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "round5_map_supply.json"
assert OUT.name.startswith("round5_")
CODE = HERE.parents[3] / "AlienFrontier" / "scripts" / "world"

res = json.loads((HERE / "round3_map_results.json").read_text(encoding="utf-8"))
R = res["resources"]
NAMES = {0: "iron", 1: "coal", 2: "oil", 3: "offshore"}
BASE = {"iron": 20.0, "coal": 300.0, "oil": 400.0, "offshore": 800.0}   # design: steel/min or energy supply
CODE_BASE_RATE = {"iron": 1.0, "coal": 1.2, "oil": 1.1, "offshore": 1.6}  # resource_types.gd ECONOMY placeholders


def band(d):
    return 1.0 if d < 200 else 1.15 if d < 500 else 1.3 if d < 900 else 1.5


# --- generator province rules (parsed, not hardcoded) ------------------------
src = (CODE / "resource_types.gd").read_text(encoding="utf-8")
prov = {}
for kind, name in NAMES.items():
    blk = src.split(f"Kind.{ {0:'IRON',1:'COAL',2:'OIL',3:'OIL_OFFSHORE'}[kind] }: {{", 1)[1]
    pc = int(re.search(r'"province_count":\s*(\d+)', blk).group(1))
    lo, hi = map(int, re.search(r'"per_province":\s*\[(\d+),\s*(\d+)\]', blk).groups())
    prov[name] = {"province_count": pc, "per_province": [lo, hi], "expected_points": pc * (lo + hi) / 2}
# code placeholder table must match what we assume
gen_src = (CODE / "resource_generator.gd").read_text(encoding="utf-8")
starter_range = float(re.search(r"const STARTER_RANGE\s*:=\s*([\d.]+)", gen_src).group(1))

per_kind = {}
for k, name in NAMES.items():
    rs = [r for r in R if r["kind"] == k]
    reach = [r for r in rs if r["grid_access_path_m"] is not None]
    bands_all, bands_reach = {}, {}
    for r in rs:
        bands_all[str(band(r["straight_distance_m"]))] = bands_all.get(str(band(r["straight_distance_m"])), 0) + 1
    for r in reach:
        bands_reach[str(band(r["straight_distance_m"]))] = bands_reach.get(str(band(r["straight_distance_m"])), 0) + 1
    paths = sorted(round(r["grid_access_path_m"], 1) for r in reach)
    straight = sorted(round(r["straight_distance_m"], 1) for r in rs)
    per_kind[name] = {
        "world_total": len(rs), "reachable_from_spawn_on_candidate_grid": len(reach),
        "expected_world_total_from_rules": prov[name]["expected_points"],
        "straight_nearest_5": straight[:5], "reachable_path_nearest_5": paths[:5],
        "yield_band_counts_all": bands_all, "yield_band_counts_reachable": bands_reach,
        "reachable_supply_upper_bound_at_actual_multipliers": round(
            sum(BASE[name] * band(r["straight_distance_m"]) for r in reach), 1),
    }

# --- first-mine reality check ---------------------------------------------
iron_reach = sorted([r for r in R if r["kind"] == 0 and r["grid_access_path_m"] is not None],
                    key=lambda r: r["grid_access_path_m"])
coal_reach = sorted([r for r in R if r["kind"] == 1 and r["grid_access_path_m"] is not None],
                    key=lambda r: r["grid_access_path_m"])
WORKER_SPEED = 2.5
first = {
    "design_starter_range_m": starter_range,
    "generated_iron_within_range": sum(1 for r in R if r["kind"] == 0 and r["straight_distance_m"] <= starter_range),
    "generated_iron_within_range_reachable": sum(1 for r in R if r["kind"] == 0 and r["straight_distance_m"] <= starter_range
                                                and r["grid_access_path_m"] is not None),
    "nearest_reachable_iron_straight_m": round(iron_reach[0]["straight_distance_m"], 1),
    "nearest_reachable_iron_path_m": round(iron_reach[0]["grid_access_path_m"], 1),
    "nearest_reachable_iron_multiplier": band(iron_reach[0]["straight_distance_m"]),
    "nearest_coal_path_m": round(coal_reach[0]["grid_access_path_m"], 1),
    "second_coal_path_m": round(coal_reach[1]["grid_access_path_m"], 1),
    "model_first_mine_walk_s_at_120m_x1.25": math.ceil(120 * 1.25 / WORKER_SPEED),
    "real_seed_first_iron_walk_s_one_way": math.ceil(iron_reach[0]["grid_access_path_m"] / WORKER_SPEED),
    "steel_per_min_first_mine_model": 20 * 1.0,
    "steel_per_min_first_mine_real_seed": round(20 * band(iron_reach[0]["straight_distance_m"]), 2),
}

# --- one steel mill (100 m) coverage over reachable iron ------------------------
pts = [(r["x"], r["z"]) for r in iron_reach]
best = {"count": 0, "center": None}
for c in pts:   # centre candidates = each deposit (mill must sit near mines)
    n = sum(1 for p in pts if math.dist(c, p) <= 100)
    if n > best["count"]:
        best = {"count": n, "center": list(c)}
pair_d = sorted(round(math.dist(a, b), 1) for a, b in combinations(pts, 2))
mill = {"reachable_iron_points": len(pts), "max_points_covered_by_one_100m_mill": best["count"],
        "nearest_neighbour_distance_median_m": None, "pairwise_distance_nearest_10": pair_d[:10]}
nn = []
for i, a in enumerate(pts):
    nn.append(min(math.dist(a, b) for j, b in enumerate(pts) if j != i))
nn.sort()
mill["nearest_neighbour_distance_median_m"] = round(nn[len(nn) // 2], 1)
# same statistics for ALL generated iron points (any continent), mill centre free on a 10 m lattice
allp = [(r["x"], r["z"]) for r in R if r["kind"] == 0]
nn_all = sorted(min(math.dist(a, b) for j, b in enumerate(allp) if j != i) for i, a in enumerate(allp))
best_all = 0
xs = [p[0] for p in allp]; zs = [p[1] for p in allp]
for gx in range(int(min(xs)) - 100, int(max(xs)) + 101, 10):
    for gz in range(int(min(zs)) - 100, int(max(zs)) + 101, 10):
        c = sum(1 for p in allp if math.dist((gx, gz), p) <= 100)
        if c > best_all:
            best_all = c
best_reach_free = 0
for gx in range(int(min(p[0] for p in pts)) - 100, int(max(p[0] for p in pts)) + 101, 10):
    for gz in range(int(min(p[1] for p in pts)) - 100, int(max(p[1] for p in pts)) + 101, 10):
        c = sum(1 for p in pts if math.dist((gx, gz), p) <= 100)
        if c > best_reach_free:
            best_reach_free = c
mill["all_iron_points"] = len(allp)
mill["all_iron_nearest_neighbour_median_m"] = round(nn_all[len(nn_all) // 2], 1)
mill["all_iron_max_covered_by_one_100m_mill_free_centre"] = best_all
mill["reachable_iron_max_covered_free_centre"] = best_reach_free
mill["design_doc_claim"] = "地图与资源点5.5: 相邻矿点间距中位数约113m, 100m炼钢厂基本照顾整片矿区"

# --- placeholders in code vs design ----------------------------------------
sync = {
    "code_base_rate_units_per_second_placeholder": CODE_BASE_RATE,
    "design_values": {"iron_steel_per_min": 20, "iron_steel_per_second": round(20 / 60, 4),
                      "coal_energy": 300, "oil_energy": 400, "offshore_energy": 800},
    "ratios_oil_over_coal_code_vs_design": [round(1.1 / 1.2, 3), round(400 / 300, 3)],
    "ratios_offshore_over_coal_code_vs_design": [round(1.6 / 1.2, 3), round(800 / 300, 3)],
    "other_gd_references_to_base_rate": None,
}
import subprocess  # noqa: E402  (only for a read-only grep; falls back to python scan)
count = 0
for p in (HERE.parents[3] / "AlienFrontier").rglob("*.gd"):
    if p.name == "resource_types.gd":
        continue
    try:
        if "base_rate" in p.read_text(encoding="utf-8"):
            count += 1
    except Exception:
        pass
sync["other_gd_references_to_base_rate"] = count

result = {"schema": "round5_map_supply_v1", "seed": res["seed"], "scope": "one actual seed, candidate walk grid, not engine navigation",
          "generator_province_rules": prov, "per_kind": per_kind, "first_mine_reality_check": first,
          "steel_mill_100m_coverage_reachable_iron": mill, "base_rate_sync": sync}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: result[k] for k in ("first_mine_reality_check", "steel_mill_100m_coverage_reachable_iron", "base_rate_sync")}, ensure_ascii=False, indent=1))
for n, v in per_kind.items():
    print(n, v["world_total"], v["reachable_from_spawn_on_candidate_grid"], v["expected_world_total_from_rules"], v["reachable_supply_upper_bound_at_actual_multipliers"])
