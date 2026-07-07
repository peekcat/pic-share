import os
import time
import tempfile
import subprocess
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from io import BytesIO

from PIL import Image, ImageOps

from .config import state
from .status import update_global_status

logger = logging.getLogger(__name__)


def _temp_path(final: Path) -> Path:
    """在目标同目录下创建唯一临时文件，用于「先写后原子替换」。

    同目录保证 os.replace 是同一文件系统内的原子 rename。
    """
    fd, name = tempfile.mkstemp(dir=str(final.parent), prefix=".tmp_", suffix=final.suffix or ".jpg")
    os.close(fd)
    return Path(name)


class PreviewGenerator:
    def __init__(self):
        # 线程池用于并发扫描和生成。worker 数控制在 CPU 一半左右，
        # 避免预热时 PIL 解码 / magick 子进程占满 CPU、抢 GIL 拖累 UI 与 Web 响应。
        workers = max(2, (os.cpu_count() or 4) // 2)
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.scanned_files = set()

    @staticmethod
    def generate_raw_preview_with_magick(original_path: Path, preview_path: Path, size, quality) -> bool:
        """
        使用 ImageMagick 命令行工具 (magick) 生成 RAW 预览图。
        修复了参数传递问题，并增加了 Windows 下隐藏黑框的处理。
        """
        command = 'magick'
        tmp = None

        try:
            # 1. 确保目标预览文件夹存在
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            # 先写临时文件，成功后再原子替换（避免半截文件 / 并发写冲突）
            tmp = _temp_path(preview_path)

            # 2. 构造 Magick 命令
            # -auto-orient : 根据 EXIF 自动旋转图片 (RAW文件常需要这个)
            # -thumbnail   : 生成缩略图
            # -quality     : JPEG 质量
            magick_cmd = [
                command,
                str(original_path),
                '-auto-orient',
                '-thumbnail', f"{size[0]}x{size[1]}>",
                '-quality', str(quality),
                f"JPG:{str(tmp)}"
            ]

            logger.debug(f"⚡ 尝试用 Magick 生成: {original_path.name}")

            # [新增] 防止 Windows 下弹出黑色命令行窗口
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            # 3. 执行命令
            result = subprocess.run(
                magick_cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 增加超时时间到 60秒
                check=False,
                startupinfo=startupinfo,     # 隐藏窗口
                creationflags=creationflags  # 彻底不分配控制台，杜绝闪框
            )

            # 4. 检查结果
            if result.returncode != 0:
                logger.error(f"❌ Magick 失败 (代码 {result.returncode}): {original_path.name}")
                if result.stderr.strip():
                    logger.error(f"   错误信息: {result.stderr.strip()}")
                return False

            # 5. 验证临时文件有效后，原子替换为正式预览
            if tmp.exists() and tmp.stat().st_size > 1024:
                os.replace(tmp, preview_path)
                logger.debug(f"✅ Magick 成功: {original_path.name}")
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
        finally:
            # 清理可能残留的临时文件（成功路径下已被 os.replace 移走）
            if tmp is not None and tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    pass

    @staticmethod
    def extract_embedded_preview(image_path: Path) -> Image.Image | None:
        """提取 RAW 内嵌的「最大」JPEG 预览。

        绝大多数 RAW（CR2/CR3/NEF/ARW/DNG…）都内嵌了一张大尺寸(常为全尺寸或 ~2K)的
        JPEG 预览。这里纯 Python 扫描文件里所有 JPEG 段、取尺寸最大的一张：既得到清晰
        大图，又完全不依赖 ImageMagick。找不到返回 None。
        """
        try:
            data = image_path.read_bytes()
        except Exception:
            return None
        candidates = []   # (面积, 偏移)
        pos = 0
        while True:
            i = data.find(b'\xff\xd8\xff', pos)   # JPEG 起始标记 SOI
            if i == -1:
                break
            pos = i + 3
            try:
                # 只读图头拿尺寸：给一段足够含 SOF 的窗口即可，避免整份拷贝
                with Image.open(BytesIO(data[i:i + 262144])) as im:
                    candidates.append((im.size[0] * im.size[1], i))
            except Exception:
                continue
        if not candidates:
            return None
        candidates.sort(reverse=True)             # 取最大的一张
        off = candidates[0][1]
        end = min(len(data), off + 32 * 1024 * 1024)   # 上界 32MB，足够任何内嵌 JPEG
        try:
            with Image.open(BytesIO(data[off:end])) as im:
                im.load()
                return im.copy()
        except Exception:
            return None

    def generate_sync(self, original_path: Path, preview_path: Path, size=None, quality=None):
        """
        同步生成预览图逻辑：
        1. 检查是否存在 -> 2. PIL 读取 -> 3. 提取内嵌缩略图 -> 4. ImageMagick 转码

        size/quality 缺省用网格小图参数；查看大图传入 view_size/view_quality。
        """
        size = size or state.thumb_size
        quality = quality or state.thumb_quality
        try:
            # 检查文件是否已存在且大小正常
            if preview_path.exists() and preview_path.stat().st_size > 100:
                return True

            preview_path.parent.mkdir(parents=True, exist_ok=True)
            img = None

            is_raw = original_path.suffix.lower() in state.raw_extensions

            # [尝试 1] RAW 优先提取内嵌的「最大」JPEG 预览：绝大多数 RAW 都内嵌了大预览，
            # 命中即可得到清晰大图，且完全不依赖 ImageMagick（Windows 上尤其省事）
            if is_raw:
                img = self.extract_embedded_preview(original_path)

            # [尝试 2] 普通图片（或 RAW 无内嵌预览）用 PIL 打开
            if img is None:
                try:
                    with Image.open(original_path) as im:
                        im.load()
                        img = im.copy()
                except Exception:
                    img = None

            # [尝试 3] 如果前两者都失败，且是 RAW，调用 ImageMagick
            if img is None and is_raw:
                # 注意：Magick 会直接生成文件，不需要后续的 PIL save 操作
                # 直接返回 Magick 的执行结果
                return self.generate_raw_preview_with_magick(original_path, preview_path, size, quality)

            # 如果以上方法都无法获取图像对象，则宣告失败
            if img is None:
                return False

            # === 保存逻辑 (仅针对 PIL 或 内嵌缩略图 成功的情况) ===
            img = ImageOps.exif_transpose(img)  # 处理手机照片的旋转
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 缩放并原子保存：先写临时文件再 rename，避免半截文件 / 并发写冲突
            img.thumbnail(size, Image.Resampling.LANCZOS)
            tmp = _temp_path(preview_path)
            try:
                # 不用 optimize：对缩略图体积几乎无差，却显著拖慢编码
                img.save(tmp, "JPEG", quality=quality)
                os.replace(tmp, preview_path)
            except Exception:
                if tmp.exists():
                    tmp.unlink()
                raise
            return True

        except Exception as e:
            # 这里的日志级别改为 ERROR，确保你能看到为什么失败
            logger.error(f"生成预览图最终失败: {original_path} \n原因: {e}")
            return False

    def scan_all(self, root_path: Path):
        if not root_path.exists():
            return
        update_global_status("⏳ 正在后台预热缩略图...")
        futures = []
        try:
            for item in root_path.iterdir():
                # 跳过系统文件夹
                if item.name in (state.marked_subdir, state.preview_subdir, state.view_subdir):
                    continue

                if item.is_dir():
                    for file_path in item.rglob("*"):
                        if not file_path.is_file():
                            continue
                        if file_path.suffix.lower() not in state.allowed_extensions:
                            continue
                        # 防御性检查
                        if any(d in file_path.parts for d in
                               (state.marked_subdir, state.preview_subdir, state.view_subdir)):
                            continue

                        try:
                            rel_path = file_path.relative_to(root_path)
                            preview_path = root_path / state.preview_subdir / rel_path

                            if str(preview_path) not in self.scanned_files:
                                if not preview_path.exists():
                                    futures.append(
                                        self.executor.submit(self.generate_sync, file_path, preview_path))
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

        # 等待后台生成真正完成。进度按时间节流上报：只有预热确实较慢
        # （距上次播报超过 0.5s）才报中间进度，避免快速场景出现失真的 0/N。
        done = failed = 0
        last_report = time.monotonic()
        for fut in as_completed(futures):
            done += 1
            try:
                if not fut.result():
                    failed += 1
            except Exception:
                failed += 1
            now = time.monotonic()
            if done < total and now - last_report >= 0.5:
                update_global_status(f"⚡ 预热中: {done}/{total}")
                last_report = now

        if failed:
            update_global_status(f"✅ 预热完成: {total} 张（{failed} 张失败）")
        else:
            update_global_status(f"✅ 预热完成: 共 {total} 张")


generator = PreviewGenerator()
