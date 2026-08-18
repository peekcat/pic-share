import errno
import socket
import threading
import unittest
from unittest import mock

from picshare import server


def _take_port():
    """占住一个临时端口，返回 (socket, port)。调用方负责关闭。"""
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("::", 0))
    s.listen(1)
    return s, s.getsockname()[1]


class CreatePublicServerTest(unittest.TestCase):
    def test_free_port_creates_server(self):
        holder, port = _take_port()
        holder.close()                      # 拿到一个大概率空闲的端口号后立即释放
        srv = server.create_public_server(port)
        try:
            self.assertEqual(srv.socket.getsockname()[1], port)
        finally:
            srv.close()

    def test_port_in_use_raises_with_actionable_message(self):
        holder, port = _take_port()
        try:
            with self.assertRaises(server.ServerStartError) as cm:
                server.create_public_server(port)
        finally:
            holder.close()
        msg = str(cm.exception)
        self.assertIn(str(port), msg)       # 说清是哪个端口
        self.assertIn("被占用", msg)
        self.assertIn("重启", msg)          # 说清怎么办

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

    def test_other_oserror_uses_generic_message(self):
        """非「端口占用」的绑定错误照样如实报出，但不得误报为被占用。"""
        boom = OSError(errno.EACCES, "Permission denied")
        with mock.patch("waitress.create_server", side_effect=boom):
            with self.assertRaises(server.ServerStartError) as cm:
                server.create_public_server(5000)
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


if __name__ == "__main__":
    unittest.main()
