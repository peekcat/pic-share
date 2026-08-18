"""对外 Web 服务的创建与启动。

与桌面/GUI 无关，单独成模块：``desktop.py`` 顶层 import webview，逻辑留在那里
就无法在没有 pywebview 的环境下测试。

关键点：``waitress.serve()`` 等价于 ``create_server()`` + ``server.run()``，而
**绑定发生在 create_server()**。把两步拆开，调用方就能在主线程同步拿到绑定结果，
再把阻塞的 ``run()`` 丢进守护线程——而不是等它在后台线程里静默炸掉。
"""

import errno
import logging
import threading

from .web.app import app

logger = logging.getLogger(__name__)


class ServerStartError(Exception):
    """对外服务未能启动。message 为可直接展示给用户的说明。"""


def create_public_server(port: int):
    """在 ``[::]:port`` 上创建对外服务（绑定在此完成）。

    绑定失败抛 ``ServerStartError``。文案只陈述事实：哪个端口、什么后果、怎么办，
    不针对任何操作系统或具体软件做猜测式提示。
    """
    from waitress import create_server
    try:
        return create_server(app, listen=f"[::]:{port}", threads=16)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            raise ServerStartError(
                f"端口 {port} 被占用，对外服务未启动，分享链接暂时无法访问。"
                f"请释放该端口后重启 PicShare。"
            ) from e
        raise ServerStartError(f"对外服务启动失败：{e}") from e


def start_public_server(port: int):
    """绑定成功后把阻塞的 ``run()`` 放进守护线程，返回 server 对象。

    绑定失败直接抛 ``ServerStartError``，由调用方决定如何告知用户。
    """
    server = create_public_server(port)
    threading.Thread(target=server.run, daemon=True, name="picshare-web").start()
    logger.info(f"对外服务已启动，监听端口 {port}")
    return server
