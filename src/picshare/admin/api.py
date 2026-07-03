"""暴露给管理网页(pywebview)的 Python API。

网页通过 ``window.pywebview.api.<方法>()`` 调用，返回值以 Promise 形式回到 JS。
所有方法都在 pywebview 的处理线程中执行（非 GUI 主线程），因此阻塞调用
（如查 IPv6、生成 token）不会冻结界面。
"""

import os
import sys
import base64
import shutil
import threading
import subprocess
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path

import webview
import qrcode

from ..config import state
from ..paths import safe_join
from ..network import get_ipv6_addresses_v2
from ..preview import generator
from .. import settings, tokens, selections

_HELP_TEXT = """【使用教程】
1. 设置根目录：点击「选择」，指定存放各相册子文件夹的主目录。
2. 刷新地址：确认显示「检测到 IPv6 地址」。
3. 生成链接：在「相册访问管理」选相册、设有效期（可选加口令），生成并复制。
4. 发给客户：把链接发给客户，对方打开即可浏览、选片。

【文件夹格式】
- 根目录：存放所有相册子文件夹的主目录。
- 预览缓存：程序自动创建 ._preview_ipv6_opt，请勿删除。
- 收藏照片：客户标记的照片副本保存在「被标记的照片」文件夹内。

【网络安全提示】
- 访问控制依赖不可枚举的 token 链接，可叠加访问口令与有效期，并可随时撤销。
- 请确保根目录下只存放愿意交付的照片。当前为明文 HTTP，敏感场景建议配合 TLS / 隧道。

【注意事项】
- 本程序仅支持 IPv6 网络访问，IPv4 环境下无法使用。
- 需向宽带运营商（ISP）开通 IPv6 服务：多数地区已默认开通，如未生效，请将光猫改为桥接模式。
- 需在路由器上启用 IPv6，并确认分配到的公网 IPv6 地址可从外部访问。
- 需在系统防火墙及路由器上放行监听端口（默认 5000），否则客户无法连接。
- 客户所在网络同样需支持 IPv6，否则无法打开链接；手机蜂窝数据通常已支持，可直接访问。
"""


