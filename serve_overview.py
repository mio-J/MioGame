"""启动设计总览的入口，实际代码在 工具/总览/serve.py。

单独放在根目录、文件名用英文，是为了让 打开设计总览.bat 里不出现中文路径
（cmd 读取含中文的 bat 内容容易出错）。
"""
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(HERE, "工具", "总览", "serve.py"), run_name="__main__")
