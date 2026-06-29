import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from . import status
from . import tokens
from .config import state
from .network import get_ipv6_addresses_v2
from .preview import generator
from .web.app import app


# ====== 4. Tkinter GUI (新增帮助按钮) ======
class ServerGUI:
    def __init__(self, root):
        self.root = root
        status.gui_app = self
        self.timer = None

        self.style = {
            'bg': '#1E1E1E',
            'panel': '#252526',
            'input': '#333333',
            'fg': '#CCCCCC',
            'text': '#FFFFFF',
            'accent': '#3794FF',
            'success': '#4EC9B0'
        }

        root.title("IPv6 Photo Server")
        root.geometry("480x560")
        root.configure(bg=self.style['bg'])

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 10), borderwidth=0)

        header = tk.Frame(root, bg=self.style['bg'], pady=25)
        header.pack(fill='x')
        tk.Label(header, text="IPv6 相册服务", bg=self.style['bg'], fg=self.style['text'],
                 font=("Microsoft YaHei UI", 18, "bold")).pack()
        tk.Label(header, text="极速预览 · 智能缓存 · 安全访问", bg=self.style['bg'], fg=self.style['accent'],
                 font=("Microsoft YaHei UI", 10)).pack(pady=(5, 0))

        card = tk.Frame(root, bg=self.style['panel'], padx=25, pady=25)
        card.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        self.create_label(card, "📂 相册根目录")
        path_box = tk.Frame(card, bg=self.style['panel'])
        path_box.pack(fill='x', pady=(5, 20))

        self.path_var = tk.StringVar(value=state.base_dir)
        e = tk.Entry(path_box, textvariable=self.path_var, bg=self.style['input'], fg='white',
                     relief='flat', font=("Segoe UI", 10))
        e.pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 10))

        btn_browse = tk.Button(path_box, text="选择", command=self.browse,
                               bg=self.style['input'], fg='white', relief='flat', font=('Segoe UI', 9))
        btn_browse.pack(side='right', ipady=4, padx=0)

        self.create_label(card, "🌐 公网访问地址")
        self.ip_frame = tk.Frame(card, bg=self.style['panel'])
        self.ip_frame.pack(fill='x', pady=(5, 10))

        btn_frame = tk.Frame(card, bg=self.style['panel'])
        btn_frame.pack(fill='x', pady=10)

        # 刷新按钮
        tk.Button(btn_frame, text="🔄 刷新网络状态", command=self.refresh,
                  bg=self.style['accent'], fg='white', relief='flat', font=("Microsoft YaHei UI", 10, "bold")
                  ).pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 5))

        # 新增：帮助与提示按钮
        tk.Button(btn_frame, text="❓ 帮助与提示", command=self.show_help,
                  bg=self.style['input'], fg='white', relief='flat', font=("Microsoft YaHei UI", 10)
                  ).pack(side='left', fill='x', expand=True, ipady=6, padx=(5, 0))

        # 相册访问管理：生成 / 撤销专属访问链接
        tk.Button(card, text="🔗 相册访问管理（生成 / 撤销专属链接）", command=self.show_token_manager,
                  bg=self.style['success'], fg='#1E1E1E', relief='flat', font=("Microsoft YaHei UI", 10, "bold")
                  ).pack(fill='x', pady=(0, 10), ipady=6)

        tk.Label(card, text="运行日志", bg=self.style['panel'], fg='#666', font=("Segoe UI", 9)).pack(anchor='w',
                                                                                                      pady=(15, 5))
        self.status_var = tk.StringVar(value="正在初始化...")
        self.status_lbl = tk.Label(card, textvariable=self.status_var, bg=self.style['input'], fg=self.style['success'],
                                   anchor='w', padx=10, font=("Segoe UI", 9))
        self.status_lbl.pack(fill='x', ipady=8)

        self.refresh()
        threading.Thread(target=app.run, kwargs={'host': '::', 'port': 5000, 'debug': False, 'use_reloader': False},
                         daemon=True).start()
        threading.Thread(target=lambda: generator.scan_all(Path(state.base_dir)), daemon=True).start()

    def create_label(self, parent, text):
        tk.Label(parent, text=text, bg=self.style['panel'], fg=self.style['fg'],
                 font=("Microsoft YaHei UI", 10, "bold")).pack(anchor='w')

    def update_status(self, msg):
        self.root.after(0, lambda: self._upd(msg))

    def _upd(self, msg):
        if self.timer: self.root.after_cancel(self.timer)
        self.status_var.set(msg)
        self.status_lbl.config(fg=self.style['success'])
        self.timer = self.root.after(5000, lambda: [
            self.status_var.set("✅ 服务运行中 (等待连接)"),
            self.status_lbl.config(fg='#888')
        ])

    def browse(self):
        p = filedialog.askdirectory(initialdir=self.path_var.get())
        if p:
            self.path_var.set(p)
            state.base_dir = p
            self.refresh()
            threading.Thread(target=lambda: generator.scan_all(Path(p)), daemon=True).start()

    def copy_ip(self, event):
        try:
            txt = self.ip_text.get("1.0", tk.END).strip()
            url = txt.split('\n')[0].split(' ')[-1] if 'http' in txt else txt
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("提示", "地址已复制到剪贴板")
        except:
            pass

    def refresh(self):
        ipv6_addrs = get_ipv6_addresses_v2()[:5]  # 最多取前5个
        # 清空旧的地址显示
        for widget in self.ip_frame.winfo_children():
            widget.destroy()

        if ipv6_addrs:
            tk.Label(self.ip_frame, text="点击以下任意地址复制完整链接：", bg=self.style['panel'],
                     fg=self.style['fg'], font=("Segoe UI", 9)).pack(anchor='w', pady=(0, 5))
            for ip in ipv6_addrs:
                url = f"http://[{ip}]:{state.port}"
                lbl = tk.Label(
                    self.ip_frame,
                    text=url,
                    bg=self.style['input'],
                    fg=self.style['accent'],
                    relief='flat',
                    font=("Consolas", 10),
                    padx=10,
                    pady=5,
                    cursor="hand2",  # 手型光标
                    anchor="w"
                )
                lbl.pack(fill='x', pady=2)
                # 绑定点击复制事件，使用 lambda 闭包捕获当前 ip
                lbl.bind("<Button-1>", lambda e, u=url: self.copy_single_ip(u))
            self.update_status(f"🌐 检测到 {len(ipv6_addrs)} 个公网 IPv6 地址")
        else:
            lbl = tk.Label(
                self.ip_frame,
                text="⚠️ 未检测到 IPv6 地址，请检查网络设置。",
                bg=self.style['input'],
                fg='#FF6B6B',
                font=("Segoe UI", 10),
                padx=10,
                pady=8,
                anchor="w"
            )
            lbl.pack(fill='x')
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
2. 刷新地址: 确保底部状态显示“检测到 IPv6 地址”。
3. 访问相册: 复制上方显示的 `http://[...]` 地址，在手机或电脑浏览器中访问。
4. 输入相册名: 在网页输入框中输入根目录下的子文件夹名（即相册名）即可访问。

