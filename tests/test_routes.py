import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from picshare.config import state
from picshare import tokens, selections
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
        self.assertEqual(self.c.get("/share/nope").status_code, 404)

    # ---- 无口令 token 正常访问 ----
    def test_album_and_files(self):
        self.assertEqual(self.c.get(f"/share/{self.tok}").status_code, 200)
        self.assertEqual(self.c.get(f"/share/{self.tok}/preview/a.jpg").status_code, 200)
        self.assertEqual(self.c.get(f"/share/{self.tok}/original/a.jpg").status_code, 200)

    def test_raw_original_blocked(self):
        self.assertEqual(self.c.get(f"/share/{self.tok}/original/raw.cr2").status_code, 403)

    def test_cross_album_isolation(self):
        # albumA 的 token 无法取到 albumB 的文件（相册由 token 固定）
        self.assertEqual(self.c.get(f"/share/{self.tok}/original/b.jpg").status_code, 404)

    def test_token_for_system_dir_404(self):
        bad = tokens.create_token(state.marked_subdir)
        self.assertEqual(self.c.get(f"/share/{bad}").status_code, 404)

    # ---- 口令流程 ----
    def test_passcode_gate(self):
        r = self.c.get(f"/share/{self.tok_pass}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("访问口令", r.get_data(as_text=True))  # 显示口令页而非相册
        # 未解锁时文件路由直接 403
        self.assertEqual(self.c.get(f"/share/{self.tok_pass}/preview/a.jpg").status_code, 403)

    def test_passcode_wrong_then_right(self):
        r = self.c.post(f"/share/{self.tok_pass}/unlock", data={"passcode": "0000"})
        self.assertIn("口令错误", r.get_data(as_text=True))
        # 正确口令 → 跳转 → 解锁后可访问
        r2 = self.c.post(f"/share/{self.tok_pass}/unlock", data={"passcode": "1234"})
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(self.c.get(f"/share/{self.tok_pass}").status_code, 200)
        self.assertEqual(self.c.get(f"/share/{self.tok_pass}/preview/a.jpg").status_code, 200)

    # ---- 标记流程 ----
    def test_mark_toggle(self):
        self.assertEqual(selections.list_selected("albumA"), [])
        # 标记
        r = self.c.post(f"/share/{self.tok}/mark", json={"filename": "a.jpg"})
        self.assertEqual(r.get_json(), {"success": True, "is_marked": True, "count": 1})
        self.assertEqual(selections.list_selected("albumA"), ["a.jpg"])
        # 取消
        r2 = self.c.post(f"/share/{self.tok}/mark", json={"filename": "a.jpg"})
        self.assertEqual(r2.get_json(), {"success": True, "is_marked": False, "count": 0})
        self.assertEqual(selections.list_selected("albumA"), [])

    def test_mark_only_writes_manifest_no_copy(self):
        """选片只写清单、不复制原图——原图复制发生在桌面端点「导出」时。"""
        self.c.post(f"/share/{self.tok}/mark", json={"filename": "a.jpg"})
        self.assertFalse((Path(state.base_dir) / state.marked_subdir).exists())

    @unittest.expectedFailure
    def test_mark_rejects_file_outside_album(self):
        """【已知缺陷，待修】客户可用 ../ 把别的相册的文件写进本相册的选片清单。

        根因：paths.safe_join() 只保证结果落在它的第一个参数内，而所有路由都写成
        safe_join(state.base_dir, album, filename)——夹的是「根目录」而非「相册目录」，
        于是 filename 里的 ../ 可以横向跨到同根下的其它相册。
        同一根因还让 preview / view / original 路由能直接读到别的相册的照片。
        修复后请删除本装饰器（届时 unittest 会以「意外通过」提醒你）。
        """
        r = self.c.post(f"/share/{self.tok}/mark", json={"filename": "../albumB/b.jpg"})
        self.assertFalse(r.get_json()["success"])
        self.assertEqual(selections.list_selected("albumA"), [])

    @unittest.expectedFailure
    def test_cross_album_traversal_blocked(self):
        """【已知缺陷，待修】同上：token 绑定的相册边界能被 ../ 绕过。

        README 承诺「客户无法在 URL 中指定相册名，也看不到、猜不到别人的相册」，
        当前实现不满足该承诺——只要猜中相册文件夹名与文件名即可读取。
        """
        r = self.c.get(f"/share/{self.tok}/original/..%2falbumB%2fb.jpg")
        self.assertEqual(r.status_code, 404)

    def test_album_page_injects_selected_list(self):
        """已选清单由服务端一次性注入相册页（取代已删除的 check_mark 轮询接口）。"""
        body = self.c.get(f"/share/{self.tok}").get_data(as_text=True)
        self.assertIn("[].forEach", body)  # 未选片时注入空数组
        self.c.post(f"/share/{self.tok}/mark", json={"filename": "a.jpg"})
        body2 = self.c.get(f"/share/{self.tok}").get_data(as_text=True)
        self.assertIn('["a.jpg"]', body2)

    def test_clear_selection(self):
        self.c.post(f"/share/{self.tok}/mark", json={"filename": "a.jpg"})
        r = self.c.post(f"/share/{self.tok}/clear_selection")
        self.assertEqual(r.get_json(), {"success": True, "count": 0})
        self.assertEqual(selections.list_selected("albumA"), [])

    def test_mark_missing_filename_is_400_not_500(self):
        r = self.c.post(f"/share/{self.tok}/mark", json={})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
