"""Keep modified Markdown tables rectangular after adding baseline status cells."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
snapshot = json.loads((HERE / "输入文档快照.json").read_text(encoding="utf-8"))
old = {r["file"].replace("\\", "/"): r["sha256"] for r in snapshot}
fixed = []
for p in (ROOT / "项目文档" / "设计文档").rglob("*.md"):
    rel = p.relative_to(ROOT).as_posix()
    if old.get(rel) == hashlib.sha256(p.read_bytes()).hexdigest().upper():
        continue
    lines = p.read_text(encoding="utf-8-sig").splitlines()
    i, changes = 0, 0
    while i < len(lines):
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        j = i
        while j < len(lines) and lines[j].strip().startswith("|"):
            j += 1
        rows = [re.split(r"(?<!\\)\|", line.strip())[1:-1] for line in lines[i:j]]
        if len(rows) >= 2 and all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in rows[1]):
            width = max(map(len, rows))
            if any(len(row) != width for row in rows):
                for k, row in enumerate(rows):
                    while len(row) < width:
                        row.append("---" if k == 1 else (" 状态 " if k == 0 else " — "))
                    lines[i + k] = "|" + "|".join(row) + "|"
                changes += 1
        i = j
    if changes:
        p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        fixed.append({"file": rel, "tables": changes})
(HERE / "table_normalization.json").write_text(json.dumps(fixed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"files": len(fixed), "tables": sum(r["tables"] for r in fixed)}))
