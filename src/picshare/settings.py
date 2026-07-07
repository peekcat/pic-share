"""用户级配置持久化（记住相册根目录等设置，重启后自动恢复）。

存放在各平台标准配置目录，而非相册根目录下——根目录本身就是要持久化的内容，
不能依赖它来定位配置文件。
"""

import os
import sys
import json
from pathlib import Path


def _config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / "PicShare"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PicShare"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "PicShare"


def _settings_file() -> Path:
    return _config_dir() / "settings.json"


def log_file() -> Path:
    """日志文件路径（与配置同目录，跨平台标准位置）。"""
    return _config_dir() / "picshare.log"


def load_settings() -> dict:
    try:
        with open(_settings_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def save_settings(data: dict) -> None:
    try:
        _config_dir().mkdir(parents=True, exist_ok=True)
        target = _settings_file()
        tmp = target.with_name(target.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)  # 原子替换，避免写一半损坏
    except OSError:
        pass


def get(key, default=None):
    return load_settings().get(key, default)


def set_value(key, value) -> None:
    data = load_settings()
    data[key] = value
    save_settings(data)
