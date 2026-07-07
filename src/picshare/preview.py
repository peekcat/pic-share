import os
import time
import shutil
import struct
import tempfile
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from io import BytesIO

from PIL import Image, ImageOps

from .config import state
from .status import update_global_status

logger = logging.getLogger(__name__)

# 缓存生成逻辑版本：改动「生成算法」(RAW 提取方式 / 方向 / 编码逻辑等)时 +1，
# 使旧缓存自动失效重建，无需手动删缓存目录。
# v2: RAW 兜底改用 rawpy(替代 ImageMagick)。
CACHE_GEN_VERSION = 2


def _cache_signature(size, quality) -> str:
    """缓存版本签名：生成逻辑版本 + 尺寸 + 质量。任一变化都应让旧缓存失效。"""
    return f"g{CACHE_GEN_VERSION}-{size[0]}x{size[1]}q{quality}"


def _tiff_orientation(data: bytes):
    """从 TIFF 系 RAW(CR2/NEF/ARW/DNG/ORF/RW2/PEF/SR2)的头部 IFD0 读 Orientation(0x0112)。

    RAW 的方向常记在主 EXIF 而非内嵌预览里。非 TIFF(如 CR3)或解析失败返回 None。
    """
    try:
        bo = '<' if data[:2] == b'II' else '>' if data[:2] == b'MM' else None
        if bo is None:
            return None
        ifd_off = struct.unpack(bo + 'I', data[4:8])[0]
        count = struct.unpack(bo + 'H', data[ifd_off:ifd_off + 2])[0]
        for i in range(count):
            e = ifd_off + 2 + i * 12
            tag = struct.unpack(bo + 'H', data[e:e + 2])[0]
            if tag == 0x0112:                                  # Orientation
                return struct.unpack(bo + 'H', data[e + 8:e + 10])[0]
    except Exception:
        return None
    return None


