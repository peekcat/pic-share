import logging

from . import settings

# ====== 0. 全局变量 & 配置 (不变) ======


class ServerState:
    def __init__(self):
        # 优先用上次保存的根目录，没有则用默认值
        self.base_dir = settings.get("base_dir") or r"F:\共享照片"
        self.preview_subdir = "._preview_ipv6_opt"
        self.marked_subdir = "被标记的照片"
        # 访问 token 存储文件（相对根目录），由桌面端管理、Web 端只读校验
        self.token_file = "._access_tokens.json"

        # [修改] 提高分辨率到 640x640
        self.thumb_size = (640, 640)
        self.thumb_quality = 60
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)
