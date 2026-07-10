from . import settings

# ====== 0. 全局变量 & 配置 (不变) ======


class ServerState:
    def __init__(self):
        # 优先用上次保存的根目录；首次运行为空字符串（界面引导用户选择）
        self.base_dir = settings.get("base_dir") or ""
        # 所有缓存与元数据统一收进根目录下这一个隐藏目录，避免污染摄影师的照片目录
        self.data_dir = "._picshare"
        self.preview_subdir = f"{self.data_dir}/preview"   # 网格缩略图缓存（小图）
        self.view_subdir = f"{self.data_dir}/view"         # 查看大图缓存（按需生成）
        self.hd_subdir = f"{self.data_dir}/hd"             # RAW「高清」缓存（按需生成，替代原图）
        self.marked_subdir = "被标记的照片"
        # 访问 token 存储文件，由桌面端管理、Web 端只读校验
        self.token_file = f"{self.data_dir}/tokens.json"
        # 客户选片清单，Web 端读写、桌面端导出时读取
        self.selection_file = f"{self.data_dir}/selections.json"
        # 跳过检查只需认顶层目录名：._picshare 一名即覆盖其下全部缓存/数据。
        # 集中定义，列相册/算张数/文件路由访问控制统一引用，避免到处漏改。
        self.system_subdirs = (self.marked_subdir, self.data_dir)

        # 两档缩略图：网格小图要快、查看大图要清晰
        self.thumb_size = (400, 400)     # 网格缩略图：一屏几十张，够用即可
        self.thumb_quality = 65
        self.view_size = (1600, 1600)    # 查看大图：满屏清晰，按需单张生成
        self.view_quality = 80
        # RAW 不能给真原图(容器浏览器打不开、体积也大)，改为客户主动点「高清」时
        # 才按需生成的更大尺寸 JPEG——比 view 更清晰，又远小于原始 RAW 文件。
        self.hd_size = (3600, 3600)
        self.hd_quality = 88
        self.port = 5000

        # 定义 RAW 扩展名（这些文件禁止下载真原图，改为可按需查看「高清」衍生 JPEG）
        self.raw_extensions = {
            '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.sr2'
        }

        # 允许扫描的所有扩展名 (RAW + 普通图片)
        self.allowed_extensions = {
                                      '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic'
                                  } | self.raw_extensions  # 合并集合


state = ServerState()