class Api:
    def __init__(self):
        self._logs = []
        self._log_lock = threading.Lock()
        self._window = None
        self._photo_count_cache = {}  # 相册张数缓存（照片极少变动，切目录时清空）

    def set_window(self, window):
        self._window = window

    # ====== 运行日志 ======
    def log(self, msg):
        with self._log_lock:
            self._logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg})
            del self._logs[:-200]  # 最多保留 200 条

    # status.gui_app 适配：后端模块通过 update_global_status -> update_status 上报
    def update_status(self, msg):
        self.log(msg)

    def get_logs(self):
        with self._log_lock:
            return list(self._logs)

    def clear_logs(self):
        with self._log_lock:
            self._logs.clear()
        return True

    # ====== 根目录 ======
    def get_state(self):
        return {
            "base_dir": state.base_dir,
            "base_dir_exists": bool(state.base_dir) and Path(state.base_dir).exists(),
            "port": state.port,
        }

    def choose_folder(self):
        if not self._window:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return None
        path = result[0]
        state.base_dir = path
        settings.set_value("base_dir", path)  # 记住选择，下次启动自动恢复
        self._photo_count_cache.clear()
        self.log(f"📂 已选择根目录：{path}")
        self._start_prewarm(path)
        return path

    # ====== 网络 ======
    def get_ipv6(self, force_refresh=False):
        addrs = get_ipv6_addresses_v2(force_refresh=force_refresh)[:5]
        if addrs:
            self.log(f"🌐 检测到 {len(addrs)} 个公网 IPv6 地址")
        else:
            self.log("⚠️ 未检测到 IPv6 地址，请检查网络设置")
        return [{"ip": ip, "url": f"http://[{ip}]:{state.port}"} for ip in addrs]

    def _base_url(self):
        ips = get_ipv6_addresses_v2()
        host = f"[{ips[0]}]" if ips else "localhost"
        return f"http://{host}:{state.port}"

    # ====== 相册 / token ======
    def _count_photos(self, album_dir: Path) -> int:
        name = album_dir.name
        if name in self._photo_count_cache:
            return self._photo_count_cache[name]
        n = 0
        for f in album_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in state.allowed_extensions:
                if any(d in f.parts for d in
                       (state.marked_subdir, state.preview_subdir, state.view_subdir)):
                    continue
                n += 1
        self._photo_count_cache[name] = n
        return n

    def _count_marked(self, album: str) -> int:
        return selections.count_selected(album)

    @staticmethod
    def _link_status(meta: dict) -> dict:
        exp = meta.get("expires")
        if not exp:
            return {"expired": False, "days_left": None}
        try:
            dt = datetime.fromisoformat(exp)
            now = datetime.now(timezone.utc)
            return {"expired": now >= dt, "days_left": max(0, (dt - now).days)}
        except Exception:
            return {"expired": False, "days_left": None}

    def get_albums(self):
        """仪表盘数据：每个相册的张数、已选数、状态徽章及其全部分享链接。"""
        if not state.base_dir:
            return {"base_dir_ok": False, "reason": "unset", "albums": []}
        base = Path(state.base_dir)
        if not base.exists():
            return {"base_dir_ok": False, "reason": "missing", "albums": []}

        # 链接按相册归集
        base_url = self._base_url()
        links_by_album = {}
        for tok, meta in tokens.list_tokens():
            st = self._link_status(meta)
            links_by_album.setdefault(meta.get("album"), []).append({
                "token": tok,
                "expires": (meta.get("expires") or "")[:10],
                "passcode": meta.get("passcode") or "",
                "url": f"{base_url}/share/{tok}",
                "expired": st["expired"],
                "days_left": st["days_left"],
            })

        skip = {state.marked_subdir, state.preview_subdir, state.view_subdir}
        albums = []
        for d in sorted(base.iterdir(), key=lambda p: p.name):
            if not d.is_dir() or d.name in skip or d.name.startswith("._"):
                continue
            links = links_by_album.get(d.name, [])
            active = [l for l in links if not l["expired"]]
            if active:
                badge = "active"
                days_left = min(l["days_left"] for l in active if l["days_left"] is not None) \
                    if any(l["days_left"] is not None for l in active) else None
            elif links:
                badge = "expired"
                days_left = None
            else:
                badge = "none"
                days_left = None
            albums.append({
                "name": d.name,
                "photos": self._count_photos(d),
                "marked": self._count_marked(d.name),
                "links": links,
                "badge": badge,
                "days_left": days_left,
            })
        return {"base_dir_ok": True, "albums": albums}

    def make_qr(self, text):
        """把分享链接编码成二维码 PNG 的 data URI（不涉及任何照片内容）。"""
        img = qrcode.make(text, border=2)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    def _sync_marked_folder(self, album: str, dest: Path) -> tuple[int, int]:
        """把 dest 内容对齐到选片清单：补齐已选原图，清理已取消的本相册副本。

        只删除「同时存在于源相册」的残留副本(即我们导出来的)，绝不动摄影师
        自己手工放进该文件夹的其它文件。返回 (新增数, 删除数)。
        """
        selected = selections.list_selected(album)
        selected_set = set(selected)

        copied = 0
        for rel in selected:
            src = safe_join(state.base_dir, album, rel)
            dst = safe_join(str(dest), rel)
            if not src or not dst or not src.exists():
                continue
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1

        removed = 0
        if dest.exists():
            for f in dest.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    rel = f.relative_to(dest).as_posix()
                except ValueError:
                    continue
                if rel in selected_set:
                    continue
                src = safe_join(state.base_dir, album, rel)  # 仅清理确属该相册的副本
                if src and src.exists():
                    try:
                        f.unlink()
                        removed += 1
                    except Exception:
                        pass
        return copied, removed

    def open_marked_folder(self, album):
        """按选片清单导出原图到「被标记的照片/<相册>」，然后在文件管理器中打开。"""
        base = Path(state.base_dir)
        dest = base / state.marked_subdir / album
        try:
            copied, removed = self._sync_marked_folder(album, dest)
            if copied or removed:
                self.log(f"📦 已导出选片：{album}（新增 {copied}，清理 {removed}）")
        except Exception:
            self.log(f"⚠️ 导出选片时出错：{album}")

        candidates = [dest, base / state.marked_subdir, base]
        folder = next((p for p in candidates if p.exists()), None)
        if folder is None:
            return False
        try:
            if os.name == "nt":
                os.startfile(str(folder))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
            return True
        except Exception:
            return False

    def generate_passcode(self):
        return tokens.generate_passcode()

    def create_token(self, album, days, passcode):
        album = (album or "").strip()
        if not album:
            return {"ok": False, "error": "请先选择相册。"}
        passcode = (passcode or "").strip() or None
        tok = tokens.create_token(album, expires_days=int(days), passcode=passcode, label=album)
        url = f"{self._base_url()}/share/{tok}"
        self.log(f"🔗 已生成链接：{album}" + (f"（口令 {passcode}）" if passcode else ""))
        return {"ok": True, "token": tok, "url": url, "passcode": passcode or ""}

    def revoke_token(self, token):
        ok = tokens.revoke_token(token)
        if ok:
            self.log("🗑️ 已撤销一条链接")
        return ok

    # ====== 其它 ======
    def help_text(self):
        return _HELP_TEXT

    def _start_prewarm(self, base_dir):
        threading.Thread(target=lambda: generator.scan_all(Path(base_dir)), daemon=True).start()
