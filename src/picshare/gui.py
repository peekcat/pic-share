import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from . import status
from . import tokens
from .config import state
from .network import get_ipv6_addresses_v2
from .preview import generator
from .web.app import app


def _ui_font_family():
    """选用支持中文(CJK)的系统字体，避免 macOS 上中文显示为方块。"""
    if sys.platform == "darwin":
        return "PingFang SC"
    if os.name == "nt":
        return "Microsoft YaHei UI"
    return None  # 其它平台用默认字体


# ====== Tkinter GUI（customtkinter 现代深色界面）======
class ServerGUI:
    def __init__(self, root):
        self.root = root
        status.gui_app = self

        fam = _ui_font_family()
        self.font = ctk.CTkFont(family=fam, size=14) if fam else ctk.CTkFont(size=14)
        self.font_bold = ctk.CTkFont(family=fam, size=14, weight="bold") if fam else ctk.CTkFont(size=14, weight="bold")
        self.font_title = ctk.CTkFont(family=fam, size=22, weight="bold") if fam else ctk.CTkFont(size=22, weight="bold")
        self.font_small = ctk.CTkFont(family=fam, size=12) if fam else ctk.CTkFont(size=12)
        self.font_mono = ctk.CTkFont(family="Menlo" if sys.platform == "darwin" else "Consolas", size=13)

        root.title("PicShare · IPv6 相册服务")
        root.geometry("520x600")
        root.minsize(480, 560)

        # 标题
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 6))
        ctk.CTkLabel(header, text="IPv6 相册服务", font=self.font_title).pack(anchor="w")
        ctk.CTkLabel(header, text="极速预览 · 智能缓存 · 安全访问",
                     font=self.font_small, text_color=("gray50", "gray60")).pack(anchor="w", pady=(2, 0))

        card = ctk.CTkFrame(root)
        card.pack(fill="both", expand=True, padx=24, pady=(8, 20))
        card.grid_columnconfigure(0, weight=1)

        # 相册根目录
        ctk.CTkLabel(card, text="📂 相册根目录", font=self.font_bold).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        path_box = ctk.CTkFrame(card, fg_color="transparent")
        path_box.grid(row=1, column=0, sticky="ew", padx=18)
        path_box.grid_columnconfigure(0, weight=1)
        self.path_var = tk.StringVar(value=state.base_dir)
        ctk.CTkEntry(path_box, textvariable=self.path_var, font=self.font).grid(
            row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(path_box, text="选择", width=64, font=self.font, command=self.browse).grid(row=0, column=1)

        # 公网访问地址
        ctk.CTkLabel(card, text="🌐 公网访问地址", font=self.font_bold).grid(
            row=2, column=0, sticky="w", padx=18, pady=(18, 4))
        self.ip_frame = ctk.CTkFrame(card, fg_color=("gray92", "gray17"))
        self.ip_frame.grid(row=3, column=0, sticky="ew", padx=18)
        self.ip_frame.grid_columnconfigure(0, weight=1)

        # 操作按钮
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=18, pady=(16, 0))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="🔄 刷新网络", font=self.font, command=self.refresh).grid(
            row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(btns, text="❓ 帮助", font=self.font, fg_color=("gray75", "gray25"),
                      hover_color=("gray65", "gray35"), command=self.show_help).grid(
            row=0, column=1, sticky="ew", padx=(6, 0))

        ctk.CTkButton(card, text="🔗 相册访问管理", font=self.font_bold,
                      fg_color="#2FA572", hover_color="#268a61", command=self.show_token_manager).grid(
            row=5, column=0, sticky="ew", padx=18, pady=(10, 0))

        # 运行日志（滚动、带时间戳、多行累积）
        log_head = ctk.CTkFrame(card, fg_color="transparent")
        log_head.grid(row=6, column=0, sticky="ew", padx=18, pady=(18, 4))
        log_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_head, text="运行日志", font=self.font_small,
                     text_color=("gray50", "gray55")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_head, text="清空", width=48, height=22, font=self.font_small,
                      fg_color="transparent", text_color=("gray45", "gray60"),
                      hover_color=("gray85", "gray25"), command=self._clear_log).grid(row=0, column=1, sticky="e")

        self.log_box = ctk.CTkTextbox(card, font=self.font_mono, wrap="word", height=150, activate_scrollbars=True)
        self.log_box.grid(row=7, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.log_box.tag_config("warn", foreground="#E6A23C")
        self.log_box.tag_config("ok", foreground="#67C26B")
        self.log_box.configure(state="disabled")
        card.grid_rowconfigure(7, weight=1)

        self._append_log("✅ 服务已启动，等待连接")
        self.refresh()
        threading.Thread(target=app.run,
                         kwargs={"host": "::", "port": state.port, "debug": False,
                                 "use_reloader": False, "threaded": True},
                         daemon=True).start()
        # 延迟启动缩略图预热：先让窗口画完、可交互，避免预热线程池抢 GIL 造成启动卡顿
        self.root.after(2500, lambda: self._start_prewarm(state.base_dir))

    def _start_prewarm(self, base_dir):
        threading.Thread(target=lambda: generator.scan_all(Path(base_dir)), daemon=True).start()

    # ====== 运行日志 ======
    def update_status(self, msg):
        # 可能从后台线程调用，切回主线程更新
        self.root.after(0, lambda: self._append_log(msg))

    def _append_log(self, msg):
        tag = "warn" if any(s in msg for s in ("⚠️", "❌", "🚨")) else "ok"
        line = f"[{datetime.now():%H:%M:%S}] {msg}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line, tag)
        # 限制日志长度，最多保留约 200 行
        total = int(self.log_box.index("end-1c").split(".")[0])
        if total > 200:
            self.log_box.delete("1.0", f"{total - 200}.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def browse(self):
        p = filedialog.askdirectory(initialdir=self.path_var.get())
        if p:
            self.path_var.set(p)
            state.base_dir = p
            self.refresh()
            threading.Thread(target=lambda: generator.scan_all(Path(p)), daemon=True).start()

    def refresh(self):
        # 在后台线程查 IPv6（会 spawn 子进程），查完用 root.after 回主线程刷新 UI，
        # 避免「刷新网络」/ 启动 / 切换目录时阻塞界面造成卡顿。
        def work():
            addrs = get_ipv6_addresses_v2(force_refresh=True)[:5]
            self.root.after(0, lambda: self._render_ips(addrs))

        threading.Thread(target=work, daemon=True).start()

    def _render_ips(self, ipv6_addrs):
        for w in self.ip_frame.winfo_children():
            w.destroy()
        if ipv6_addrs:
            ctk.CTkLabel(self.ip_frame, text="点击任意地址复制完整链接：", font=self.font_small,
                         text_color=("gray45", "gray60"), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=10, pady=(8, 2))
            for i, ip in enumerate(ipv6_addrs, start=1):
                url = f"http://[{ip}]:{state.port}"
                ctk.CTkButton(self.ip_frame, text=url, font=self.font_mono, anchor="w", height=30,
                              fg_color="transparent", text_color=("#1a6fc4", "#5aa9ff"),
                              hover_color=("gray85", "gray25"),
                              command=lambda u=url: self.copy_single_ip(u)).grid(
                    row=i, column=0, sticky="ew", padx=8, pady=2)
            self.update_status(f"🌐 检测到 {len(ipv6_addrs)} 个公网 IPv6 地址")
        else:
            ctk.CTkLabel(self.ip_frame, text="⚠️ 未检测到 IPv6 地址，请检查网络设置。",
                         font=self.font, text_color="#E06C6C", anchor="w").grid(
                row=0, column=0, sticky="ew", padx=10, pady=10)
            self.update_status("⚠️ 网络检测失败")

    def copy_single_ip(self, url):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("已复制", f"已复制地址到剪贴板：\n{url}", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{e}", parent=self.root)

    def show_help(self):
        help_message = """
【使用教程】
1. 设置根目录: 点击“选择”按钮，指定您要共享的大文件夹作为相册根目录。
2. 刷新地址: 确保状态显示“检测到 IPv6 地址”。
3. 生成链接: 点击“相册访问管理”，为某个相册生成专属链接（可选加口令）。
4. 发给客户: 把链接发给客户，对方打开即可浏览、选片。

【文件夹格式要求】
- 根目录: 存放所有相册子文件夹的主目录（如：F:\\共享照片）。
- 相册子文件夹: 根目录下包含图片的子文件夹（如：2025年旅行）。
- 预览缓存: 程序自动创建 `._preview_ipv6_opt` 存放缩略图缓存，请勿删除。
- 收藏照片: 客户标记的照片副本保存在 `被标记的照片` 文件夹内。

【网络安全风险提示】
- 本服务默认使用 IPv6 地址和 5000 端口。访问控制依赖不可枚举的 token 链接，
  可选叠加访问口令与有效期，并可随时撤销链接。
- 重要: 请确保“相册根目录”下只存放您愿意交付的照片。
- 当前为明文 HTTP，敏感场景建议配合 TLS / 隧道部署。
        """
        messagebox.showinfo("帮助与网络风险提示", help_message)

    # ====== 相册访问管理 ======
    def _list_albums(self):
        """列出根目录下可作为相册的子文件夹(跳过系统目录与隐藏目录)。"""
        base = Path(state.base_dir)
        if not base.exists():
            return []
        skip = {state.marked_subdir, state.preview_subdir}
        return sorted(d.name for d in base.iterdir()
                      if d.is_dir() and d.name not in skip and not d.name.startswith("._"))

    def _base_url(self):
        ips = get_ipv6_addresses_v2()
        host = f"[{ips[0]}]" if ips else "localhost"
        return f"http://{host}:{state.port}"

    def show_token_manager(self):
        if not Path(state.base_dir).exists():
            messagebox.showwarning("提示", "请先选择有效的相册根目录。", parent=self.root)
            return

        win = ctk.CTkToplevel(self.root)
        win.title("相册访问管理")
        win.geometry("660x620")
        win.after(200, win.lift)  # 确保浮在主窗之上

        # --- 生成区 ---
        gen = ctk.CTkFrame(win)
        gen.pack(fill="x", padx=18, pady=(18, 8))
        gen.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(gen, text="生成访问链接", font=self.font_bold).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))

        albums = self._list_albums()
        ctk.CTkLabel(gen, text="相册", font=self.font).grid(row=1, column=0, sticky="w", padx=14, pady=6)
        album_var = tk.StringVar(value=albums[0] if albums else "")
        ctk.CTkOptionMenu(gen, variable=album_var, values=albums or ["(无相册)"], font=self.font,
                          dynamic_resizing=False).grid(row=1, column=1, sticky="ew", padx=14, pady=6)

        ctk.CTkLabel(gen, text="有效期", font=self.font).grid(row=2, column=0, sticky="w", padx=14, pady=6)
        expiry_var = tk.StringVar(value="3 天")
        ctk.CTkOptionMenu(gen, variable=expiry_var, values=["3 天", "7 天", "14 天"], font=self.font,
                          dynamic_resizing=False).grid(row=2, column=1, sticky="ew", padx=14, pady=6)

        # 可选口令（默认关闭）
        use_pass_var = tk.BooleanVar(value=False)
        pass_var = tk.StringVar()
        pass_entry = ctk.CTkEntry(gen, textvariable=pass_var, font=self.font,
                                  placeholder_text="留空则随机 4 位")

        def _toggle_pass():
            if use_pass_var.get():
                if not pass_var.get().strip():
                    pass_var.set(tokens.generate_passcode())
                pass_entry.configure(state="normal")
            else:
                pass_var.set("")
                pass_entry.configure(state="disabled")

        ctk.CTkCheckBox(gen, text="加访问口令(可选)", variable=use_pass_var, command=_toggle_pass,
                        font=self.font).grid(row=3, column=0, sticky="w", padx=14, pady=6)
        pass_entry.grid(row=3, column=1, sticky="ew", padx=14, pady=6)
        pass_entry.configure(state="disabled")

        # --- 已生成链接列表 ---
        list_frame = ctk.CTkScrollableFrame(win, label_text="已生成的链接")
        list_frame.pack(fill="both", expand=True, padx=18, pady=8)

        def copy_link(tok):
            url = f"{self._base_url()}/share/{tok}"
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("已复制链接", url, parent=win)

        def copy_pass(pw):
            self.root.clipboard_clear()
            self.root.clipboard_append(pw)
            messagebox.showinfo("已复制口令", f"访问口令：{pw}", parent=win)

        def revoke(tok):
            if messagebox.askyesno("确认撤销", "撤销后该链接将立即失效，确定吗？", parent=win):
                tokens.revoke_token(tok)
                reload_tokens()

        def reload_tokens():
            for w in list_frame.winfo_children():
                w.destroy()
            toks = tokens.list_tokens()
            if not toks:
                ctk.CTkLabel(list_frame, text="暂无链接，请在上方生成。", font=self.font,
                             text_color=("gray50", "gray55")).pack(pady=24)
                return
            for tok, meta in toks:
                row = ctk.CTkFrame(list_frame)
                row.pack(fill="x", pady=4, padx=2)
                name = meta.get("label") or meta.get("album")
                exp = meta.get("expires")
                exp_disp = exp[:10] if exp else "永久"
                pw = meta.get("passcode")
                sub = f"有效期至 {exp_disp}" + (f" · 口令 {pw}" if pw else " · 无口令")
                info = ctk.CTkFrame(row, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True, padx=10, pady=6)
                ctk.CTkLabel(info, text=name, font=self.font_bold, anchor="w").pack(anchor="w")
                ctk.CTkLabel(info, text=sub, font=self.font_small, anchor="w",
                             text_color=("gray45", "gray60")).pack(anchor="w")
                ctk.CTkButton(row, text="复制链接", width=72, font=self.font_small,
                              command=lambda t=tok: copy_link(t)).pack(side="left", padx=3)
                if pw:
                    ctk.CTkButton(row, text="复制口令", width=72, font=self.font_small,
                                  command=lambda p=pw: copy_pass(p)).pack(side="left", padx=3)
                ctk.CTkButton(row, text="撤销", width=52, font=self.font_small,
                              fg_color="#C0392B", hover_color="#a93226",
                              command=lambda t=tok: revoke(t)).pack(side="left", padx=(3, 8))

        def do_generate():
            album = album_var.get().strip()
            if not album or album == "(无相册)":
                messagebox.showwarning("提示", "请先选择相册。", parent=win)
                return
            days = {"3 天": 3, "7 天": 7, "14 天": 14}.get(expiry_var.get(), 3)
            passcode = (pass_var.get().strip() or tokens.generate_passcode()) if use_pass_var.get() else None
            tok = tokens.create_token(album, expires_days=days, passcode=passcode, label=album)
            url = f"{self._base_url()}/share/{tok}"
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            use_pass_var.set(False)
            pass_var.set("")
            pass_entry.configure(state="disabled")
            reload_tokens()
            if passcode:
                messagebox.showinfo(
                    "已生成 · 链接已复制",
                    f"专属链接已复制到剪贴板：\n\n{url}\n\n访问口令：{passcode}\n\n"
                    "请把链接与口令分别发给客户（口令需客户在网页手动输入）。",
                    parent=win)
            else:
                messagebox.showinfo(
                    "已生成 · 链接已复制",
                    f"专属链接已复制到剪贴板：\n\n{url}\n\n凭此链接即可访问，发给客户即可。",
                    parent=win)

        ctk.CTkButton(gen, text="生成并复制链接", font=self.font_bold, command=do_generate).grid(
            row=4, column=1, sticky="e", padx=14, pady=(10, 14))

        reload_tokens()


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    ServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
