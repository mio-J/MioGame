"""Round 5 numeric A: read-only document consistency audit (stdlib only).

Reads formal documents under 项目文档/设计文档 and writes ONLY round5_doc_audit.json
next to this script. It never edits formal documents and refuses to overwrite any
file that is not a round5_ output.

Checks
  1. Master cost table (成本体系 sections 3-6) vs each building/unit document
     (成本 / 维持费 / 能源占用 rows).
  2. Stale-phrase scan: text that contradicts the current master tables or the
     adopted rules (total-population gates, "price pending", pre-x20 residues ...).
This is a document-consistency check only. It proves nothing about fun or balance.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOCS = ROOT / "项目文档" / "设计文档"
OUT = HERE / "round5_doc_audit.json"
assert OUT.name.startswith("round5_")


def read(p):
    return p.read_text(encoding="utf-8-sig")


def nums(s):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]


def parse_cost(cell):
    """Return dict gold/steel/crystal from a cell like '8000 金币 + 100 钢铁'."""
    cell = cell.replace(",", "")
    d = {"gold": 0.0, "steel": 0.0, "crystal": 0.0}
    m = re.search(r"(\d+(?:\.\d+)?)\s*金币", cell)
    if m:
        d["gold"] = float(m.group(1))
    elif re.fullmatch(r"\s*\*{0,2}\d+\*{0,2}\s*", cell):
        d["gold"] = float(re.search(r"\d+", cell).group(0))
    m = re.search(r"(\d+(?:\.\d+)?)\s*钢铁", cell)
    if m:
        d["steel"] = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*魔晶", cell)
    if m:
        d["crystal"] = float(m.group(1))
    return d


# ---------- 1. master table -------------------------------------------------
master_text = read(DOCS / "系统" / "成本体系.md")
master = {}
section = None
for line in master_text.splitlines():
    if line.startswith("## "):
        section = line
    if not line.startswith("|") or "---" in line:
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if section and (section.startswith("## 4") or section.startswith("## 6")) and len(cells) >= 3:
        name = cells[0]
        if section.startswith("## 4") and len(cells) >= 5:
            # 对象 | 金币 | 材料 | 维护 | 能源
            c = {"gold": nums(cells[1])[0] if nums(cells[1]) else 0.0}
            c.update({k: v for k, v in parse_cost(cells[2]).items() if k != "gold"})
            master[name] = {"cost": c, "upkeep": nums(cells[3])[0] if nums(cells[3]) else 0.0,
                            "energy": nums(cells[4])[0] if nums(cells[4]) else 0.0, "section": 4}
        elif section.startswith("## 6") and len(cells) >= 4:
            # 对象 | 价格(含材料) | 维护 | 能源
            master[name] = {"cost": parse_cost(cells[1]),
                            "upkeep": nums(cells[2])[0] if nums(cells[2]) else 0.0,
                            "energy": nums(cells[3])[0] if nums(cells[3]) else 0.0, "section": 6}

rows = []
files = list((DOCS / "建筑" / "经营建筑").glob("*.md")) + list((DOCS / "建筑" / "军事建筑").glob("*.md"))
for p in sorted(files):
    name = p.stem
    if name not in master:
        continue
    fields = {}
    for m in re.finditer(r"(?m)^\|\s*([^|]+?)\s*\|\s*([^|]+)\|", read(p)):
        fields.setdefault(m.group(1).strip(), m.group(2).strip())
    key = next((k for k in ("成本", "建造成本", "造价") if k in fields), None)
    doc_cost = parse_cost(fields[key]) if key else None
    mc = master[name]["cost"]
    # military docs may state cost in a banner paragraph instead of a table row
    banner = re.search(r"造价\s*\*{0,2}(\d+)\s*金币\*{0,2}", read(p))
    if doc_cost is None and banner:
        doc_cost = {"gold": float(banner.group(1)), "steel": 0.0, "crystal": 0.0}
    up_doc = nums(fields.get("维持费", ""))
    en_doc = nums(fields.get("能源占用", ""))
    row = {"object": name, "master_cost": mc, "doc_cost": doc_cost,
           "cost_ok": None if doc_cost is None else abs(doc_cost["gold"] - mc["gold"]) < 1e-9 and
           (doc_cost["steel"] == mc.get("steel", 0) or doc_cost["gold"] == 0) and
           (doc_cost["crystal"] == mc.get("crystal", 0) or doc_cost["gold"] == 0),
           "master_upkeep": master[name]["upkeep"], "doc_upkeep": up_doc[0] if up_doc else None,
           "master_energy": master[name]["energy"], "doc_energy": en_doc[0] if en_doc else (0.0 if "无" in fields.get("能源占用", "") else None)}
    row["upkeep_ok"] = None if row["doc_upkeep"] is None and "无" not in fields.get("维持费", "") else \
        (row["doc_upkeep"] if row["doc_upkeep"] is not None else 0.0) == row["master_upkeep"]
    row["energy_ok"] = None if row["doc_energy"] is None else row["doc_energy"] == row["master_energy"]
    rows.append(row)

mismatch = [r for r in rows if r["cost_ok"] is False or r["upkeep_ok"] is False or r["energy_ok"] is False]

# ---------- 2. stale-phrase scan -------------------------------------------
STALE = [
    ("研究院/法师营地升本门槛写总人口，已改城镇等级", r"总人口\s*(50|120)", ["建筑/军事建筑/研究院.md"]),
    ("文档称升本要看总人口", r"升本要看总人口", ["建筑/军事建筑/研究院.md"]),
    ("研究价格/时间/本数仍称待定，成本体系5已有", r"研究的价格、时间、本数要求待定", ["建筑/军事建筑/研究院.md", "建筑/军事建筑/法师营地.md"]),
    ("电影院/市政厅仍挂研究院本数，已改城镇等级", r"\[电影院\]\([^)]*\)、油井|科技 3 本[^|\n]*\|\s*\[市政厅\]|\| 科技 3 本 \| \[市政厅\]", ["建筑/军事建筑/研究院.md"]),
    ("3本塔仍写待设计占位（机枪塔/雷霆塔）", r"机枪塔等|雷霆塔等", ["建筑/军事建筑/研究院.md", "建筑/军事建筑/法师营地.md"]),
    ("价格仍写待写入成本体系（主表已收录）", r"待写入\[成本体系\]", ["建筑/经营建筑"]),
    ("状态栏仍写价格待定（主表已有价格）", r"价格待定", ["建筑/经营建筑", "系统/能源体系.md"]),
    ("能源体系仍写具体价格待定", r"具体价格待定", ["系统/能源体系.md"]),
    ("能源体系遗留放大10倍待确认", r"同比例放大 10 倍，待确认", ["系统/能源体系.md"]),
    ("能源建筑属性仍列待设计，但建筑文档已有", r"\|\s*能源建筑属性\s*\|\s*生命值", ["系统/能源体系.md"]),
    ("科技系统仍称法师营地/研究院生命值等待设计", r"\|\s*法师营地、研究院\s*\|\s*生命值", ["系统/科技系统.md"]),
    ("箭塔Lv2是否需2本仍写待定，科技系统6已定", r"箭塔 Lv2 是否需要 2 本待定|箭塔 Lv2（弩塔）是否需要", ["系统/科技系统.md", "建筑/军事建筑/研究院.md"]),
    ("核心循环3.1仍写箭塔Lv2价格待定", r"价格待定，预计消耗钢铁", ["核心玩法循环.md"]),
    ("核心循环6仍列维持费金额待设计（5.2已定）", r"\|\s*维持费\s*\|\s*各单位与建筑的具体金额", ["核心玩法循环.md"]),
    ("开拓者人口占用数量仍写待定（核心循环4已定1人）", r"已确定；数量待定", ["单位/开拓者.md"]),
    ("开拓者建造速度仍写待定", r"\|\s*建造速度\s*\|\s*待定", ["单位/开拓者.md"]),
    ("炼金坊仍用旧采矿场每分钟10钢铁作对照", r"采矿场（每分钟 10）", ["建筑/经营建筑/炼金坊.md"]),
    ("炼金坊仍用旧中期净收入7000/分钟", r"中期净收入（约 7000", ["建筑/经营建筑/炼金坊.md"]),
    ("城镇经营残留乱码句：不能仅由人口估算 人", r"不能仅由人口估算 人", ["系统/城镇经营.md"]),
    ("城镇6级名称不一致（开拓之都/开拓之城）", r"开拓之城", ["系统/城镇经营.md"]),
    ("城镇经营商店价格仍写待定/逐座递增而无数字（主表+400）", r"具体价格待定", ["系统/城镇经营.md"]),
    ("建造与修理出现两个4.5节编号", r"(?m)^### 4\.5 ", ["系统/建造与修理.md"]),
    ("地图文档矿点数量/采矿速度仍列待设计", r"\|\s*矿点数量\s*\|\s*世界里一共有多少个", ["系统/地图与资源点.md"]),
    ("采矿场仍称矿点数量/一矿一座待定", r"一个矿点是否只能建一座采矿场", ["建筑/经营建筑/采矿场.md"]),
    ("采矿场钢铁用途仍写箭塔Lv2待定", r"箭塔升级为 Lv2（弩塔）、铁箭头研究 \| 待定", ["建筑/经营建筑/采矿场.md"]),
    ("星象殿升本价格/时间/前置仍待定", r"升本花费 \| 价格、时间、前置条件 \| 待定", ["建筑/军事建筑/星象殿.md"]),
]
stale_hits = []
for label, pat, targets in STALE:
    rx = re.compile(pat)
    for t in targets:
        base = DOCS / t
        paths = [base] if base.is_file() else sorted(base.glob("*.md"))
        for p in paths:
            for i, line in enumerate(read(p).splitlines(), 1):
                if rx.search(line):
                    stale_hits.append({"issue": label, "file": str(p.relative_to(ROOT)).replace("\\", "/"),
                                       "line": i, "text": line.strip()[:140]})

# 建造与修理 duplicate 4.5: count rather than flag every match
dup = [h for h in stale_hits if h["issue"].startswith("建造与修理出现两个")]
if len(dup) < 2:
    stale_hits = [h for h in stale_hits if not h["issue"].startswith("建造与修理出现两个")]

result = {
    "schema": "round5_doc_audit_v1",
    "scope": "document text only; no gameplay/balance claim",
    "master_rows_parsed": len(master),
    "objects_compared": len(rows),
    "numeric_mismatches": mismatch,
    "compared_rows": rows,
    "not_fully_checked": [r["object"] for r in rows if None in (r["cost_ok"], r["upkeep_ok"], r["energy_ok"])],
    "stale_phrase_hits": stale_hits,
    "stale_hit_count": len(stale_hits),
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"parsed": len(master), "compared": len(rows), "numeric_mismatches": len(mismatch),
                  "stale_hits": len(stale_hits)}, ensure_ascii=False))
for r in mismatch:
    print("MISMATCH", json.dumps(r, ensure_ascii=False))
