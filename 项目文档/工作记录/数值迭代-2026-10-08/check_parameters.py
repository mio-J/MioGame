import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
params = json.loads((HERE / "combat_parameters.json").read_text(encoding="utf-8"))
master = (ROOT / "项目文档/设计文档/系统/成本体系.md").read_text(encoding="utf-8-sig")
results = []
for category, entries in params.items():
    directory = ROOT / ("项目文档/设计文档/单位" if category == "units" else "项目文档/设计文档/建筑/军事建筑")
    for name, expected in entries.items():
        p = directory / (name + ".md")
        s = p.read_text(encoding="utf-8-sig")
        fields = {}
        for m in re.finditer(r"(?m)^\|\s*([^|]+?)\s*\|\s*([^|]+)\|", s):
            fields.setdefault(m.group(1).strip(), m.group(2).strip())
        key = next((k for k in ("成本", "招募成本", "生产价格", "建造成本") if k in fields), None)
        got = re.findall(r"\d+(?:\.\d+)?", fields.get(key, "")) if key else []
        want = re.findall(r"\d+(?:\.\d+)?", str(expected["cost"]))
        price_ok = got == want
        master_lines = [l for l in master.splitlines() if l.startswith("|") and (f"| {name} |" in l or f"[{name}]" in l)]
        master_ok = any(all(n in l for n in want) for l in master_lines)
        row = {"object": name, "price_ok": price_ok, "master_ok": master_ok, "actual": fields.get(key), "expected": expected["cost"]}
        for attr, field in (("maintenance", "维持费"), ("energy", "能源占用")):
            if attr in expected and field in fields:
                val = re.findall(r"\d+(?:\.\d+)?", fields[field])
                actual = float(val[0]) if val else 0
                row[attr + "_ok"] = actual == expected[attr]
        results.append(row)
(HERE / "parameter_check.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
bad = [r for r in results if any(v is False for k, v in r.items() if k.endswith("_ok"))]
print(json.dumps({"objects": len(results), "mismatches": len(bad)}, ensure_ascii=False))
for r in bad:
    print(json.dumps(r, ensure_ascii=False))
