"""暴露给管理网页(pywebview)的 Python API。

网页通过 ``window.pywebview.api.<方法>()`` 调用，返回值以 Promise 形式回到 JS。
所有方法都在 pywebview 的处理线程中执行（非 GUI 主线程），因此阻塞调用
（如查 IPv6、生成 token）不会冻结界面。
"""

import threading
from datetime import datetime
from pathlib import Path

import webview

from ..config import state
from ..network import get_ipv6_addresses_v2
from ..preview import generator
from .. import settings, tokens

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
- 请确保根目录下只存放愿意交付的照片。当前为明文 HTTP，敏感场景建议配合 TLS / 隧道。"""


class Api:
    def __init__(self):
        self._logs = []
        self._log_lock = threading.Lock()
        self._window = None

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
            "base_dir_exists": Path(state.base_dir).exists(),
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
    def list_albums(self):
        base = Path(state.base_dir)
        if not base.exists():
            return []
        skip = {state.marked_subdir, state.preview_subdir}
        return sorted(d.name for d in base.iterdir()
                      if d.is_dir() and d.name not in skip and not d.name.startswith("._"))

    def list_tokens(self):
        base_url = self._base_url()
        out = []
        for tok, meta in tokens.list_tokens():
            out.append({
                "token": tok,
                "label": meta.get("label") or meta.get("album"),
                "album": meta.get("album"),
                "expires": (meta.get("expires") or "")[:10],
                "passcode": meta.get("passcode") or "",
                "url": f"{base_url}/share/{tok}",
            })
        return out

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
