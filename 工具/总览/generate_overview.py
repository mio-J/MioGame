"""读取设计文档中的「属性表」，生成一张可对比、可搜索的总览页。

用法：py generate_overview.py
输出：MioGame/设计总览.html（双击用浏览器打开即可）

数据全部来自项目文档，文档改了以后重新运行一次就会更新。
识别规则：表头第一列是「属性」的表格，都当作一个条目（建筑 / 单位 / 敌人）。
一份文档里有多张属性表时（例如双重箭塔与多重箭塔），每张表各自成为一个条目，
条目名取表格上方最近的小标题。
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DOCS = os.path.join(ROOT, "项目文档", "设计文档")
OUT = os.path.join(ROOT, "设计总览.html")

CATEGORIES = [("建筑", "建筑"), ("单位", "单位"), ("敌人", "敌人")]

# 对比表里固定展示的行：(显示名, 匹配属性名的正则)
CANON = [
    ("生命值", r"生命值"),
    ("护甲", r"^护甲"),
    ("攻击力", r"^攻击(力)?$|每次齐射"),
    ("攻击间隔", r"攻击间隔"),
    ("射程", r"射程|攻击距离"),
    ("视野", r"视野"),
    ("移动速度", r"移动速度"),
    ("占地", r"占地"),
    ("建造 / 招募时间", r"建造时间|招募时间"),
    ("成本", r"^成本|生产价格|招募成本|^价格|^建造$"),
    ("维持费", r"维持费"),
    ("能源占用", r"能源占用"),
    ("人口", r"人口占用|提供人口"),
]


def clean(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"!\[\[.*?\]\]", "", s)
    return s.strip()


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [clean(c) for c in line.split("|")]


def status_of(text, heading):
    t = text or ""
    if "已确定" in t and "提案" in t:
        return "mixed"
    if "已确定" in t:
        return "confirmed"
    if "待" in t and "提案" not in t:
        return "tbd"
    if "提案" in t:
        return "proposal"
    if "提案" in heading:
        return "proposal"
    return "proposal" if t else "unknown"


def entry_name(heading, title):
    """同一份文档有多张属性表时，用表格上方的小标题给条目命名。"""
    h = re.sub(r"^#+\s*", "", heading)
    h = re.sub(r"^[\d.]+\s*", "", h)
    m = re.match(r"^([^（(]*)[（(]([^）)]*)[）)]", h)
    base, paren = (m.group(1).strip(), m.group(2)) if m else (h.strip(), "")
    if base in ("属性表", "属性"):
        return "%s（%s）" % (title, paren) if paren else title
    base = re.sub(r"(数值|属性表?)$", "", base).strip()
    return base or title


def parse_doc(path, category):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    title = next((clean(l[2:]) for l in lines if l.startswith("# ")), os.path.basename(path))
    if title.endswith("设计") and len(title) > 2:
        title = title[:-2]  # 「主城设计」显示为「主城」
    meta, tables = {}, []
    heading, i = "", 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line
        if line.strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [split_row(l) for l in block]
            header = rows[0]
            body = [r for r in rows[1:] if not re.match(r"^[-: ]+$", "".join(r))]
            if header and header[0] == "文档属性":
                for r in body:
                    if len(r) >= 2:
                        meta[r[0]] = r[1]
            elif header and header[0] == "属性" and len(header) >= 2 and header[1] in ("当前设定", "提案值"):
                tables.append((heading, header, body))
            continue
        i += 1

    doc_id = next((v for k, v in meta.items() if k.endswith("编号")), "")
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    entries = []
    for heading, header, body in tables:
        status_col = header.index("状态") if "状态" in header else None
        name = title if len(tables) == 1 else entry_name(heading, title)
        rows = []
        for r in body:
            if len(r) < 2:
                continue
            note = r[status_col] if status_col is not None and status_col < len(r) else ""
            if status_col is None and len(r) > 2:
                note = r[2]
            st = status_of(note if status_col is not None else "", heading)
            rows.append({"name": r[0], "value": r[1], "note": note, "status": st})
        canon = {}
        used = set()
        for label, pat in CANON:
            for idx, row in enumerate(rows):
                if idx in used:
                    continue
                if re.search(pat, row["name"]):
                    canon[label] = row
                    used.add(idx)
                    break
        others = [row for idx, row in enumerate(rows) if idx not in used]
        entries.append({
            "name": name,
            "category": category,
            "id": doc_id,
            "version": meta.get("版本", ""),
            "updated": meta.get("更新日期", ""),
            "docStatus": meta.get("状态", ""),
            "path": rel,
            "canon": canon,
            "others": others,
        })
    return entries


def build():
    """现读一遍文档，返回 (页面 HTML, 条目列表)。服务器每次刷新都会调用它。"""
    data = []
    for folder, category in CATEGORIES:
        for path in sorted(glob.glob(os.path.join(DOCS, folder, "*.md"))):
            data.extend(parse_doc(path, category))
    data.sort(key=lambda e: (e["category"], e["id"], e["name"]))

    payload = {"cats": [c for _, c in CATEGORIES], "canon": [c[0] for c in CANON], "entries": data}
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        html = f.read()
    return html.replace("__DATA__", json.dumps(payload, ensure_ascii=False)), data


def main():
    html, data = build()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("entries:", len(data))
    for e in data:
        print(" ", e["category"], e["id"], e["name"], len(e["canon"]), "canon rows,", len(e["others"]), "other")
    print("written", OUT)


if __name__ == "__main__":
    main()
