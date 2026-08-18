import unittest
from unittest import mock

from picshare.config import ServerState, normalize_port, DEFAULT_PORT, PORT_MIN, PORT_MAX


class NormalizePortTest(unittest.TestCase):
    def test_accepts_int_and_string(self):
        self.assertEqual(normalize_port(5001), 5001)
        self.assertEqual(normalize_port("5001"), 5001)
        self.assertEqual(normalize_port("  8080  "), 8080)   # 界面输入常带空格

    def test_boundaries_are_inclusive(self):
        self.assertEqual(normalize_port(PORT_MIN), PORT_MIN)
        self.assertEqual(normalize_port(PORT_MAX), PORT_MAX)

    def test_rejects_out_of_range(self):
        for bad in (PORT_MIN - 1, PORT_MAX + 1, 0, -1, 80):
            with self.subTest(port=bad):
                with self.assertRaises(ValueError) as cm:
                    normalize_port(bad)
                self.assertIn("1024", str(cm.exception))

    def test_rejects_non_numeric(self):
        for bad in ("abc", "", "  ", None, "50 00", "5000.5"):
            with self.subTest(port=bad):
                with self.assertRaises(ValueError) as cm:
                    normalize_port(bad)
                self.assertIn("数字", str(cm.exception))


class LoadPortTest(unittest.TestCase):
    """端口从用户设置里读，且要能扛住被手改坏的值。"""

    def test_uses_persisted_value(self):
        with mock.patch("picshare.settings.get", return_value=5051):
            self.assertEqual(ServerState._load_port(), 5051)

    def test_falls_back_to_default_when_unset(self):
        with mock.patch("picshare.settings.get", return_value=None):
            self.assertEqual(ServerState._load_port(), DEFAULT_PORT)

    def test_falls_back_to_default_on_garbage(self):
        # settings.json 是纯文本，用户可能手改坏；坏值不该让程序起不来
        for bad in ("", "abc", 80, 70000, [], {"a": 1}):
            with self.subTest(stored=bad):
                with mock.patch("picshare.settings.get", return_value=bad):
                    self.assertEqual(ServerState._load_port(), DEFAULT_PORT)


if __name__ == "__main__":
    unittest.main()
