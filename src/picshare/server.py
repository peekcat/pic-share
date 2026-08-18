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

# 当前运行中的对外服务。换端口时要停掉旧的，故需持有引用。
# 单服务的桌面程序，与 config.state 的单例风格一致。
_current = None


class ServerStartError(Exception):
    """对外服务未能启动。message 为可直接展示给用户的说明。"""


def create_public_server(port: int):
    """在 ``[::]:port`` 上创建对外服务（绑定在此完成）。

    绑定失败抛 ``ServerStartError``，其 message 只陈述事实（哪个端口怎么了）。
    该做什么由调用点补充——启动失败与界面改端口失败该说的话不一样。
    任何情况下都不针对特定操作系统或具体软件做猜测式提示。
    """
    from waitress import create_server
    try:
        return create_server(app, listen=f"[::]:{port}", threads=16)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            # 只陈述事实。后续建议由调用点补——启动时与界面改端口时该说的话不一样，
            # 也不针对任何操作系统或具体软件做猜测式提示。
            raise ServerStartError(f"端口 {port} 被占用。") from e
        raise ServerStartError(f"对外服务启动失败：{e}") from e


def _spawn(server):
    """把阻塞的 ``run()`` 放进守护线程。

    ``server.close()`` 会把 socket 从 asyncore 循环下面抽走，循环随即抛 OSError
    ——那是我们主动停服的正常结果，吞掉即可，否则每次换端口都刷一屏 traceback。
    """
    def _run():
        try:
            server.run()
        except OSError as e:
            logger.debug(f"对外服务循环退出（通常是主动停服）：{e}")

    threading.Thread(target=_run, daemon=True, name="picshare-web").start()


def start_public_server(port: int):
    """绑定成功后把阻塞的 ``run()`` 放进守护线程，返回 server 对象。

    绑定失败直接抛 ``ServerStartError``，由调用方决定如何告知用户。
    """
    global _current
    server = create_public_server(port)
    _current = server
    _spawn(server)
    logger.info(f"对外服务已启动，监听端口 {port}")
    return server


def restart_public_server(port: int):
    """在新端口上重启对外服务，返回新的 server 对象。

    **先绑新端口、成功后才停旧的**：新端口绑不上时直接抛 ``ServerStartError``，
    旧服务原封不动继续跑——绝不能让用户落到「两个端口都没服务」的境地。
    """
    global _current
    server = create_public_server(port)   # 失败即抛，此时 _current 尚未动过
    old, _current = _current, server
    if old is not None:
        old.close()
    _spawn(server)
    logger.info(f"对外服务已切换到端口 {port}")
    return server
