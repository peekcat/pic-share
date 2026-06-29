import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from . import status
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


def main():
    root = tk.Tk()
    ServerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
