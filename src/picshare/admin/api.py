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

from ..config import state, normalize_port
from ..paths import safe_join, safe_album_join
from ..network import get_access_addresses, KIND_PUBLIC, KIND_LAN
from ..server import restart_public_server, ServerStartError
from ..preview import generator
from .. import settings, tokens, selections

_HELP_TEXT = """【使用教程】
1. 设置根目录：点击「选择」，指定存放各相册子文件夹的主目录。
2. 查看地址：点右上角「网络」，确认列出了可用的访问地址。
3. 生成链接：在「相册」里选相册、设有效期（可选加口令），生成并复制。
4. 发给客户：把链接发给客户，对方打开即可浏览、选片。

【两种访问地址，适用范围不同】
- 🌐 公网（IPv6）：客户在任何网络下都能打开，用于远程交付。
  需要宽带已开通 IPv6（多数地区默认开通，未生效可将光猫改为桥接模式），
  路由器上也要启用 IPv6。客户一侧同样需要 IPv6，手机蜂窝数据通常已支持。
- 📶 局域网（IPv4）：只有连着同一个路由器 / 同一个 WiFi 的人能打开，
  适合当面选片。不需要运营商配合，也不用改路由器。

两种地址都没有时，检查网线/WiFi 是否连着；只有局域网地址时，
链接发给不在场的客户是打不开的，别发。

【文件夹格式】
- 根目录：存放所有相册子文件夹的主目录。
- 程序数据：所有缓存与记录都放在根目录下的 ._picshare 文件夹，请勿手动改动。
- 收藏照片：客户标记的照片副本保存在「被标记的照片」文件夹内。

【网络安全提示】
- 访问控制依赖不可枚举的 token 链接，可叠加访问口令与有效期，并可随时撤销。
- 请确保根目录下只存放愿意交付的照片。当前为明文 HTTP，敏感场景建议配合 TLS / 隧道。

【注意事项】
- 需在系统防火墙及路由器上放行监听端口（默认 5000），否则客户无法连接。
- 改端口后，之前发出去的链接里的端口号就过时了，需要重新复制发给客户；
  口令、有效期与客户已选的照片都不受影响。
"""


