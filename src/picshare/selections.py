"""客户选片清单存储。

每个相册维护一份「已选文件」清单，存于 ``<根目录>/._picshare/selections.json``，按相册名归集。
选片只改清单（快、不复制原图）；真正的原图交付在桌面端点「收藏夹」时，按清单同步到
``被标记的照片`` 文件夹。同一进程内 Flask 线程(写)与 GUI 线程(读)共享，加锁保护。
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import state

# 与 tokens 一样：同进程内 Web 线程(写)与 GUI 线程(读)共享存储，加锁保护
_LOCK = threading.Lock()


def _store_path() -> Path:
    # 随当前根目录走（切换目录后自动指向新目录下的文件）
    return Path(state.base_dir) / state.selection_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty() -> dict:
    return {"version": 1, "albums": {}}


def _load() -> dict:
    p = _store_path()
    if not p.exists():
        return _empty()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "albums" not in data:
            return _empty()
        return data
    except Exception:
        # 文件损坏时退化为空，不让整个服务崩溃
        return _empty()


def _save(data: dict) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(p)  # 原子替换，避免半写文件


def list_selected(album: str) -> list:
    """返回该相册已选文件的相对路径列表(posix)。"""
    with _LOCK:
        entry = _load()["albums"].get(album)
        return list(entry["files"]) if entry else []


def count_selected(album: str) -> int:
    """返回该相册已选数量。"""
    with _LOCK:
        entry = _load()["albums"].get(album)
        return len(entry["files"]) if entry else 0


def toggle(album: str, filename: str) -> tuple[bool, int]:
    """翻转单个文件的选中态，返回 (最新是否选中, 该相册最新已选数量)。

    以服务端清单为准翻转，避免与客户端乐观状态产生分歧。
    """
    with _LOCK:
        data = _load()
        entry = data["albums"].setdefault(album, {"files": [], "updated": _now_iso()})
        files = entry["files"]
        if filename in files:
            files.remove(filename)
            now_selected = False
        else:
            files.append(filename)
            now_selected = True
        entry["updated"] = _now_iso()
        if not files:
            data["albums"].pop(album, None)  # 清空后不保留空条目
        _save(data)
        return now_selected, len(files)


def clear_selected(album: str) -> int:
    """清空该相册全部选择，返回清空前的数量。"""
    with _LOCK:
        data = _load()
        entry = data["albums"].pop(album, None)
        if entry is None:
            return 0
        _save(data)
        return len(entry["files"])
