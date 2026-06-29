import urllib.parse
from pathlib import Path

# ====== 1. 核心逻辑工具 (不变) ======


def safe_join(base_path: str, *paths: str) -> Path:
    try:
        base = Path(base_path).resolve()
        decoded_paths = [urllib.parse.unquote(p) for p in paths]
        final_path = base.joinpath(*decoded_paths).resolve()
        if base in final_path.parents or base == final_path:
            return final_path
        return None
    except Exception:
        return None
