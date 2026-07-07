"""桌面入口：pywebview 宿主窗口 + 对外 Web 服务。

- 管理界面：pywebview 加载本地 HTML，经 js_api 进程内调用 Python（无管理 HTTP 端点）。
- 对外服务：waitress 在 ``[::]:port`` 提供客户端 ``/share`` 访问，与原版一致。
"""

import threading
from pathlib import Path

import webview

from .config import state
from .web.app import app
from .admin.api import Api
from .admin.templates import ADMIN_HTML
from . import status, settings


def _serve_app(port):
    """对外 Web 服务（waitress：生产级 WSGI，多线程、Windows 友好）。"""
    from waitress import serve
    serve(app, listen=f"[::]:{port}", threads=16)


def main():
    status.setup_logging(settings.log_file())  # 统一日志：控制台 + 滚动文件 + 运行日志面板
    api = Api()
    status.set_gui_sink(api.log)  # 后端日志（含 RAW 解码报错等）汇入管理窗口运行日志

    # 启动对外 Web 服务（守护线程，随主程序退出）
    threading.Thread(target=_serve_app, args=(state.port,), daemon=True).start()

    window = webview.create_window(
        "PicShare · IPv6 相册服务",
        html=ADMIN_HTML,
        js_api=api,
        width=900, height=800, min_size=(620, 560),
    )
    api.set_window(window)

    def _on_start():
        api.log("✅ 服务已启动，等待连接")
        # 延迟一点再预热，让窗口先渲染完
        if state.base_dir and Path(state.base_dir).exists():
            threading.Timer(2.0, lambda: api._start_prewarm(state.base_dir)).start()

    webview.start(_on_start)


if __name__ == "__main__":
    main()
