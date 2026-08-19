import errno
import socket
import threading
import unittest
from unittest import mock

from picshare import server


def _take_port():
    """占住一个临时端口的 IPv6 侧，返回 (socket, port)。调用方负责关闭。

    服务是双栈的，只占住一个协议族就足以让绑定失败——这正是要测的：
    半边被占也必须如实报错，而不是起一个只有一半能连的服务。
    """
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    s.bind(("::", 0))
    s.listen(1)
    return s, s.getsockname()[1]


def _bindable(family, port):
    """该协议族上这个端口现在还能不能绑（用来验证失败后没有残留占用）。"""
    probe = socket.socket(family, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    try:
        probe.bind(("::" if family == socket.AF_INET6 else "0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


class CreatePublicServerTest(unittest.TestCase):
    def test_free_port_binds_both_families(self):
        """双栈：IPv6 供公网远程交付，IPv4 覆盖同一局域网当面选片，缺一不可。

        waitress 对 IPv6 socket 显式设了 IPV6_V6ONLY=1，只绑 [::] 不会自动兼容
        IPv4——这条就是防止有人"简化"回单地址监听。
        """
        holder, port = _take_port()
        holder.close()                      # 拿到一个大概率空闲的端口号后立即释放
        srv = server.create_public_server(port)
        try:
            # MultiSocketServer 没有 .socket，只有 effective_listen
            listen = {(host, int(p)) for host, p in srv.effective_listen}
            self.assertIn(("0.0.0.0", port), listen)
            self.assertIn(("::", port), listen)
        finally:
            srv.close()

    def test_port_in_use_names_the_port(self):
        """只陈述事实：哪个端口被占用。该怎么办由调用点按场景补充。"""
        holder, port = _take_port()
        try:
            with self.assertRaises(server.ServerStartError) as cm:
                server.create_public_server(port)
        finally:
            holder.close()
        msg = str(cm.exception)
        self.assertIn(str(port), msg)
        self.assertIn("被占用", msg)
        # 不应把「重启程序」写死在这里——界面上改端口失败时并不需要重启
        self.assertNotIn("重启", msg)

    def test_message_names_no_operating_system(self):
        """错误文案只陈述事实，不针对特定系统/软件做猜测式提示。

        这是明确的产品要求：写成断言，防止以后有人「好心」把
        macOS / AirPlay 之类的提示加回去。
        """
        holder, port = _take_port()
        try:
            with self.assertRaises(server.ServerStartError) as cm:
                server.create_public_server(port)
        finally:
            holder.close()
        lowered = str(cm.exception).lower()
        for word in ("macos", "mac os", "airplay", "airtunes", "windows",
                     "linux", "隔空", "控制中心"):
            self.assertNotIn(word, lowered, f"文案不应提及特定系统/软件：{word}")

    def test_half_taken_port_leaves_nothing_bound(self):
        """只有 IPv6 侧被占时，IPv4 侧不能被我们自己占住不放。

        直接把双栈交给 waitress 会踩到这个坑：它按顺序绑，v4 先成功、v6 再失败，
        那个已绑上的 v4 socket 会卡在 asyncore 的引用环里迟迟不回收。用户
        「改端口失败 → 立刻重试同一端口」就会撞上一个自己造出来的占用。
        """
        holder, port = _take_port()
        try:
            with self.assertRaises(server.ServerStartError):
                server.create_public_server(port)
            self.assertTrue(_bindable(socket.AF_INET, port),
                            "IPv4 侧被我们自己占住了，端口再也换不回来")
        finally:
            holder.close()

    def test_other_oserror_uses_generic_message(self):
        """非「端口占用」的绑定错误照样如实报出，但不得误报为被占用。"""
        boom = OSError(errno.EACCES, "Permission denied")
        holder, port = _take_port()
        holder.close()                      # 预检要能过，错误才来自被 mock 的 waitress
        with mock.patch("waitress.create_server", side_effect=boom):
            with self.assertRaises(server.ServerStartError) as cm:
                server.create_public_server(port)
        msg = str(cm.exception)
        self.assertIn("启动失败", msg)
        self.assertNotIn("被占用", msg)


class StartPublicServerTest(unittest.TestCase):
    def test_start_runs_server_in_daemon_thread(self):
        """验证接线：run() 必须跑在守护线程里，否则关窗口时进程不退出。

        用假 server 替掉真实绑定——既不真跑 asyncore 循环（close() 会把 socket
        从循环下抽走、刷一屏噪音），也不去 patch 全局的 threading.Thread
        （waitress 自己就要起 16 个工作线程，patch 了会把它们一并捕获）。
        """
        ran = threading.Event()
        seen = {}

        fake = mock.Mock()
        fake.run.side_effect = lambda: (seen.update(thread=threading.current_thread()),
                                        ran.set())

        with mock.patch.object(server, "create_public_server", return_value=fake):
            srv = server.start_public_server(5000)

        self.assertIs(srv, fake)
        self.assertTrue(ran.wait(5), "run() 未在后台线程中被调用")
        self.assertTrue(seen["thread"].daemon, "必须是守护线程，否则关窗口后进程不退出")
        self.assertNotEqual(seen["thread"], threading.current_thread())

    def test_start_propagates_bind_failure(self):
        holder, port = _take_port()
        try:
            with self.assertRaises(server.ServerStartError):
                server.start_public_server(port)
        finally:
            holder.close()


class RestartPublicServerTest(unittest.TestCase):
    """换端口重启。核心不变量：新端口绑不上时，旧服务必须原封不动继续跑。"""

    def setUp(self):
        self._free = []

    def tearDown(self):
        if server._current is not None:
            server._current.close()
            server._current = None
        for s in self._free:
            s.close()

    @staticmethod
    def _free_port():
        holder, port = _take_port()
        holder.close()
        return port

    @staticmethod
    def _alive(port, host="[::1]"):
        """真发一次 HTTP 请求确认服务在响应（落地页无需任何相册配置）。"""
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def test_serves_over_ipv4_as_well(self):
        """端到端确认 IPv4 真的能连上——局域网当面选片全靠这条。

        只断言 socket 绑上了还不够：waitress 对 IPv6 socket 设了 IPV6_V6ONLY=1，
        历史上就是因为只绑 [::] 才让 IPv4 客户端吃闭门羹。
        """
        port = self._free_port()
        server.start_public_server(port)
        self.assertTrue(self._alive(port, "127.0.0.1"), "IPv4 连不上")
        self.assertTrue(self._alive(port, "[::1]"), "IPv6 连不上")

    def test_moves_service_to_new_port(self):
        p1, p2 = self._free_port(), self._free_port()
        server.start_public_server(p1)
        self.assertTrue(self._alive(p1), "旧端口应先能服务")

        server.restart_public_server(p2)
        self.assertTrue(self._alive(p2), "新端口应能服务")
        self.assertFalse(self._alive(p1), "旧端口应已停止服务")

    def test_releases_old_port(self):
        p1, p2 = self._free_port(), self._free_port()
        server.start_public_server(p1)
        server.restart_public_server(p2)

        probe = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._free.append(probe)
        try:
            probe.bind(("::", p1))
        except OSError as e:
            self.fail(f"旧端口未释放：{e}")

    def test_updates_current(self):
        p1, p2 = self._free_port(), self._free_port()
        server.start_public_server(p1)
        new = server.restart_public_server(p2)
        self.assertIs(server._current, new)

    def test_bind_failure_keeps_old_server_alive(self):
        """最重要的一条：换到被占用的端口失败后，用户不能两个端口都连不上。"""
        p1 = self._free_port()
        old = server.start_public_server(p1)
        self.assertTrue(self._alive(p1))

        blocker, busy = _take_port()
        self._free.append(blocker)
        with self.assertRaises(server.ServerStartError):
            server.restart_public_server(busy)

        self.assertIs(server._current, old, "失败后 _current 不该被换掉")
        self.assertTrue(self._alive(p1), "失败后旧端口必须仍在服务")


if __name__ == "__main__":
    unittest.main()