【文件夹格式要求】
- 根目录: 存放所有相册子文件夹的主目录（如：F:\\共享照片）。
- 相册子文件夹: 根目录下包含图片的子文件夹（如：F:\\共享照片\\2025年旅行）。
- 预览缓存: 程序会自动创建 `._preview_ipv6_opt` 文件夹用于存放缩略图缓存，请勿删除。
- 收藏照片: 收藏的照片副本会保存在 `被标记的照片` 文件夹内。

【网络安全风险提示】
- 本服务默认使用 IPv6 地址和 5000 端口。如果您的网络允许公网访问（例如，许多家庭宽带自动支持 IPv6 公网），则任何知道您地址的人都可以访问。
- 重要: 请确保您选择的“相册根目录”下只存放您想要共享的照片。
- 本程序目前没有访问密码，安全性依赖于 IPv6 地址的随机性和复杂性。请谨慎分享您的地址。
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
                      if d.is_dir() and d.name not in skip and not d.name.startswith('._'))

    def _base_url(self):
        ips = get_ipv6_addresses_v2()
        host = f"[{ips[0]}]" if ips else "localhost"
        return f"http://{host}:{state.port}"

    def show_token_manager(self):
        if not Path(state.base_dir).exists():
            messagebox.showwarning("提示", "请先选择有效的相册根目录。", parent=self.root)
            return

        win = tk.Toplevel(self.root)
        win.title("相册访问管理")
        win.geometry("640x560")
        win.configure(bg=self.style['bg'])

        # --- 生成区 ---
        gen = tk.LabelFrame(win, text=" 生成访问链接 ", bg=self.style['panel'], fg=self.style['fg'],
                            font=("Microsoft YaHei UI", 10, "bold"), padx=15, pady=15, bd=0)
        gen.pack(fill='x', padx=15, pady=(15, 8))

        tk.Label(gen, text="相册", bg=self.style['panel'], fg=self.style['fg']).grid(row=0, column=0, sticky='w', pady=4)
        album_var = tk.StringVar()
        album_cb = ttk.Combobox(gen, textvariable=album_var, values=self._list_albums(), state='readonly', width=30)
        album_cb.grid(row=0, column=1, sticky='w', padx=8, pady=4)
        if album_cb['values']:
            album_cb.current(0)

        tk.Label(gen, text="有效期", bg=self.style['panel'], fg=self.style['fg']).grid(row=1, column=0, sticky='w', pady=4)
        expiry_var = tk.StringVar(value="3 天")
        ttk.Combobox(gen, textvariable=expiry_var, values=["3 天", "7 天", "14 天"],
                     state='readonly', width=30).grid(row=1, column=1, sticky='w', padx=8, pady=4)

        # 口令为可选项，默认关闭（token 已是强随机，多数场景一条链接即可）
        use_pass_var = tk.BooleanVar(value=False)
        pass_var = tk.StringVar()
        pass_entry = tk.Entry(gen, textvariable=pass_var, bg=self.style['input'], fg='white',
                              relief='flat', width=32, disabledbackground=self.style['panel'])

        def _toggle_pass():
            if use_pass_var.get():
                if not pass_var.get().strip():
                    pass_var.set(tokens.generate_passcode())  # 勾选时自动给一个随机 4 位
                pass_entry.config(state='normal')
            else:
                pass_var.set('')
                pass_entry.config(state='disabled')

        tk.Checkbutton(gen, text="加访问口令(可选)", variable=use_pass_var, command=_toggle_pass,
                       bg=self.style['panel'], fg=self.style['fg'], selectcolor=self.style['input'],
                       activebackground=self.style['panel'], activeforeground=self.style['fg'],
                       highlightthickness=0, bd=0).grid(row=2, column=0, sticky='w', pady=4)
        pass_entry.grid(row=2, column=1, sticky='w', padx=8, pady=4, ipady=3)
        pass_entry.config(state='disabled')  # 默认关闭

        # --- 已生成 token 列表 ---
        list_frame = tk.Frame(win, bg=self.style['bg'])
        list_frame.pack(fill='both', expand=True, padx=15, pady=8)
        cols = ("album", "expires", "passcode")
        tree = ttk.Treeview(list_frame, columns=cols, show='headings', height=10)
        tree.heading("album", text="相册")
        tree.heading("expires", text="有效期至")
        tree.heading("passcode", text="口令")
        tree.column("album", width=280)
        tree.column("expires", width=140)
        tree.column("passcode", width=90, anchor='center')
        tree.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(list_frame, orient='vertical', command=tree.yview)
        sb.pack(side='right', fill='y')
        tree.configure(yscrollcommand=sb.set)

        token_by_item = {}

        def reload_tokens():
            tree.delete(*tree.get_children())
            token_by_item.clear()
            for tok, meta in tokens.list_tokens():
                exp = meta.get('expires')
                exp_disp = exp[:10] if exp else "永久"
                pc = meta.get('passcode') or "—"
                item = tree.insert('', 'end', values=(meta.get('label') or meta.get('album'), exp_disp, pc))
                token_by_item[item] = tok

        def do_generate():
            album = album_var.get().strip()
            if not album:
                messagebox.showwarning("提示", "请先选择相册。", parent=win)
                return
            days_map = {"3 天": 3, "7 天": 7, "14 天": 14}
            days = days_map.get(expiry_var.get(), 3)  # 默认 3 天
            # 仅在勾选「加访问口令」时设口令；默认 token-only，一条链接即可
            passcode = (pass_var.get().strip() or tokens.generate_passcode()) if use_pass_var.get() else None
            tok = tokens.create_token(album, expires_days=days, passcode=passcode, label=album)
            url = f"{self._base_url()}/share/{tok}"
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            # 复位口令控件
            use_pass_var.set(False)
            pass_var.set('')
            pass_entry.config(state='disabled')
            reload_tokens()
            if passcode:
                messagebox.showinfo(
                    "已生成 · 链接已复制",
                    f"专属链接已复制到剪贴板：\n\n{url}\n\n访问口令：{passcode}\n\n"
                    "请把链接与口令分别发给客户（口令需客户在网页手动输入）。\n"
                    "可在下方列表用「复制链接 / 复制口令」按钮随时重新复制。",
                    parent=win)
            else:
                messagebox.showinfo(
                    "已生成 · 链接已复制",
                    f"专属链接已复制到剪贴板：\n\n{url}\n\n"
                    "凭此链接即可访问，把它发给客户即可。",
                    parent=win)

        def _selected_token(self_meta=False):
            sel = tree.selection()
            if not sel:
                return (None, None) if self_meta else None
            tok = token_by_item.get(sel[0])
            if not self_meta:
                return tok
            meta = next((m for t, m in tokens.list_tokens() if t == tok), None)
            return tok, meta

        def do_copy():
            tok = _selected_token()
            if not tok:
                return
            url = f"{self._base_url()}/share/{tok}"
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("已复制链接", url, parent=win)

        def do_copy_pass():
            tok, meta = _selected_token(self_meta=True)
            if not tok:
                return
            pw = (meta or {}).get('passcode')
            if not pw:
                messagebox.showinfo("提示", "该链接未设口令。", parent=win)
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(pw)
            messagebox.showinfo("已复制口令", f"访问口令：{pw}", parent=win)

        def do_revoke():
            tok = _selected_token()
            if not tok:
                return
            if messagebox.askyesno("确认撤销", "撤销后该链接将立即失效，确定吗？", parent=win):
                tokens.revoke_token(tok)
                reload_tokens()

        tk.Button(gen, text="生成并复制链接", command=do_generate,
                  bg=self.style['accent'], fg='white', relief='flat', font=("Microsoft YaHei UI", 10, "bold")
                  ).grid(row=3, column=1, sticky='w', padx=8, pady=(10, 0), ipady=4)

        ops = tk.Frame(win, bg=self.style['bg'])
        ops.pack(fill='x', padx=15, pady=(0, 15))
        tk.Button(ops, text="复制链接", command=do_copy, bg=self.style['input'], fg='white',
                  relief='flat').pack(side='left', ipady=4, padx=(0, 8))
        tk.Button(ops, text="复制口令", command=do_copy_pass, bg=self.style['input'], fg='white',
                  relief='flat').pack(side='left', ipady=4, padx=(0, 8))
        tk.Button(ops, text="撤销选中", command=do_revoke, bg='#7a2e2e', fg='white',
                  relief='flat').pack(side='left', ipady=4)

        reload_tokens()


def main():
    root = tk.Tk()
    ServerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
