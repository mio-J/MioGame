"""Round 5 numeric A: starter-resource reachability over 10 ACTUAL generated seeds.

Read-only. Inputs: round5_seed_exports/seed_*.json.gz (made by round5_export_seeds.gd from the
current AlienFrontier generator; candidate walk grid slope tan<=0.6, water<=0.15 m,
8-neighbour, no diagonal corner cutting, same rule as round3_map_audit.py).
Output: round5_multiseed_supply.json only.

Question: does 'iron and coal within 200 m of spawn' (straight line, as the generator
enforces) imply the player can actually walk to them? Counts how many seeds fail, and
what the nearest REACHABLE iron/coal really is. Candidate grid only: not engine navigation,
not foundation placement. Ten seeds are a sample, not a guarantee about all seeds.
"""
import base64
import glob
import gzip
import heapq
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "round5_multiseed_supply.json"
assert OUT.name.startswith("round5_")
NAMES = {0: "iron", 1: "coal", 2: "oil", 3: "offshore"}
DIRS = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz]


def band(d):
    return 1.0 if d < 200 else 1.15 if d < 500 else 1.3 if d < 900 else 1.5


def analyse(path):
    w = json.loads(gzip.open(path, "rt", encoding="utf-8").read())
    n, cell = w["grid_size"], w["cell_m"]
    grid = base64.b64decode(w["walkable_base64"])
    sp = tuple(w["spawn"])

    def center(i):
        return ((i % n + .5) * cell, (i // n + .5) * cell)

    def near(pt, r):
        xx, zz = int(pt[0] / cell), int(pt[1] / cell)
        k = math.ceil(r / cell)
        for z in range(max(0, zz - k), min(n, zz + k + 1)):
            for x in range(max(0, xx - k), min(n, xx + k + 1)):
                i = z * n + x
                if grid[i] and math.dist(center(i), pt) <= r:
                    yield i
    starts = list(near(sp, 8))
    if not starts:
        return {"seed": w["seed"], "error": "spawn not on candidate grid"}
    st = min(starts, key=lambda i: math.dist(center(i), sp))
    dist = [math.inf] * (n * n)
    dist[st] = math.dist(center(st), sp)
    pq = [(dist[st], st)]
    while pq:
        L, i = heapq.heappop(pq)
        if L != dist[i]:
            continue
        x, z = i % n, i // n
        for dx, dz in DIRS:
            nx, nz = x + dx, z + dz
            if not (0 <= nx < n and 0 <= nz < n):
                continue
            j = nz * n + nx
            if not grid[j]:
                continue
            if dx and dz and not (grid[z * n + nx] and grid[nz * n + x]):
                continue
            nl = L + cell * math.hypot(dx, dz)
            if nl < dist[j]:
                dist[j] = nl
                heapq.heappush(pq, (nl, j))
    res = {"seed": w["seed"], "spawn": sp, "world_deposits": len(w["deposits"])}
    deps = []
    for d in w["deposits"]:
        p = (d["x"] + .5, d["z"] + .5)
        ch = [i for i in near(p, min(d["radius"], 12)) if math.isfinite(dist[i])]
        path = min(dist[i] for i in ch) if ch else None
        deps.append({"kind": d["kind"], "straight": math.dist(sp, p), "path": path})
    for k, name in NAMES.items():
        ds = [x for x in deps if x["kind"] == k]
        reach = [x for x in ds if x["path"] is not None]
        res[name] = {
            "total": len(ds), "reachable": len(reach),
            "within_200_straight": sum(x["straight"] <= 200 for x in ds),
            "within_200_straight_and_reachable": sum(x["straight"] <= 200 for x in reach),
            "nearest_reachable_path_m": round(min((x["path"] for x in reach), default=float("nan")), 1) if reach else None,
            "nearest_reachable_straight_m": round(min((x["straight"] for x in reach), default=float("nan")), 1) if reach else None,
            "reachable_with_path_le_250": sum(x["path"] <= 250 for x in reach),
            "reachable_with_path_le_300": sum(x["path"] <= 300 for x in reach),
            "reachable_mean_multiplier": round(sum(band(x["straight"]) for x in reach) / len(reach), 3) if reach else None,
            "reachable_in_x1.5_band": sum(band(x["straight"]) == 1.5 for x in reach),
        }
    res["starter_iron_reachable_ok"] = res["iron"]["within_200_straight_and_reachable"] > 0
    res["starter_coal_reachable_ok"] = res["coal"]["within_200_straight_and_reachable"] > 0
    res["gate_iron_path_le_250"] = (res["iron"]["reachable_with_path_le_250"] or 0) > 0
    res["gate_iron_path_le_300"] = (res["iron"]["reachable_with_path_le_300"] or 0) > 0
    res["gate_coal_path_le_300"] = (res["coal"]["reachable_with_path_le_300"] or 0) > 0
    res["gate_coal_path_le_250"] = (res["coal"]["reachable_with_path_le_250"] or 0) > 0
    res["gate_counts_ge_6_5_2"] = res["iron"]["reachable"] >= 6 and res["coal"]["reachable"] >= 5 and res["oil"]["reachable"] >= 2
    return res


rows = [analyse(p) for p in sorted(glob.glob(str(HERE / "round5_seed_exports" / "seed_*.json.gz")))]
ok = [r for r in rows if "error" not in r]
summary = {
    "seeds": len(rows),
    "starter_iron_within_200_and_reachable": sum(r["starter_iron_reachable_ok"] for r in ok),
    "starter_coal_within_200_and_reachable": sum(r["starter_coal_reachable_ok"] for r in ok),
    "proposed_gate_iron_path_le_250": sum(r["gate_iron_path_le_250"] for r in ok),
    "proposed_gate_coal_path_le_250": sum(r["gate_coal_path_le_250"] for r in ok),
    "proposed_gate_iron_path_le_300": sum(r["gate_iron_path_le_300"] for r in ok),
    "proposed_gate_coal_path_le_300": sum(r["gate_coal_path_le_300"] for r in ok),
    "proposed_gate_counts_ge_6_5_2": sum(r["gate_counts_ge_6_5_2"] for r in ok),
    "gates_300_all_three": sum(r["gate_iron_path_le_300"] and r["gate_coal_path_le_300"] and r["gate_counts_ge_6_5_2"] for r in ok),
    "failing_seeds_300_gate": [r["seed"] for r in ok if not (r["gate_iron_path_le_300"] and r["gate_coal_path_le_300"] and r["gate_counts_ge_6_5_2"])],
    "nearest_reachable_iron_path_m_by_seed": {str(r["seed"]): r["iron"]["nearest_reachable_path_m"] for r in ok},
    "mean_multiplier_of_reachable_iron_over_seeds": round(sum(r["iron"]["reachable_mean_multiplier"] or 0 for r in ok) / len(ok), 3),
    "all_three_gates": sum(r["gate_iron_path_le_250"] and r["gate_coal_path_le_250"] and r["gate_counts_ge_6_5_2"] for r in ok),
    "scope": "10 seeds, candidate walk grid, generator as of this run; not engine navigation or foundation test",
}
OUT.write_text(json.dumps({"schema": "round5_multiseed_v1", "summary": summary, "per_seed": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
for r in ok:
    print(r["seed"], "iron r/t", r["iron"]["reachable"], r["iron"]["total"], "near path", r["iron"]["nearest_reachable_path_m"],
          "| coal r/t", r["coal"]["reachable"], r["coal"]["total"], "near path", r["coal"]["nearest_reachable_path_m"],
          "| oil r/t", r["oil"]["reachable"], r["oil"]["total"], "| starter iron/coal ok", r["starter_iron_reachable_ok"], r["starter_coal_reachable_ok"])
