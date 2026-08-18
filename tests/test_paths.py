import tempfile
import unittest
from pathlib import Path

from picshare.paths import safe_join, safe_album_join


class SafeJoinTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def test_normal_join(self):
        self.assertEqual(safe_join(str(self.base), "a.jpg"), self.base / "a.jpg")

    def test_nested_join(self):
        # 单段里带斜杠也要能正确落到子目录（相册内子文件夹的常见形态）
        self.assertEqual(safe_join(str(self.base), "第一天/001.jpg"),
                         self.base / "第一天" / "001.jpg")

    def test_escape_returns_none(self):
        self.assertIsNone(safe_join(str(self.base), "../outside.jpg"))
        self.assertIsNone(safe_join(str(self.base), "a/../../outside.jpg"))

    def test_absolute_path_injection_returns_none(self):
        # 绝对路径会顶掉 base，必须被拦
        self.assertIsNone(safe_join(str(self.base), "/etc/passwd"))

    def test_no_double_decoding(self):
        """不得对入参再做一次 URL 解码。

        Werkzeug 已经把路由参数解过码；这里再解一次会让真名含 %2F 的文件被拆成
        两段路径（永远 404），也曾让 %252e%252e%252f 落成 ../。
        """
        self.assertEqual(safe_join(str(self.base), "abc%2Fdef.jpg"),
                         self.base / "abc%2Fdef.jpg")
        # 双层编码解一次后的形态，不应被再解成 ../
        self.assertEqual(safe_join(str(self.base), "%2e%2e%2fx.jpg"),
                         self.base / "%2e%2e%2fx.jpg")


class SafeAlbumJoinTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        (self.root / "albumA").mkdir()
        (self.root / "albumB").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_album_root_without_paths(self):
        self.assertEqual(safe_album_join(str(self.root), "albumA"), self.root / "albumA")

    def test_normal_file_in_album(self):
        self.assertEqual(safe_album_join(str(self.root), "albumA", "a.jpg"),
                         self.root / "albumA" / "a.jpg")

    def test_nested_file_in_album(self):
        self.assertEqual(safe_album_join(str(self.root), "albumA", "第一天/001.jpg"),
                         self.root / "albumA" / "第一天" / "001.jpg")

    def test_cross_album_escape_returns_none(self):
        """核心：safe_join 会放行的横向穿越，这里必须拦下。"""
        payload = "../albumB/secret.jpg"
        # 旧写法（夹的是根目录）确实会放行——留作对照，说明为什么需要本函数
        self.assertIsNotNone(safe_join(str(self.root), "albumA", payload))
        self.assertIsNone(safe_album_join(str(self.root), "albumA", payload))

    def test_escape_above_root_returns_none(self):
        self.assertIsNone(safe_album_join(str(self.root), "albumA", "../../outside.jpg"))

    def test_untrusted_album_name_returns_none(self):
        self.assertIsNone(safe_album_join(str(self.root), "../..", "a.jpg"))


if __name__ == "__main__":
    unittest.main()
