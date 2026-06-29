import os
import subprocess
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

from .config import state
from .status import update_global_status

logger = logging.getLogger(__name__)


class PreviewGenerator:
    def __init__(self):
        # 线程池用于并发扫描和生成
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.scanned_files = set()

    @staticmethod
    def generate_raw_preview_with_magick(original_path: Path, preview_path: Path) -> bool:
        """
        使用 ImageMagick 命令行工具 (magick) 生成 RAW 预览图。
        修复了参数传递问题，并增加了 Windows 下隐藏黑框的处理。
        """
        command = 'magick'

        try:
            # 1. 确保目标预览文件夹存在
            preview_path.parent.mkdir(parents=True, exist_ok=True)

            # 2. 构造 Magick 命令
            # -auto-orient : 根据 EXIF 自动旋转图片 (RAW文件常需要这个)
            # -thumbnail   : 生成缩略图
            # -quality     : JPEG 质量
            magick_cmd = [
                command,
                str(original_path),
                '-auto-orient',
                '-thumbnail', f"{state.thumb_size[0]}x{state.thumb_size[1]}>",
                '-quality', str(state.thumb_quality),
                f"JPG:{str(preview_path)}"
            ]

            logger.info(f"⚡ 尝试用 Magick 生成: {original_path.name}")

            # [新增] 防止 Windows 下弹出黑色命令行窗口
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # 3. 执行命令
            result = subprocess.run(
                magick_cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 增加超时时间到 60秒
                check=False,
                startupinfo=startupinfo  # 应用隐藏窗口设置
            )

            # 4. 检查结果
            if result.returncode != 0:
                logger.error(f"❌ Magick 失败 (代码 {result.returncode}): {original_path.name}")
                if result.stderr.strip():
                    logger.error(f"   错误信息: {result.stderr.strip()}")
                return False

            # 5. 验证文件是否有效
            if preview_path.exists() and preview_path.stat().st_size > 1024:
                logger.info(f"✅ Magick 成功: {original_path.name}")
                return True
            else:
                logger.warning(f"⚠️ Magick 运行成功但文件无效: {original_path.name}")
                return False

        except FileNotFoundError:
            logger.error(f"🚨 找不到命令 '{command}'。请确认 ImageMagick 已安装并添加到 PATH 环境变量。")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Magick 处理超时: {original_path.name}")
            return False
        except Exception as e:
            logger.exception(f"Magick 运行时异常: {original_path.name} - {e}")
            return False

    @staticmethod
    def extract_embedded_thumbnail(image_path: Path) -> Image.Image | None:
        """尝试从 RAW 文件中提取内嵌的 JPEG 缩略图"""
        try:
            from PIL import Image, ExifTags, JpegImagePlugin
            from io import BytesIO

            with open(image_path, 'rb') as f:
                img = JpegImagePlugin.JpegImageFile(f)
                exif = img.getexif()
                if exif:
                    for tag, value in exif.items():
                        if ExifTags.TAGS.get(tag) == 'JPEGInterchangeFormat':
                            offset = value
                            length_tag = next(
                                (k for k, v in ExifTags.TAGS.items() if v == 'JPEGInterchangeFormatLength'), None)
                            length = exif.get(length_tag, 0) if length_tag else 0
                            if offset and length:
                                f.seek(offset)
                                thumbnail_data = f.read(length)
                                return Image.open(BytesIO(thumbnail_data))
        except Exception:
            pass
        return None

    def generate_sync(self, original_path: Path, preview_path: Path):
        """
        同步生成预览图逻辑：
        1. 检查是否存在 -> 2. PIL 读取 -> 3. 提取内嵌缩略图 -> 4. ImageMagick 转码
        """
        try:
            from PIL import Image, ImageOps

            # 检查文件是否已存在且大小正常
            if preview_path.exists() and preview_path.stat().st_size > 100:
                return True

            preview_path.parent.mkdir(parents=True, exist_ok=True)
            img = None

            # 定义 RAW 扩展名集合
            raw_exts = {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.sr2'}
            is_raw = original_path.suffix.lower() in raw_exts

            # [尝试 1] 直接用 PIL 打开 (适合 JPG, PNG, 部分简单 RAW)
            try:
                with Image.open(original_path) as im:
                    im.load()
                    img = im.copy()
            except Exception:
                img = None

            # [尝试 2] 如果是 RAW 且 PIL 失败，尝试提取内嵌预览图
            if img is None and is_raw:
                img = self.extract_embedded_thumbnail(original_path)

            # [尝试 3] 如果前两者都失败，且是 RAW，调用 ImageMagick
            if img is None and is_raw:
                # 注意：Magick 会直接生成文件，不需要后续的 PIL save 操作
                # 直接返回 Magick 的执行结果
                return self.generate_raw_preview_with_magick(original_path, preview_path)

            # 如果以上方法都无法获取图像对象，则宣告失败
            if img is None:
                return False

            # === 保存逻辑 (仅针对 PIL 或 内嵌缩略图 成功的情况) ===
            img = ImageOps.exif_transpose(img)  # 处理手机照片的旋转
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 缩放并保存
            img.thumbnail(state.thumb_size, Image.Resampling.LANCZOS)
            img.save(preview_path, "JPEG", quality=state.thumb_quality, optimize=True)
            return True

        except Exception as e:
            # 这里的日志级别改为 ERROR，确保你能看到为什么失败
            logger.error(f"生成预览图最终失败: {original_path} \n原因: {e}")
            return False

    def generate_task(self, original_path, preview_path):
        return self.generate_sync(original_path, preview_path)

    def scan_all(self, root_path: Path):
        if not root_path.exists():
            return
        update_global_status("⏳ 正在后台预热缩略图...")
        futures = []
        try:
            for item in root_path.iterdir():
                # 跳过系统文件夹
                if item.name in (state.marked_subdir, state.preview_subdir):
                    continue

                if item.is_dir():
                    for file_path in item.rglob("*"):
                        if not file_path.is_file():
                            continue
                        if file_path.suffix.lower() not in state.allowed_extensions:
                            continue
                        # 防御性检查
                        if state.marked_subdir in file_path.parts or state.preview_subdir in file_path.parts:
                            continue

                        try:
                            rel_path = file_path.relative_to(root_path)
                            preview_path = root_path / state.preview_subdir / rel_path

                            if str(preview_path) not in self.scanned_files:
                                if not preview_path.exists():
                                    futures.append(
                                        self.executor.submit(self.generate_task, file_path, preview_path))
                                self.scanned_files.add(str(preview_path))
                        except ValueError:
                            continue
        except Exception:
            logger.exception("扫描出错")
            update_global_status("⚠️ 扫描出错")
            return

        total = len(futures)
        if total == 0:
            update_global_status("✅ 就绪: 所有图片已索引")
            return

        # 等待后台生成真正完成，并上报进度（而不是停在"处理中"）
        update_global_status(f"⚡ 预热中: 0/{total}")
        done = failed = 0
        for fut in as_completed(futures):
            done += 1
            try:
                if not fut.result():
                    failed += 1
            except Exception:
                failed += 1
            if done % 10 == 0:
                update_global_status(f"⚡ 预热中: {done}/{total}")

        if failed:
            update_global_status(f"✅ 预热完成: {total} 张（{failed} 张失败）")
        else:
            update_global_status(f"✅ 预热完成: 共 {total} 张")


generator = PreviewGenerator()
