"""设计总览的本地动态服务。

用法：py serve.py        （或双击 打开设计总览.bat）
然后浏览器打开 http://localhost:8765

每次刷新页面都会重新读取项目文档；页面开着的时候，只要文档有改动，
几秒内会自动刷新，不需要手动重新生成。
只监听本机 127.0.0.1，别的电脑访问不到。
"""
import glob
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_overview import DOCS, build  # noqa: E402

PORT = 8765

POLL = """
<script>
(function () {
  let last = null;
  async function tick() {
    try {
      const s = await (await fetch('/stamp', {cache: 'no-store'})).text();
      if (last !== null && s !== last) { location.reload(); return; }
      last = s;
    } catch (e) {}
    setTimeout(tick, 2000);
  }
  tick();
})();
</script>
"""


def stamp():
    files = glob.glob(os.path.join(DOCS, "**", "*.md"), recursive=True)
    newest = max((os.path.getmtime(p) for p in files), default=0)
    return "%d-%f" % (len(files), newest)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/stamp"):
            body, kind = stamp().encode(), "text/plain; charset=utf-8"
        elif self.path in ("/", "/index.html"):
            html, _ = build()
            body, kind = html.replace("</body>", POLL + "</body>").encode("utf-8"), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://localhost:%d" % PORT
    print("设计总览已启动：", url, "（关闭此窗口即停止）")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
