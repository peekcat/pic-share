import glob
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from picshare.config import state
from picshare import preview


class AtomicPreviewWriteTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_base = state.base_dir
        state.base_dir = self._tmp.name

    def tearDown(self):
        state.base_dir = self._old_base
        self._tmp.cleanup()

    def test_concurrent_same_preview_not_corrupt(self):
        base = Path(self._tmp.name)
        src = base / "p.jpg"
        Image.new("RGB", (1500, 1500), (120, 90, 60)).save(src, quality=90)
        prev = base / state.preview_subdir / "p.jpg"

        errs = []

        def worker():
            try:
                preview.generator.generate_sync(src, prev)
            except Exception as e:  # pragma: no cover
                errs.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errs, f"并发生成抛异常: {errs}")
        # 最终预览必须是完整、可打开的 JPEG（原子替换保证不会是半截文件）
        with Image.open(prev) as im:
            im.load()
        # 不留临时文件
        leftovers = glob.glob(str(base / state.preview_subdir / ".tmp_*"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
