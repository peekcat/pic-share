from . import settings

# ====== 0. 全局变量 & 配置 (不变) ======


class ServerState:
    def __init__(self):
        # 优先用上次保存的根目录；首次运行为空字符串（界面引导用户选择）
        self.base_dir = settings.get("base_dir") or ""
        self.preview_subdir = "._preview_ipv6_opt"   # 网格缩略图缓存（小图）
        self.view_subdir = "._view_ipv6_opt"         # 查看大图缓存（按需生成）
        self.marked_subdir = "被标记的照片"
        # 访问 token 存储文件（相对根目录），由桌面端管理、Web 端只读校验
        self.token_file = "._access_tokens.json"
        # 客户选片清单（相对根目录），Web 端读写、桌面端导出时读取
        self.selection_file = "._selections.json"

        # 两档缩略图：网格小图要快、查看大图要清晰
        self.thumb_size = (400, 400)     # 网格缩略图：一屏几十张，够用即可
        self.thumb_quality = 65
        self.view_size = (1600, 1600)    # 查看大图：满屏清晰，按需单张生成
        self.view_quality = 80
        self.port = 5000

        # 定义 RAW 扩展名 (这些文件将被禁止查看原图)
        self.raw_extensions = {
            '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.sr2'
        }

        # 允许扫描的所有扩展名 (RAW + 普通图片)
        self.allowed_extensions = {
                                      '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic'
                                  } | self.raw_extensions  # 合并集合


state = ServerState()
