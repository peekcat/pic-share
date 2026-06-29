import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from picshare.config import state
from picshare import tokens
from picshare.web.app import app


class RouteAccessTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_base = state.base_dir
        state.base_dir = self._tmp.name
        base = Path(self._tmp.name)

        # 相册 A：一张真实 JPG + 一个伪 RAW
        (base / "albumA").mkdir()
        Image.new("RGB", (400, 300), (200, 100, 100)).save(base / "albumA" / "a.jpg", quality=80)
        (base / "albumA" / "raw.cr2").write_bytes(b"RAWDATA" * 50)
        # 相册 B：另一张图（用于隔离验证）
        (base / "albumB").mkdir()
        Image.new("RGB", (400, 300), (100, 100, 200)).save(base / "albumB" / "b.jpg", quality=80)

        self.tok = tokens.create_token("albumA", label="客户A")
        self.tok_pass = tokens.create_token("albumA", passcode="1234")
        app.config.update(TESTING=True)
        self.c = app.test_client()

    def tearDown(self):
        state.base_dir = self._old_base
        self._tmp.cleanup()

    def U(self, *parts):
        return "/".join(quote(p) for p in parts)

    # ---- 落地页 & 无效 token ----
    def test_landing_has_no_album_input(self):
        r = self.c.get("/")
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("专属", body)
        self.assertNotIn("<form action=\"/check_album\"", body)  # 旧枚举入口已移除

    def test_old_routes_gone(self):
        self.assertEqual(self.c.get("/album/albumA").status_code, 404)
        self.assertEqual(self.c.get("/check_album?name=albumA").status_code, 404)
        self.assertEqual(self.c.get("/api/check_mark").status_code, 404)

    def test_invalid_token_404(self):
        self.assertEqual(self.c.get("/a/nope").status_code, 404)

    # ---- 无口令 token 正常访问 ----
    def test_album_and_files(self):
        self.assertEqual(self.c.get(f"/a/{self.tok}").status_code, 200)
        self.assertEqual(self.c.get(f"/a/{self.tok}/p/a.jpg").status_code, 200)
        self.assertEqual(self.c.get(f"/a/{self.tok}/o/a.jpg").status_code, 200)

    def test_raw_original_blocked(self):
        self.assertEqual(self.c.get(f"/a/{self.tok}/o/raw.cr2").status_code, 403)

    def test_cross_album_isolation(self):
        # albumA 的 token 无法取到 albumB 的文件（相册由 token 固定）
        self.assertEqual(self.c.get(f"/a/{self.tok}/o/b.jpg").status_code, 404)

    def test_token_for_system_dir_404(self):
        bad = tokens.create_token(state.marked_subdir)
        self.assertEqual(self.c.get(f"/a/{bad}").status_code, 404)

    # ---- 口令流程 ----
    def test_passcode_gate(self):
        r = self.c.get(f"/a/{self.tok_pass}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("访问口令", r.get_data(as_text=True))  # 显示口令页而非相册
        # 未解锁时文件路由直接 403
        self.assertEqual(self.c.get(f"/a/{self.tok_pass}/p/a.jpg").status_code, 403)

    def test_passcode_wrong_then_right(self):
        r = self.c.post(f"/a/{self.tok_pass}/unlock", data={"passcode": "0000"})
        self.assertIn("口令错误", r.get_data(as_text=True))
        # 正确口令 → 跳转 → 解锁后可访问
        r2 = self.c.post(f"/a/{self.tok_pass}/unlock", data={"passcode": "1234"})
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(self.c.get(f"/a/{self.tok_pass}").status_code, 200)
        self.assertEqual(self.c.get(f"/a/{self.tok_pass}/p/a.jpg").status_code, 200)

    # ---- 标记流程 ----
    def test_mark_toggle_and_check(self):
        # 初始未标记
        r = self.c.get(f"/a/{self.tok}/check_mark?filename=a.jpg")
        self.assertEqual(r.get_json(), {"is_marked": False})
        # 标记
        r2 = self.c.post(f"/a/{self.tok}/mark", json={"filename": "a.jpg"})
        self.assertTrue(r2.get_json()["is_marked"])
        self.assertTrue((Path(state.base_dir) / state.marked_subdir / "albumA" / "a.jpg").exists())
        # 取消
        r3 = self.c.post(f"/a/{self.tok}/mark", json={"filename": "a.jpg"})
        self.assertFalse(r3.get_json()["is_marked"])

    def test_mark_missing_filename_is_400_not_500(self):
        r = self.c.post(f"/a/{self.tok}/mark", json={})
        self.assertEqual(r.status_code, 400)

    def test_check_mark_missing_filename_is_false_not_null(self):
        r = self.c.get(f"/a/{self.tok}/check_mark")
        self.assertEqual(r.get_json(), {"is_marked": False})


if __name__ == "__main__":
    unittest.main()
