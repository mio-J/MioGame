import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
entry = ROOT / "项目文档" / "游戏设计文档.md"
s = entry.read_text(encoding="utf-8-sig")
lines = []
for line in s.splitlines():
    m = re.search(r"\]\((设计文档/[^)#]+\.md)\)", line)
    if m:
        p = entry.parent / m.group(1)
        if p.exists():
            content = p.read_text(encoding="utf-8-sig")
            v = re.search(r"(?m)^\|\s*版本\s*\|\s*([^|]+)\|", content)
            if v:
                line = re.sub(r"\|\s*v\d[\d.]*\s*\|$", "| " + v.group(1).strip() + " |", line)
    lines.append(line)
s = "\n".join(lines) + "\n"
new = "\n".join([
    "| [数值与趣味性总规划](设计文档/系统/数值与趣味性总规划.md) | 数值职责、统一数据入口、双主策评分、采纳规则与趣味性验收 | v0.6 |",
    "| [生存数值配置](设计文档/系统/生存数值配置.md) | S02正常生存、S01内部短测及独立S02-G实验、逐波预算、实际计时边界 | v0.5 |",
])
s = re.sub(r"(?m)^\| \[(?:数值与趣味性总规划|生存数值配置)\].*\n", "", s)
s = s.replace("| [项目总览]", new + "\n| [项目总览]", 1)
entry.write_text(s, encoding="utf-8", newline="\n")
print("Navigation versions synchronized")