def _correct_raw_orientation(img: Image.Image, raw_data: bytes) -> Image.Image:
    """校正一张「来自 RAW 的 JPEG 预览」的方向。

    先用预览自带的 EXIF 方向；很多 RAW 的方向记在主 EXIF(TIFF IFD0)而预览
    不带，此时按 RAW 头部方向补转。供内嵌预览提取与 rawpy 缩略图两条路复用。
    """
    prev_orient = img.getexif().get(0x0112, 1)
    img = ImageOps.exif_transpose(img)
    if prev_orient in (1, None):
        o = _tiff_orientation(raw_data)
        if o in (6, 8) and img.width >= img.height:        # RAW 标注为竖、预览仍是横
            img = img.transpose(Image.Transpose.ROTATE_270 if o == 6 else Image.Transpose.ROTATE_90)
        elif o == 3:
            img = img.transpose(Image.Transpose.ROTATE_180)
    return img


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
        # 避免预热时 PIL/rawpy 解码占满 CPU、抢 GIL 拖累 UI 与 Web 响应。
        workers = max(2, (os.cpu_count() or 4) // 2)
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.scanned_files = set()

    @staticmethod
    def _rawpy_image(original_path: Path) -> Image.Image | None:
        """RAW 兜底：内嵌预览提取失败(极少数无内嵌预览的 RAW)时，用 rawpy(libraw)解码。

        惰性 import：不处理 RAW 就不加载 libraw；万一 rawpy 未打进包，
        本函数返回 None，不影响内嵌预览这条覆盖 99% RAW 的主路径。

        1. 优先 raw.extract_thumb()：多数情况下也能拿到内嵌预览(比主路径更彻底地找)；
        2. 无内嵌缩略图则 raw.postprocess() 全解码，half_size=True 半尺寸——
           目标预览最大仅 hd_size(2800)，全尺寸传感器缩到 2800 与半尺寸缩到 2800
           画质无差，但半尺寸解码快 4 倍、内存省 4 倍。
        """
        try:
            import rawpy
        except ImportError:
            logger.warning("rawpy 未安装，RAW 内嵌预览失败时无法兜底生成")
            return None

        try:
            data = original_path.read_bytes()
        except Exception:
            return None

        try:
            with rawpy.imread(BytesIO(data)) as raw:
                try:
                    t = raw.extract_thumb()
                    if t.format == rawpy.ThumbFormat.JPEG:
                        img = Image.open(BytesIO(t.data))
                        img.load()
                        return _correct_raw_orientation(img, data)
                    if t.format == rawpy.ThumbFormat.BITMAP:
                        # libraw 已按方向摆正位图缩略图，无需再校正
                        return Image.fromarray(t.data)
                except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
                    pass

                # 无内嵌缩略图：全解码兜底。libraw 按相机方向自动摆正，无需再校正。
                logger.debug(f"⚡ rawpy 全解码兜底(无内嵌缩略图): {original_path.name}")
                rgb = raw.postprocess(use_camera_wb=True, half_size=True)
                return Image.fromarray(rgb)
        except Exception as e:
            logger.error(f"rawpy 解码失败: {original_path.name}\n原因: {e}")
            return None

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
                img = im.copy()
        except Exception:
            return None
        return _correct_raw_orientation(img, data)

    def generate_sync(self, original_path: Path, preview_path: Path, size=None, quality=None):
        """
        同步生成预览图逻辑：
        1. 已存在则跳过 -> 2. RAW 提取内嵌大预览 -> 3. PIL 打开普通图 -> 4. RAW 用 rawpy 兜底

        size/quality 缺省用网格小图参数；查看大图传入 view_size/view_quality，
        RAW「高清」传入 hd_size/hd_quality。
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
            # 命中即可得到清晰大图，且完全不依赖任何原生解码库
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

            # [尝试 3] 如果前两者都失败，且是 RAW，用 rawpy(libraw) 兜底解码
            if img is None and is_raw:
                img = self._rawpy_image(original_path)

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

    @staticmethod
    def _reset_if_stale(cache_dir: Path, sig: str) -> bool:
        """缓存目录的版本戳与 sig 不符时，清空目录并写入新戳；返回是否清理过。"""
        marker = cache_dir / ".cachever"
        try:
            current = marker.read_text(encoding="utf-8") if marker.exists() else ""
        except Exception:
            current = ""
        if current == sig:
            return False
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
            except Exception:
                pass
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            marker.write_text(sig, encoding="utf-8")
        except Exception:
            pass
        logger.info(f"缓存逻辑/参数变更，已清理重置：{cache_dir.name}（{sig}）")
        return True

    def ensure_cache_current(self, root_path: Path):
        """比对各级缓存目录的版本戳；参数或生成逻辑变更时清掉对应目录以便重建。

        仅在启动 / 切换根目录时(scan_all 入口)调用一次，不在请求路径上。
        """
        wiped = False
        for subdir, size, quality in (
            (state.preview_subdir, state.thumb_size, state.thumb_quality),   # 网格小图
            (state.view_subdir, state.view_size, state.view_quality),        # 查看大图
            (state.hd_subdir, state.hd_size, state.hd_quality),              # RAW 高清
        ):
            if self._reset_if_stale(root_path / subdir, _cache_signature(size, quality)):
                wiped = True
        if wiped:
            self.scanned_files.clear()   # 已清缓存，强制重新扫描生成

    def scan_all(self, root_path: Path):
        if not root_path.exists():
            return
        self.ensure_cache_current(root_path)
        update_global_status("⏳ 正在后台预热缩略图...")
        futures = []
        try:
            for item in root_path.iterdir():
                # 跳过系统文件夹
                if item.name in state.system_subdirs:
                    continue

                if item.is_dir():
                    for file_path in item.rglob("*"):
                        if not file_path.is_file():
                            continue
                        if file_path.suffix.lower() not in state.allowed_extensions:
                            continue
                        # 防御性检查
                        if any(d in file_path.parts for d in state.system_subdirs):
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
