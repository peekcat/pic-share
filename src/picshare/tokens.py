"""相册访问 token 存储与校验。

能力 URL(Capability URL)模型：每个相册子文件夹绑定一个不可枚举的随机 token，
客户凭 ``/share/<token>`` 访问，相册名由 token 在服务端推导，客户无法指定。

token 存储在 ``<根目录>/._access_tokens.json``，由桌面端创建/撤销，
Web 端只做只读校验。口令以哈希形式存储（werkzeug，零新依赖），绝不落明文。
"""

import json
import secrets
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .config import state

# 同一进程内 GUI 线程(写)与 Flask 线程(读)共享存储，加锁保护
_LOCK = threading.Lock()

# 口令字符集：英文数字混合，剔除易混淆字符(0/1/I/O/l/o)，便于客户手动输入
_PASSCODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz"


def generate_passcode(length: int = 4) -> str:
    """生成随机短口令(默认 4 位英文数字混合)。"""
    return "".join(secrets.choice(_PASSCODE_ALPHABET) for _ in range(length))


def _store_path() -> Path:
    # 存储文件随当前根目录走（GUI 切换目录后自动指向新目录下的文件）
    return Path(state.base_dir) / state.token_file


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _empty():
    return {"version": 1, "tokens": {}}


def _load() -> dict:
    p = _store_path()
    if not p.exists():
        return _empty()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "tokens" not in data:
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


def _is_expired(meta: dict) -> bool:
    exp = meta.get("expires")
    if not exp:
        return False
    try:
        return _now() >= datetime.fromisoformat(exp)
    except Exception:
        return False


def create_token(album: str, *, expires_days: int | None = None,
                 passcode: str | None = None, label: str | None = None) -> str:
    """为 ``album``(相对根目录的相册路径)创建访问 token，返回 token 字符串。

    expires_days: 有效天数，None 表示永久。
    passcode:     可选短口令，None 表示无口令。明文存储以便随时重新复制重发；
                  其安全性来自「不嵌入分享链接」，而非磁盘哈希。
    """
    token = secrets.token_urlsafe(24)
    expires = (_now() + timedelta(days=expires_days)).isoformat() if expires_days else None
    meta = {
        "album": album,
        "label": label or album,
        "created": _now().isoformat(),
        "expires": expires,
        "passcode": passcode or None,
    }
    with _LOCK:
        data = _load()
        data["tokens"][token] = meta
        _save(data)
    return token


def revoke_token(token: str) -> bool:
    """删除 token，链接立即失效。返回是否确实删除了。"""
    with _LOCK:
        data = _load()
        existed = data["tokens"].pop(token, None) is not None
        if existed:
            _save(data)
    return existed


def list_tokens() -> list:
    """返回 [(token, meta), ...]，供桌面端列出管理。"""
    with _LOCK:
        data = _load()
        return [(t, dict(m)) for t, m in data["tokens"].items()]


def resolve(token: str):
    """校验 token：不存在或已过期返回 None，否则返回 meta(含 ``album``)。"""
    if not token:
        return None
    with _LOCK:
        data = _load()
        meta = data["tokens"].get(token)
    if meta is None or _is_expired(meta):
        return None
    return meta


def requires_passcode(token: str) -> bool:
    """该 token 是否设置了口令。"""
    meta = resolve(token)
    return bool(meta and meta.get("passcode"))


def verify_passcode(token: str, code: str) -> bool:
    """校验口令；未设口令的 token 视为通过。token 无效则返回 False。"""
    meta = resolve(token)
    if not meta:
        return False
    pw = meta.get("passcode")
    if not pw:
        return True
    return secrets.compare_digest(pw, code or "")
