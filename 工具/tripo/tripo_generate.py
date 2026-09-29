"""用 Tripo 的多视图接口生成 3D 模型。

用法：
    $env:TRIPO_API_KEY = '<你的 key>'      # PowerShell，只在当前窗口有效
    py tripo_generate.py <视图目录> <输出目录>

视图目录里需要 front.png、back.png、right.png（可选 left.png）。
缺少的视角传空对象，由模型自己推断。key 只从环境变量读取，不要写进任何文件。

注意：本脚本的提交部分已经跑通到"积分不足"这一步；轮询和下载部分尚未实测。
"""
import json
import os
import sys
import time

import requests

KEY = os.environ["TRIPO_API_KEY"]
BASE = "https://api.tripo3d.ai/v2/openapi"
H = {"Authorization": "Bearer " + KEY}

views_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)

r = requests.get(BASE + "/user/balance", headers=H, timeout=60)
print("balance", r.text)


def upload(name):
    path = os.path.join(views_dir, name + ".png")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        r = requests.post(BASE + "/upload", headers=H,
                          files={"file": (name + ".png", f, "image/png")}, timeout=120)
    r.raise_for_status()
    return r.json()["data"]["image_token"]


# 顺序固定：正面、左侧、背面、右侧；缺的视角用空对象占位
files = []
for name in ["front", "left", "back", "right"]:
    token = upload(name)
    files.append({"type": "png", "file_token": token} if token else {})

body = {
    "type": "multiview_to_model",
    "files": files,
    "model_version": "v2.5-20250123",
    "texture": True,
    "pbr": True,
    "face_limit": 30000,
}
r = requests.post(BASE + "/task", headers={**H, "Content-Type": "application/json"},
                  data=json.dumps(body), timeout=120)
print("task", r.status_code, r.text[:500])
r.raise_for_status()
task_id = r.json()["data"]["task_id"]
print("task_id", task_id)

while True:
    time.sleep(10)
    r = requests.get(BASE + "/task/" + task_id, headers=H, timeout=60)
    data = r.json()["data"]
    print(data["status"], data.get("progress"))
    if data["status"] in ("success", "failed", "cancelled", "unknown"):
        break

if data["status"] != "success":
    print(json.dumps(data, ensure_ascii=False)[:800])
    sys.exit(1)

output = data["output"]
for key in ("pbr_model", "model", "base_model", "rendered_image"):
    url = output.get(key)
    if not url:
        continue
    ext = ".webp" if key == "rendered_image" else ".glb"
    dest = os.path.join(out_dir, key + ext)
    with open(dest, "wb") as f:
        f.write(requests.get(url, timeout=300).content)
    print("saved", dest)
