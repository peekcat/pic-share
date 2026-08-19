"""对外 Web 服务的创建与启动。

与桌面/GUI 无关，单独成模块：``desktop.py`` 顶层 import webview，逻辑留在那里
就无法在没有 pywebview 的环境下测试。

关键点：``waitress.serve()`` 等价于 ``create_server()`` + ``server.run()``，而
**绑定发生在 create_server()**。把两步拆开，调用方就能在主线程同步拿到绑定结果，
再把阻塞的 ``run()`` 丢进守护线程——而不是等它在后台线程里静默炸掉。
"""

import errno
import gc
import logging
import socket
import threading

from .web.app import app

logger = logging.getLogger(__name__)

# 当前运行中的对外服务。换端口时要停掉旧的，故需持有引用。
# 单服务的桌面程序，与 config.state 的单例风格一致。
_current = None


class ServerStartError(Exception):
    """对外服务未能启动。message 为可直接展示给用户的说明。"""


def _as_start_error(port: int, e: OSError) -> ServerStartError:
    """把绑定失败翻译成可直接展示的说明。

    只陈述事实。后续建议由调用点补——启动时与界面改端口时该说的话不一样，
    也不针对任何操作系统或具体软件做猜测式提示。
    """
    if e.errno == errno.EADDRINUSE:
        return ServerStartError(f"端口 {port} 被占用。")
    return ServerStartError(f"对外服务启动失败：{e}")


def _preflight(port: int):
    """真正建服务之前，先确认 IPv4 / IPv6 两个协议族都能绑上这个端口。

    不能直接把双栈交给 waitress 试：它按顺序绑，前一个成功、后一个失败时，
    已绑上的那个 socket 会卡在 asyncore 的引用环里迟迟不释放（实测要 gc.collect()
    才回收）。用户「改端口失败 → 立刻重试同一端口」就会撞上一个自己造出来的占用。

    探测 socket 的选项与 waitress 保持一致（SO_REUSEADDR、IPv6 上 IPV6_V6ONLY），
    否则探测结果与真实绑定结果会不一致——尤其 Windows 上 SO_REUSEADDR 的语义与
    类 Unix 不同。
    """
    for family, addr in ((socket.AF_INET, ("0.0.0.0", port)),
                         (socket.AF_INET6, ("::", port))):
        probe = socket.socket(family, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            probe.bind(addr)
        except OSError as e:
            raise _as_start_error(port, e) from e
        finally:
            probe.close()


def create_public_server(port: int):
    """在 ``0.0.0.0:port`` 与 ``[::]:port`` 上创建对外服务（绑定在此完成）。

    双栈监听：IPv6 用于公网直连交付，IPv4 覆盖同一局域网当面选片的场景。
    waitress 对 IPv6 socket 显式设了 ``IPV6_V6ONLY=1``，所以只绑 ``[::]`` 不会
    自动兼容 IPv4，必须两个地址都写上。

    绑定失败抛 ``ServerStartError``，其 message 只陈述事实（哪个端口怎么了）。
    该做什么由调用点补充——启动失败与界面改端口失败该说的话不一样。
    """
    from waitress import create_server
    _preflight(port)
    try:
        return create_server(app, listen=f"0.0.0.0:{port} [::]:{port}", threads=16)
    except OSError as e:
        # 预检与真正绑定之间存在极小的竞态窗口。真撞上了，得替 waitress 收拾那个
        # 半绑状态下漏出来的 socket，否则这个端口在本进程内会一直显示被占用。
        gc.collect()
        raise _as_start_error(port, e) from e


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
