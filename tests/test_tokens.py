import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from picshare.config import state
from picshare import tokens


class TokenStoreTest(unittest.TestCase):
    def setUp(self):
        # 每个用例用独立临时根目录，互不干扰
        self._tmp = tempfile.TemporaryDirectory()
        self._old_base = state.base_dir
        state.base_dir = self._tmp.name

    def tearDown(self):
        state.base_dir = self._old_base
        self._tmp.cleanup()

    def test_create_and_resolve(self):
        t = tokens.create_token("2025-张先生婚礼", label="张先生婚礼")
        meta = tokens.resolve(t)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["album"], "2025-张先生婚礼")
        self.assertEqual(meta["label"], "张先生婚礼")

    def test_token_is_unguessable_length(self):
        t = tokens.create_token("a")
        self.assertGreaterEqual(len(t), 24)

    def test_resolve_unknown_token(self):
        self.assertIsNone(tokens.resolve("does-not-exist"))
        self.assertIsNone(tokens.resolve(""))
        self.assertIsNone(tokens.resolve(None))

    def test_revoke(self):
        t = tokens.create_token("album")
        self.assertTrue(tokens.revoke_token(t))
        self.assertIsNone(tokens.resolve(t))
        self.assertFalse(tokens.revoke_token(t))  # 再次撤销返回 False

    def test_expiry(self):
        t = tokens.create_token("album", expires_days=30)
        self.assertIsNotNone(tokens.resolve(t))
        # 手动把过期时间改到过去
        store = Path(state.base_dir) / state.token_file
        data = json.loads(store.read_text(encoding="utf-8"))
        data["tokens"][t]["expires"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        store.write_text(json.dumps(data), encoding="utf-8")
        self.assertIsNone(tokens.resolve(t))  # 过期后视为无效

    def test_passcode_stored_and_required(self):
        t = tokens.create_token("album", passcode="aB3k")
        self.assertTrue(tokens.requires_passcode(t))
        # 口令明文存储（其安全性来自「不嵌入分享链接」，而非磁盘哈希），便于随时重发
        self.assertEqual(tokens.resolve(t)["passcode"], "aB3k")

    def test_generate_passcode(self):
        pc = tokens.generate_passcode()
        self.assertEqual(len(pc), 4)
        self.assertFalse(set(pc) & set("01IOlo"))  # 不含易混淆字符
        self.assertEqual(len(tokens.generate_passcode(12)), 12)

    def test_passcode_verify(self):
        t = tokens.create_token("album", passcode="1234")
        self.assertTrue(tokens.verify_passcode(t, "1234"))
        self.assertFalse(tokens.verify_passcode(t, "0000"))
        self.assertFalse(tokens.verify_passcode(t, ""))

    def test_no_passcode_always_verifies(self):
        t = tokens.create_token("album")
        self.assertFalse(tokens.requires_passcode(t))
        self.assertTrue(tokens.verify_passcode(t, "anything"))

    def test_list_tokens(self):
        tokens.create_token("a")
        tokens.create_token("b")
        self.assertEqual(len(tokens.list_tokens()), 2)

    def test_corrupt_store_degrades_gracefully(self):
        store = Path(state.base_dir) / state.token_file
        store.write_text("{ not valid json", encoding="utf-8")
        self.assertEqual(tokens.list_tokens(), [])
        self.assertIsNone(tokens.resolve("x"))


if __name__ == "__main__":
    unittest.main()
