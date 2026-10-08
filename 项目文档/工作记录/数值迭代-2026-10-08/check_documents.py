"""Check local Markdown references and snapshot changes; preserve all source files."""
import json
import re
import hashlib
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
snapshot = json.loads((HERE / "输入文档快照.json").read_text(encoding="utf-8"))
changed, missing, versions = [], [], {}
for p in (ROOT / "项目文档" / "设计文档").rglob("*.md"):
    s = p.read_text(encoding="utf-8-sig")
    rel = str(p.relative_to(ROOT))
    v = re.search(r"(?m)^\|\s*版本\s*\|\s*([^|]+)\|", s)
    if v:
        versions[p.name] = v.group(1).strip()
    for m in re.finditer(r"\]\(([^)]+)\)", s):
        target = m.group(1).strip().strip("<>")
        if re.match(r"^(https?:|app:|mailto:|codex:|#)", target):
            continue
        target = unquote(target.split("#", 1)[0])
        if target and not (p.parent / target).exists():
            missing.append({"file": rel, "target": target})
for r in snapshot:
    p = ROOT / r["file"]
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest().upper() != r["sha256"]:
        changed.append(r["file"])
report = {"changed_from_round1_input": changed, "missing_local_links": missing, "versions": versions}
(HERE / "document_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed_count": len(changed), "missing_count": len(missing)}, ensure_ascii=False))
for r in missing:
    print(json.dumps(r, ensure_ascii=False))
