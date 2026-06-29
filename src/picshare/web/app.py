import os
import shutil
from pathlib import Path

from flask import Flask, send_file, render_template_string, request, abort, url_for, jsonify

from ..config import state
from ..paths import safe_join
from ..preview import generator
from ..status import update_global_status
from .templates import ALBUM_TEMPLATE, HOME_TEMPLATE

app = Flask(__name__)


@app.after_request
def add_header(response):
    if 'image' in response.mimetype:
        response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


# ====== 3. Flask 路由 (不变) ======
@app.route('/')
def home(): return render_template_string(HOME_TEMPLATE)


@app.route('/check_album')
def check_album():
    name = request.args.get('name', '').strip()
    if name == state.marked_subdir: return "禁止访问", 403
    return render_template_string("<script>window.location.href='/album/'+encodeURIComponent('{{n}}')</script>", n=name)


@app.route('/album/<path:album_name>')
def album_view(album_name):
    # 🔒 禁止访问特殊系统文件夹
    if album_name == state.marked_subdir or album_name == state.preview_subdir:
        return "⛔ 禁止访问系统缓存文件夹", 403

    path = safe_join(state.base_dir, album_name)
    if not path or not path.exists():
        return "相册不存在", 404

    # 额外检查：解析后的路径是否指向预览或标记目录
    try:
        rel_path = path.relative_to(Path(state.base_dir).resolve())
        if rel_path.parts and (rel_path.parts[0] == state.marked_subdir or rel_path.parts[0] == state.preview_subdir):
            return "⛔ 禁止访问系统文件夹", 403
    except ValueError:
        pass  # 路径不在 base_dir 下，后续 404 处理

    photos = []
    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in state.allowed_extensions:
            # 双重保险：跳过任何包含系统目录的文件
            if state.marked_subdir in f.parts or state.preview_subdir in f.parts:
                continue
            try:
                rel = f.relative_to(path).as_posix()

                # [新增] 判断是否为 RAW 文件
                is_raw_file = f.suffix.lower() in state.raw_extensions

                photos.append({
                    'filename': rel,
                    'preview': url_for('get_preview', album=album_name, filename=rel),
                    'original': url_for('get_original', album=album_name, filename=rel),
                    'is_raw': is_raw_file  # 将此标记传递给前端
                })
            except:
                continue
    return render_template_string(ALBUM_TEMPLATE, album_name=album_name, photos=photos)


@app.route('/file/preview/<path:album>/<path:filename>')
@app.route('/file/preview/<path:album>/<path:filename>')
def get_preview(album, filename):
    # 原始文件的完整路径 (state.base_dir / album / filename)
    original_path = safe_join(state.base_dir, album, filename)
    if not original_path or not original_path.exists():
        abort(404)

    # 计算预览文件的完整路径
    # 预览路径 = 根目录 / 预览子目录 / album / filename
    # 注意：Path(state.base_dir) / state.preview_subdir 是预览缓存的根目录
    # album/filename 是相对于共享根目录的路径部分
    preview_path = safe_join(str(Path(state.base_dir) / state.preview_subdir), album, filename)

    if not preview_path: abort(404)

    # 检查预览文件是否存在
    if not preview_path.exists():
        # 如果不存在，则生成它
        success = generator.generate_sync(original_path, preview_path)
        if not success:
            # 如果生成失败，直接返回原图，但不返回原图的 mime-type
            # 这是一个简单的降级策略，虽然返回原图，但文件路径仍是 /file/preview/...
            return send_file(original_path)

    return send_file(preview_path)


@app.route('/file/original/<path:album>/<path:filename>')
def get_original(album, filename):
    path = safe_join(state.base_dir, album, filename)
    if not path or not path.exists(): abort(404)
    return send_file(path)


@app.route('/api/check_mark')
def check_mark():
    p = safe_join(state.base_dir, state.marked_subdir, request.args.get('album'), request.args.get('filename'))
    return jsonify({'is_marked': p and p.exists()})


@app.route('/api/toggle_mark', methods=['POST'])
def toggle_mark():
    d = request.json
    src = safe_join(state.base_dir, d['album'], d['filename'])
    dst = safe_join(state.base_dir, state.marked_subdir, d['album'], d['filename'])
    if not src or not src.exists(): return jsonify({'success': False})
    try:
        if dst.exists():
            os.remove(dst)
            update_global_status(f"🗑️ 取消: {Path(d['filename']).name}")
            return jsonify({'success': True, 'is_marked': False})
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            update_global_status(f"⭐ 标记: {Path(d['filename']).name}")
            return jsonify({'success': True, 'is_marked': True})
    except Exception as e:
        return jsonify({'success': False})
