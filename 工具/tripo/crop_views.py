"""把合在一张图里的三视图（FRONT / RIGHT / BACK）拆成单独的图。

用法：py crop_views.py <三视图.png> <输出目录>

切分位置是按古塞奇尤 v5 三视图（1536x1024）手工量出来的：
披风会越过三等分线，所以不能简单三等分。换别的三视图时要重新量。
不生成左侧图：角色左右不对称，镜像右侧会与正面、背面矛盾。
"""
import os
import sys

from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

im = Image.open(src).convert("RGB")
bg = im.getpixel((4, 4))

H = 925  # 去掉底部 FRONT / RIGHT / BACK 文字标签
W = 700
boxes = {
    "front": (0, 0, 600, H),
    "right": (600, 0, 905, H),
    "back": (905, 0, 1536, H),
}
for name, box in boxes.items():
    c = im.crop(box)
    canvas = Image.new("RGB", (W, H), bg)
    canvas.paste(c, ((W - c.width) // 2, 0))
    canvas.save(os.path.join(out, name + ".png"))
    print("saved", name)
