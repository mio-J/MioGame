"""把文档里的 〔标签名〕 变成超链接，并重新生成《标签》里每个标签的索引。

为什么不用 # 号：Obsidian 会把 #xxx 当成它自己的标签，点开是全库搜索，
而不是跳到这个标签的定义。所以标签用 〔〕 括起来，再做成指向《标签》的普通链接。

用法（在 MioGame 目录下）：
    py 工具/标签/link_tags.py                 处理《标签》《随机增益》
    py 工具/标签/link_tags.py 某文档.md ...   另外再处理这些文档

它做四件事：
  1. 词表：读《标签》第 3 节的「#### 标签名」标题，以及运行时状态表里的状态标签。
  2. 数据：读《标签》第 4 节每个对象的标签，加上「自动带上」的总称标签。
  3. 索引：在第 3 节每个标签下面重写「带这个标签的对象」「用到它的增益」两行。
  4. 超链接：把文档里所有 〔标签名〕 改成 [〔标签名〕](.../标签.md#标签名)。
     旧写法 #标签名 也会被自动改成新写法；已经是链接的会先还原再重新生成，所以可以反复运行。

写错的标签名（词表里没有的）会被报出来，这就是「定义好的标签」的校验。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYS_DIR = os.path.join(ROOT, "项目文档", "设计文档", "系统")
TAG_DOC = os.path.join(SYS_DIR, "标签.md")
BUFF_DOC = os.path.join(SYS_DIR, "随机增益.md")

GEN_PREFIXES = ("**包含：**", "**带这个标签的对象：**", "**用到它的增益：**")
STATE_HEADING = "运行时状态"
IGNORE_UNKNOWN = {"标签名", "……"}  # 文档里举例用的占位词


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def unlink(text):
    """把 [〔名〕](...) 和旧的 [#名](...) 还原成 〔名〕。"""
    text = re.sub(r"\[〔([^〕]+)〕\]\([^)]*标签\.md#[^)]*\)", r"〔\1〕", text)
    return re.sub(r"\[#([^\]\s]+)\]\([^)]*标签\.md#[^)]*\)", r"〔\1〕", text)


def migrate_hash(text, names):
    """旧写法 #标签名 -> 〔标签名〕。只改词表里有的名字。"""
    if not names:
        return text
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.sub(r"(?<![A-Za-z0-9_./\\\[\]\-#])#(" + alt + ")", r"〔\1〕", text)


def parse_vocab(text):
    """返回 {标签名: 锚点}，以及标签标题顺序。"""
    vocab = {}
    order = []
    section = None
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line
        m = re.match(r"^#### (.+)$", line)
        if m and section and section.startswith("## 3."):
            vocab[m.group(1).strip()] = m.group(1).strip()
            order.append(m.group(1).strip())
    in_state = False
    for line in text.split("\n"):
        if line.startswith("### "):
            in_state = line.strip() == "### " + STATE_HEADING
            continue
        if in_state and line.startswith("|"):
            first = line.split("|")[1]
            for name in re.findall(r"〔([^〕]+)〕|#([^\s、，,|]+)", first):
                n = name[0] or name[1]
                vocab[n] = STATE_HEADING
    return vocab, order


def tag_regex(names):
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(r"〔(" + alt + r")〕")


def parse_implied(text, vocab):
    implied = {}
    in_sec = False
    rx = tag_regex(vocab)
    for line in text.split("\n"):
        if line.startswith("### "):
            in_sec = "自动带上的标签" in line
            continue
        if in_sec and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or not cells[0].startswith("〔"):
                continue
            kids = [m.group(1) for m in rx.finditer(cells[0])]
            parents = [m.group(1) for m in rx.finditer(cells[1])]
            for k in kids:
                implied.setdefault(k, []).extend(parents)
    return implied


def parse_objects(text, vocab, implied):
    """第 4 节：返回 [(显示用的对象, 直接标签, 含总称的全部标签)]。"""
    rx = tag_regex(vocab)
    objs = []
    errors = []
    in4 = False
    for ln, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            in4 = line.startswith("## 4.")
            continue
        if not in4 or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("对象",) or set(cells[0]) <= set("-: "):
            continue
        m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", cells[0])
        if m:
            disp = "[%s](%s)" % (m.group(1), m.group(2))
        else:
            disp = re.sub(r"（.*?）", "", cells[0]).strip()
        tags = [mm.group(1) for mm in rx.finditer(cells[1])]
        leftover = rx.sub("", cells[1])
        if "〔" in leftover:
            errors.append("标签.md 第 %d 行有未定义的标签：%s" % (ln, cells[1]))
        full = set(tags)
        stack = list(tags)
        while stack:
            t = stack.pop()
            for p in implied.get(t, []):
                if p not in full:
                    full.add(p)
                    stack.append(p)
        objs.append((disp, tags, full))
    return objs, errors


def parse_buff_uses(buff_text, vocab):
    """随机增益里每个增益用到了哪些标签：{标签: [(编号, 名称)]}。"""
    rx = tag_regex(vocab)
    uses = {}
    for line in buff_text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        num, name = int(cells[0]), re.sub(r"【.*?】", "", cells[1])
        for mm in rx.finditer(line):
            uses.setdefault(mm.group(1), {})[num] = name
    return {t: sorted(v.items()) for t, v in uses.items()}


def build_index(tag_text, order, objs, uses):
    lines = tag_text.split("\n")
    n = len(lines)
    out = []
    i = 0
    section = None
    while i < n:
        line = lines[i]
        if line.startswith("## "):
            section = line
        m = re.match(r"^#### (.+)$", line)
        out.append(line)
        if m and section and section.startswith("## 3.") and m.group(1).strip() in order:
            name = m.group(1).strip()
            i += 1
            while i < n and lines[i].strip() == "":
                i += 1
            out.append("")
            while i < n and lines[i].strip() != "":
                out.append(lines[i])
                i += 1
            while i < n and (lines[i].strip() == "" or lines[i].startswith(GEN_PREFIXES)):
                i += 1
            holders = [d for d, _t, full in objs if name in full]
            used = uses.get(name, [])
            out.append("")
            mine = [d for d, _t, full in objs if name in full and "敌军" not in full]
            foes = [d for d, _t, full in objs if name in full and "敌军" in full]
            line_mine = "**带这个标签的对象：** " + ("、".join(mine) if mine else "暂无")
            if foes and mine:
                line_mine += "；**敌军（增益不作用于它们，只当条件）：** " + "、".join(foes)
            elif foes:
                line_mine = "**带这个标签的对象：** " + "、".join(foes)
            out.append(line_mine)
            out.append("")
            out.append("**用到它的增益：** " + ("、".join("[%s](随机增益.md)" % nm for _n, nm in used) if used else "暂无"))
            out.append("")
            continue
        i += 1
    return "\n".join(out)


def link_text(text, vocab, path):
    rel = os.path.relpath(TAG_DOC, os.path.dirname(path)).replace("\\", "/")
    rx = tag_regex(vocab)
    text = migrate_hash(unlink(text), vocab)
    return rx.sub(lambda m: "[〔%s〕](%s#%s)" % (m.group(1), rel, vocab[m.group(1)]), text)


def unknown_tags(text, vocab, path):
    bad = []
    for ln, line in enumerate(text.split("\n"), 1):
        if re.match(r"^#{1,6}\s", line):
            continue
        stripped = re.sub(r"`[^`]*`", "", line)
        for m in re.finditer(r"(?<!\[)〔([^〕]+)〕", stripped):
            tok = m.group(1)
            if tok not in vocab and tok not in IGNORE_UNKNOWN:
                bad.append("%s 第 %d 行：〔%s〕" % (os.path.basename(path), ln, tok))
        # 还残留旧写法 #中文 的（没被识别成标签）
        for m in re.finditer(r"(?<![A-Za-z0-9_./\\\[\]\-#])#([一-鿿]\S*)", stripped):
            bad.append("%s 第 %d 行有 # 开头的词（Obsidian 会当成它自己的标签）：#%s" % (os.path.basename(path), ln, m.group(1)))
    return bad


def main():
    extra = [os.path.abspath(a) for a in sys.argv[1:]]
    raw = unlink(read(TAG_DOC))
    # 先用标题拿到词表，再把旧写法迁移成新写法
    vocab, order = parse_vocab(raw)
    tag_text = migrate_hash(raw, vocab)
    implied = parse_implied(tag_text, vocab)
    objs, errors = parse_objects(tag_text, vocab, implied)
    buff_text = migrate_hash(unlink(read(BUFF_DOC)), vocab) if os.path.exists(BUFF_DOC) else ""
    uses = parse_buff_uses(buff_text, vocab)

    tag_text = build_index(tag_text, order, objs, uses)
    problems = list(errors)
    for path in [TAG_DOC, BUFF_DOC] + extra:
        if not os.path.exists(path):
            continue
        text = tag_text if path == TAG_DOC else read(path)
        new = link_text(text, vocab, path)
        problems += unknown_tags(new, vocab, path)
        write(path, new)

    used_tags = set()
    for _d, _t, full in objs:
        used_tags |= full
    unused = [t for t in order if t not in used_tags and t not in uses]
    print("词表 %d 个标签，%d 个对象，%d 个标签被增益使用" % (len(vocab), len(objs), len(uses)))
    if unused:
        print("没有任何对象或增益用到的标签：", "、".join(unused))
    if problems:
        print("\n需要处理的问题：")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("没有发现写错的标签。")


if __name__ == "__main__":
    main()
