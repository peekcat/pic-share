from pathlib import Path

# ====== 1. 核心逻辑工具 ======


def safe_join(base_path: str, *paths: str) -> Path | None:
    """把 paths 拼到 base_path 之下，逃出 base_path 则返回 None。

    ⚠️ 只保证「落在 base_path 之内」，不保证落在更深的某一层内。因此
    ``safe_join(root, album, filename)`` 里客户可控的 filename 用 ``../``
    仍能横向跨到同根下的**别的相册**——凡是客户可控的路径一律走
    ``safe_album_join()``，不要直接用本函数拼相册内的文件名。
    """
    try:
        base = Path(base_path).resolve()
        final_path = base.joinpath(*paths).resolve()
        if base in final_path.parents or base == final_path:
            return final_path
        return None
    except Exception:
        return None


def safe_album_join(root: str, album: str, *paths: str) -> Path | None:
    """把客户可控的相对路径夹在 ``<root>/<album>`` 之内，逃出则返回 None。

    album 来自 token（服务端推导，可信）先夹进 root；再以**相册目录**为基准夹一次
    客户可控部分，从而挡住跨相册穿越。root 既可以是照片根目录，也可以是某一级
    缓存目录（preview / view / hd）——缓存侧同样需要，否则穿越请求会在别的相册的
    缓存目录里落文件。

    不传 paths 时即返回相册根目录本身。
    """
    album_root = safe_join(root, album)
    if album_root is None:
        return None
    return safe_join(str(album_root), *paths)
