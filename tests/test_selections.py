import json
import tempfile
import unittest
from pathlib import Path

from picshare.config import state
from picshare import selections


class SelectionStoreTest(unittest.TestCase):
    def setUp(self):
        # 每个用例用独立临时根目录，互不干扰
        self._tmp = tempfile.TemporaryDirectory()
        self._old_base = state.base_dir
        state.base_dir = self._tmp.name

    def tearDown(self):
        state.base_dir = self._old_base
        self._tmp.cleanup()

    def test_empty_album(self):
        self.assertEqual(selections.list_selected("album"), [])
        self.assertEqual(selections.count_selected("album"), 0)

    def test_toggle_on_and_off(self):
        self.assertEqual(selections.toggle("album", "a.jpg"), (True, 1))
        self.assertEqual(selections.list_selected("album"), ["a.jpg"])
        self.assertEqual(selections.count_selected("album"), 1)
        self.assertEqual(selections.toggle("album", "a.jpg"), (False, 0))
        self.assertEqual(selections.list_selected("album"), [])

    def test_toggle_keeps_nested_relative_paths(self):
        # 相册内可以有子文件夹，清单存 posix 相对路径
        selections.toggle("album", "第一天/001.jpg")
        self.assertEqual(selections.list_selected("album"), ["第一天/001.jpg"])

    def test_albums_are_isolated(self):
        selections.toggle("albumA", "a.jpg")
        selections.toggle("albumB", "b.jpg")
        self.assertEqual(selections.list_selected("albumA"), ["a.jpg"])
        self.assertEqual(selections.list_selected("albumB"), ["b.jpg"])
        # 清空一个不影响另一个
        selections.clear_selected("albumA")
        self.assertEqual(selections.list_selected("albumA"), [])
        self.assertEqual(selections.list_selected("albumB"), ["b.jpg"])

    def test_clear_returns_previous_count(self):
        selections.toggle("album", "a.jpg")
        selections.toggle("album", "b.jpg")
        self.assertEqual(selections.clear_selected("album"), 2)
        self.assertEqual(selections.clear_selected("album"), 0)  # 已空再清返回 0

    def test_empty_album_entry_is_dropped(self):
        """全部取消后不留空条目，避免 selections.json 里堆积垃圾相册键。"""
        selections.toggle("album", "a.jpg")
        selections.toggle("album", "a.jpg")
        data = json.loads((Path(state.base_dir) / state.selection_file).read_text(encoding="utf-8"))
        self.assertEqual(data["albums"], {})

    def test_corrupt_store_degrades_gracefully(self):
        store = Path(state.base_dir) / state.selection_file
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text("{ not valid json", encoding="utf-8")
        # 文件损坏时退化为空，不让整个服务崩溃
        self.assertEqual(selections.list_selected("album"), [])
        self.assertEqual(selections.count_selected("album"), 0)


if __name__ == "__main__":
    unittest.main()