class Api:
    def __init__(self):
        self._logs = []
        self._log_lock = threading.Lock()
        self._window = None
        self._photo_count_cache = {}  # 相册张数缓存（照片极少变动，切目录时清空）
        self._server_error = None     # 对外服务启动失败的说明，供页面顶部横幅展示

    def set_window(self, window):
        self._window = window

    # ====== 运行日志 ======
    def log(self, msg):
        with self._log_lock:
            self._logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg})
            del self._logs[:-200]  # 最多保留 200 条

    def get_logs(self):
        with self._log_lock:
            return list(self._logs)

    def clear_logs(self):
        with self._log_lock:
            self._logs.clear()
        return True

    # ====== 根目录 ======
    def set_server_error(self, msg):
        """记录对外服务启动失败的原因，由页面顶部横幅展示（启动时调用一次）。"""
        self._server_error = msg

    def get_state(self):
        return {
            "base_dir": state.base_dir,
            "base_dir_exists": bool(state.base_dir) and Path(state.base_dir).exists(),
            "port": state.port,
            # 非空即代表对外服务没起来：运行日志面板默认折叠，必须在主界面明示
            "server_error": self._server_error or "",
            # 首次使用向导是否已走完（持久化在用户级设置里，换根目录不受影响）
            "onboarded": bool(settings.get("onboarded")),
        }

    def set_port(self, port):
        """改服务端口并立即在新端口上重启对外服务，成功后持久化。

        token 与端口无关，改端口不会让任何链接失效——只是链接 URL 里的端口号变了，
        摄影师重新复制发一次即可（_base_urls() 实时读 state.port，会自动重新生成）。
        """
        try:
            port = normalize_port(port)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        if port == state.port and not self._server_error:
            return {"ok": True, "port": port, "unchanged": True}

        try:
            restart_public_server(port)   # 新端口绑不上则抛错，旧服务继续跑
        except ServerStartError as e:
            return {"ok": False, "error": f"{e}请换一个端口。"}

        state.port = port
        settings.set_value("port", port)
        # 启动时端口被占用的用户正是靠改端口自救，成功后横幅必须撤掉
        self._server_error = None
        self.log(f"🔌 服务端口已改为 {port}，请把链接重新复制发给客户")
        return {"ok": True, "port": port}

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
    @staticmethod
    def _url_for(addr):
        host = f"[{addr['ip']}]" if addr["kind"] == KIND_PUBLIC else addr["ip"]
        return f"http://{host}:{state.port}"

    def get_addresses(self, force_refresh=False):
        """客户可用来访问本机的地址，公网在前，每条带拼好的 URL。

        两种 kind 的可用范围差别极大（公网 = 任何地方；局域网 = 同一个网络），
        界面必须分开讲，所以这里原样带出 kind，不在后端合并成一个"最佳地址"。
        """
        addrs = [dict(a, url=self._url_for(a))
                 for a in get_access_addresses(force_refresh=force_refresh)[:8]]
        n_pub = sum(1 for a in addrs if a["kind"] == KIND_PUBLIC)
        n_lan = len(addrs) - n_pub
        if n_pub:
            self.log(f"🌐 检测到 {n_pub} 个公网 IPv6 地址" + (f"、{n_lan} 个局域网地址" if n_lan else ""))
        elif n_lan:
            self.log(f"📶 检测到 {n_lan} 个局域网地址；未检测到公网 IPv6，链接只能在同一网络内打开")
        else:
            self.log("⚠️ 未检测到任何可用地址，请检查网络连接")
        return addrs

    def _base_urls(self):
        """生成分享链接用的地址前缀列表，公网优先。

        一个 token 配多个 URL：token 只绑相册/有效期/口令，与用什么地址访问无关。
        一个地址都没有时回落到 localhost——只有本机能打开，但至少摄影师自己能验证。
        """
        addrs = get_access_addresses()
        if not addrs:
            return [{"kind": KIND_LAN, "url": f"http://localhost:{state.port}"}]
        return [{"kind": a["kind"], "url": self._url_for(a)} for a in addrs]

    # ====== 相册 / token ======
    def _count_photos(self, album_dir: Path) -> int:
        name = album_dir.name
        if name in self._photo_count_cache:
            return self._photo_count_cache[name]
        n = 0
        for f in album_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in state.allowed_extensions:
                if any(d in f.parts for d in state.system_subdirs):
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

    def get_albums(self, force_refresh=False):
        """仪表盘数据：每个相册的张数、已选数、状态徽章及其全部分享链接。

        force_refresh=True 时丢弃张数缓存重新点数（供「🔄 刷新相册」按钮使用）——
        摄影师往相册里加了照片后，正是靠这个按钮看到新张数。其余调用点(初始加载、
        切目录、建/撤链接后)不传参、继续吃缓存，那些动作本就不改变照片数量。
        """
        if force_refresh:
            self._photo_count_cache.clear()
        if not state.base_dir:
            return {"base_dir_ok": False, "reason": "unset", "albums": []}
        base = Path(state.base_dir)
        if not base.exists():
            return {"base_dir_ok": False, "reason": "missing", "albums": []}

        # 链接按相册归集
        base_urls = self._base_urls()
        links_by_album = {}
        for tok, meta in tokens.list_tokens():
            st = self._link_status(meta)
            links_by_album.setdefault(meta.get("album"), []).append({
                "token": tok,
                "expires": (meta.get("expires") or "")[:10],
                "passcode": meta.get("passcode") or "",
                "urls": [{"kind": b["kind"], "url": f"{b['url']}/share/{tok}"}
                         for b in base_urls],
                "expired": st["expired"],
                "days_left": st["days_left"],
            })

        skip = set(state.system_subdirs)
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
            # 清单里万一存过 ../ 之类的历史脏条目，这里会返回 None 被跳过
            src = safe_album_join(state.base_dir, album, rel)
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
                src = safe_album_join(state.base_dir, album, rel)  # 仅清理确属该相册的副本
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
        urls = [{"kind": b["kind"], "url": f"{b['url']}/share/{tok}"} for b in self._base_urls()]
        self.log(f"🔗 已生成链接：{album}" + (f"（口令 {passcode}）" if passcode else ""))
        return {"ok": True, "token": tok, "urls": urls, "passcode": passcode or ""}

    def revoke_token(self, token):
        ok = tokens.revoke_token(token)
        if ok:
            self.log("🗑️ 已撤销一条链接")
        return ok

    # ====== 其它 ======
    def finish_onboarding(self):
        """记下首次引导已走完。持久化在用户级设置里，换根目录/换端口都不影响。"""
        settings.set_value("onboarded", True)
        return True

    def help_text(self):
        return _HELP_TEXT

    def _start_prewarm(self, base_dir):
        threading.Thread(target=lambda: generator.scan_all(Path(base_dir)), daemon=True).start()
