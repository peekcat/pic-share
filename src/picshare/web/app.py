import secrets
from functools import wraps
from pathlib import Path

from flask import (Flask, send_file, render_template_string, request, abort,
                   url_for, jsonify, session, redirect, g)

from ..config import state
from ..paths import safe_join
from ..preview import generator
from ..status import update_global_status
from .. import tokens, selections
from .templates import ALBUM_TEMPLATE, LANDING_TEMPLATE, PASSCODE_TEMPLATE

app = Flask(__name__)
# 会话密钥用于「口令已解锁」状态；进程级随机，重启后客户需重新输入口令
app.secret_key = secrets.token_hex(32)


@app.after_request
def add_header(response):
    if 'image' in response.mimetype:
        response.headers['Cache-Control'] = 'public, max-age=604800'
    return response


def _is_system_path(resolved: Path) -> bool:
    """判断解析后的路径是否落在系统目录(标记 / 预览缓存)内。

    用于在文件路由层面拦截对 ``被标记的照片`` 与 ``._preview_ipv6_opt`` 的直接访问。
    """
    try:
        rel = resolved.relative_to(Path(state.base_dir).resolve())
    except ValueError:
        return False
    forbidden = (state.marked_subdir, state.preview_subdir, state.view_subdir)
    return any(part in forbidden for part in rel.parts)


def _is_unlocked(token: str) -> bool:
    return token in session.get('unlocked', [])


def require_token(passcode_mode: str = 'deny'):
    """校验 URL 中的 token，并把相册注入 ``g.album``。

    passcode_mode='redirect' 时（相册页），需口令但未解锁则展示口令输入页；
    passcode_mode='deny' 时（文件/API 路由），未解锁直接 403。
    无效 / 过期 token 一律 404。
    """
    def decorator(view):
        @wraps(view)
        def wrapper(token, *args, **kwargs):
            meta = tokens.resolve(token)
            if not meta:
                abort(404)
            if meta.get('passcode') and not _is_unlocked(token):
                if passcode_mode == 'redirect':
                    return render_template_string(PASSCODE_TEMPLATE, token=token, error=False)
                abort(403)
            g.album = meta['album']
            g.meta = meta
            return view(token, *args, **kwargs)
        return wrapper
    return decorator


# ====== 3. Flask 路由 ======
@app.route('/')
def home():
    # 中性落地页：不提供相册名输入，避免枚举
    return render_template_string(LANDING_TEMPLATE)


@app.route('/share/<token>/unlock', methods=['POST'])
def unlock(token):
    if not tokens.resolve(token):
        abort(404)
    if tokens.verify_passcode(token, request.form.get('passcode', '')):
        unlocked = session.get('unlocked', [])
        if token not in unlocked:
            session['unlocked'] = unlocked + [token]
        return redirect(url_for('album_view', token=token))
    return render_template_string(PASSCODE_TEMPLATE, token=token, error=True)


@app.route('/share/<token>')
@require_token('redirect')
def album_view(token):
    album = g.album
    path = safe_join(state.base_dir, album)
    if not path or not path.exists() or _is_system_path(path):
        abort(404)

    photos = []
    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in state.allowed_extensions:
            # 双重保险：跳过任何包含系统目录的文件
            if any(d in f.parts for d in
                   (state.marked_subdir, state.preview_subdir, state.view_subdir)):
                continue
            try:
                rel = f.relative_to(path).as_posix()
                photos.append({
                    'filename': rel,
                    'preview': url_for('get_preview', token=token, filename=rel),
                    'view': url_for('get_view', token=token, filename=rel),
                    'original': url_for('get_original', token=token, filename=rel),
                    'is_raw': f.suffix.lower() in state.raw_extensions,
                })
            except Exception:
                continue
    title = g.meta.get('label') or album
    # 一次性把已选文件名注入模板，前端零请求即可高亮，翻图不再逐张查询
    selected = selections.list_selected(album)
    return render_template_string(ALBUM_TEMPLATE, album_name=title, token=token,
                                  photos=photos, selected=selected)


@app.route('/share/<token>/preview/<path:filename>')
@require_token('deny')
def get_preview(token, filename):
    album = g.album
    original_path = safe_join(state.base_dir, album, filename)
    if not original_path:
        abort(404)

    # 🔒 禁止借预览路由窥探系统目录(标记 / 预览缓存)
    if _is_system_path(original_path):
        abort(403)
    if not original_path.exists():
        abort(404)

    preview_path = safe_join(str(Path(state.base_dir) / state.preview_subdir), album, filename)
    if not preview_path:
        abort(404)

    if not preview_path.exists():
        success = generator.generate_sync(original_path, preview_path)
        if not success:
            # 🔒 RAW 文件禁止下载原图：预览生成失败时不能降级返回原始 RAW
            if original_path.suffix.lower() in state.raw_extensions:
                abort(404)
            return send_file(original_path)

    return send_file(preview_path)


@app.route('/share/<token>/view/<path:filename>')
@require_token('deny')
def get_view(token, filename):
    """查看大图(1600px)：按需生成并缓存。生成失败一律 404，前端保留小图占位。"""
    album = g.album
    original_path = safe_join(state.base_dir, album, filename)
    if not original_path:
        abort(404)
    # 🔒 禁止借大图路由窥探系统目录
    if _is_system_path(original_path):
        abort(403)
    if not original_path.exists():
        abort(404)

    view_path = safe_join(str(Path(state.base_dir) / state.view_subdir), album, filename)
    if not view_path:
        abort(404)
    if not view_path.exists():
        if not generator.generate_sync(original_path, view_path, state.view_size, state.view_quality):
            abort(404)
    return send_file(view_path)


@app.route('/share/<token>/original/<path:filename>')
@require_token('deny')
def get_original(token, filename):
    album = g.album
    path = safe_join(state.base_dir, album, filename)
    if not path:
        abort(404)

    # 🔒 禁止直接访问系统目录(标记 / 预览缓存)
    if _is_system_path(path):
        abort(403)
    # 🔒 RAW 文件禁止查看 / 下载原图(与前端禁用按钮保持一致，防止直接构造 URL 绕过)
    if path.suffix.lower() in state.raw_extensions:
        abort(403)
    if not path.exists():
        abort(404)
    return send_file(path)


@app.route('/share/<token>/mark', methods=['POST'])
@require_token('deny')
def toggle_mark(token):
    """翻转某张照片的选中态。只改选片清单，不复制原图(交付时再由桌面端导出)。"""
    album = g.album
    data = request.get_json(silent=True) or {}
    filename = data.get('filename')
    if not filename:
        return jsonify({'success': False}), 400

    # 仅接受确实属于该相册的文件，避免把任意路径写进清单
    src = safe_join(state.base_dir, album, filename)
    if not src or not src.exists() or _is_system_path(src):
        return jsonify({'success': False})

    is_marked, count = selections.toggle(album, filename)
    update_global_status(
        (f"⭐ 选片: {Path(filename).name}" if is_marked else f"↩️ 取消: {Path(filename).name}")
        + f"（{album} 共 {count} 张）")
    return jsonify({'success': True, 'is_marked': is_marked, 'count': count})


@app.route('/share/<token>/clear_selection', methods=['POST'])
@require_token('deny')
def clear_selection(token):
    """清空该相册当前客户端的全部选择。"""
    n = selections.clear_selected(g.album)
    if n:
        update_global_status(f"🧹 已清空选择：{g.album}（原 {n} 张）")
    return jsonify({'success': True, 'count': 0})
