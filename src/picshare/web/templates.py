# ====== 2. Web 模板设计 (增加加载进度条) ======

# 现代 SVG 图标定义
ICONS = {
    'back': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
    'star_empty': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
    'star_fill': '<svg width="24" height="24" viewBox="0 0 24 24" fill="#FFD700" stroke="#FFD700" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
    'hd': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="3" x2="12" y2="21"/><path d="M7 12h-2"/><path d="M7 15h-2"/><path d="M17 12h2"/><path d="M17 15h2"/></svg>',
    'close': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
    'prev': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
    'next': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
}

CSS_STYLE = '''
:root { --bg: #000; --bar-bg: rgba(20, 20, 20, 0.85); --accent: #0A84FF; --text: #fff; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); margin: 0; overflow-x: hidden; -webkit-tap-highlight-color: transparent; }

/* 导航栏 */
.navbar { position: fixed; top: 0; width: 100%; box-sizing: border-box; height: 44px; z-index: 100;
    background: var(--bar-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 0.5px solid rgba(255,255,255,0.1);
    display: flex; align-items: center; justify-content: space-between;
    padding: env(safe-area-inset-top) 10px 0 10px; height: calc(44px + env(safe-area-inset-top)); }
.nav-btn { color: var(--accent); background: none; border: none; padding: 10px; cursor: pointer; display: flex; align-items: center; white-space: nowrap; }
/* 三栏导航：左右等宽，标题按内容宽度钉在正中，右侧变宽也不挪动标题 */
.nav-side { flex: 1 1 0; display: flex; align-items: center; min-width: 0; }
.nav-title { flex: 0 1 auto; min-width: 0; text-align: center; font-weight: 600; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 6px; }
/* 选片汇总 */
.sel-summary { justify-content: flex-end; gap: 8px; }
.sel-count { font-size: 13px; color: rgba(255,255,255,0.6); white-space: nowrap; }
.sel-count.has { color: #FFD700; font-weight: 600; cursor: pointer; }
.sel-count.filtering { color: #000; background: #FFD700; padding: 3px 10px; border-radius: 12px; }
.sel-clear { display: none; background: none; border: none; color: var(--accent); font-size: 13px; padding: 8px 4px; cursor: pointer; }
.sel-clear.show { display: inline; }

/* 网格布局 */
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; padding: calc(50px + env(safe-area-inset-top)) 0 20px 0; }
@media (min-width: 600px) { .grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 4px; padding-left: 4px; padding-right: 4px;} }
.cell { aspect-ratio: 1; background: #1c1c1e; overflow: hidden; position: relative; cursor: pointer;}
.cell img { width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.4s ease; will-change: opacity; }
.cell img.loaded { opacity: 1; }

/* 图片查看器 */
.viewer { display: none; position: fixed; inset: 0; background: #000; z-index: 200; flex-direction: column; animation: fadeIn 0.2s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.v-header { position: absolute; top: 0; width: 100%; padding-top: env(safe-area-inset-top); display: flex; justify-content: flex-end; z-index: 202; pointer-events: none;}
.v-close { pointer-events: auto; padding: 15px; background: none; border: none; color: #fff; opacity: 0.8; }
.v-main { flex: 1; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;
    box-sizing: border-box; padding: calc(54px + env(safe-area-inset-top)) 0 calc(60px + env(safe-area-inset-bottom)) 0; }
.v-main img { max-width: 100%; max-height: 100%; object-fit: contain; transition: opacity 0.2s; }

/* 新增：图片加载动画/进度条 */
.v-loading-overlay {
    position: absolute;
    inset: 0;
    display: none; /* 默认隐藏 */
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.7);
    z-index: 201;
    color: white;
    font-size: 14px;
    flex-direction: column;
}
.loader {
    border: 4px solid rgba(255, 255, 255, 0.3);
    border-top: 4px solid #fff;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin-bottom: 10px;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* 底部控制栏 */
.controls { position: absolute; bottom: 0; width: 100%; padding-bottom: env(safe-area-inset-bottom);
    background: var(--bar-bg); backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
    border-top: 0.5px solid rgba(255,255,255,0.1);
    display: flex; justify-content: space-around; align-items: center; height: calc(60px + env(safe-area-inset-bottom)); z-index: 202;}
.c-btn { background: none; border: none; color: #fff; padding: 10px 10px; display: flex; flex-direction: column; align-items: center; font-size: 10px; gap: 4px; opacity: 0.7; transition: all 0.2s; }
.c-btn:active { transform: scale(0.9); opacity: 1; }
.c-btn svg { width: 24px; height: 24px; }
.c-btn.active { color: #FFD700; opacity: 1; text-shadow: 0 0 10px rgba(255, 215, 0, 0.4); }
.c-btn.hd-active { color: var(--accent); opacity: 1; }

/* 首页卡片 */
.card-container { display: flex; align-items: center; justify-content: center; height: 100vh; background: #000; }
.card { background: #1c1c1e; padding: 40px 30px; border-radius: 24px; width: 85%; max-width: 340px; text-align: center; border: 1px solid #333; }
.card h2 { margin-top: 0; color: #fff; font-weight: 700; }
.card input { width: 100%; padding: 16px; margin: 20px 0; border-radius: 14px; background: #2c2c2e; border: none; color: #fff; font-size: 16px; text-align: center; outline: none; }
.card button { width: 100%; padding: 16px; border-radius: 14px; background: var(--accent); border: none; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; }
.card button:active { opacity: 0.8; }
'''

ALBUM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#000000">
    <title>{{ album_name }}</title>
    <style>''' + CSS_STYLE + '''
    /* [新增] 禁用按钮的样式 */
    .c-btn.disabled {
        opacity: 0.2 !important;
        pointer-events: none;
        filter: grayscale(100%);
    }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="nav-side nav-left">
            <a href="/" class="nav-btn">''' + ICONS['back'] + '''&nbsp;返回</a>
        </div>
        <div class="nav-title">{{ album_name }}</div>
        <div class="nav-side sel-summary">
            <span class="sel-count" id="sel-count" onclick="toggleFilter()">已选 0</span>
            <button class="sel-clear" id="sel-clear" onclick="clearSelection()">清空</button>
        </div>
    </div>

    <div class="grid">
        {% for photo in photos %}
        <div class="cell" data-file="{{ photo.filename }}" onclick="openViewer({{ loop.index0 }})">
            <img data-src="{{ photo.preview }}" loading="lazy">
        </div>
        {% endfor %}
    </div>

    <div class="viewer" id="viewer">
        <div class="v-header">
            <button class="v-close" onclick="closeViewer()">''' + ICONS['close'] + '''</button>
        </div>
        <div class="v-main">
            <img id="v-img" onclick="next()">
        </div>

        <div class="v-loading-overlay" id="loading-overlay">
            <div class="loader"></div>
            <span>正在加载原图...</span>
        </div>

        <div class="controls">
            <button class="c-btn" onclick="prev(event)">
                <div>''' + ICONS['prev'] + '''</div>
                <span>上一张</span>
            </button>

            <button class="c-btn" id="mark-btn" onclick="toggleMark(event)">
                <div id="mark-icon">''' + ICONS['star_empty'] + '''</div>
                <span>收藏</span>
            </button>

            <button class="c-btn" id="orig-btn" onclick="toggleOriginal(event)">
                <div id="hd-icon">''' + ICONS['hd'] + '''</div>
                <span>原图</span>
            </button>

            <button class="c-btn" onclick="next(event)">
                <div>''' + ICONS['next'] + '''</div>
                <span>下一张</span>
            </button>
        </div>
    </div>

    <script>
        const photos = {{ photos | tojson }};
        const albumName = "{{ album_name }}";
        const token = "{{ token }}";
        let curIdx = 0;
        let isOrig = false;
        let loadViewGen = 0;   // 防止旧大图迟到后覆盖新图

        // 已选状态由服务端一次性注入，翻图无需再逐张查询
        let markedState = {};
        {{ selected | tojson }}.forEach(f => { markedState[f] = true; });
        let selCount = Object.keys(markedState).length;
        let filterOn = false;      // 是否只看已选
        let viewList = photos;     // 看图器当前翻页所用的列表

        const selCountEl = document.getElementById('sel-count');
        const selClearEl = document.getElementById('sel-clear');
        function renderSelLabel() {
            // 筛选态下换成「只看已选 N ✕」，✕ 明确提示点此退出
            selCountEl.textContent = filterOn ? ('只看已选 ' + selCount + '  ✕') : ('已选 ' + selCount);
        }
        function updateSelCount() {
            selCountEl.classList.toggle('has', selCount > 0);
            selClearEl.classList.toggle('show', selCount > 0);
            renderSelLabel();
        }
        updateSelCount();

        // 「已选 N」筛选：点一下只看已收藏，再点回到全部
        function applyFilter() {
            if (filterOn && selCount === 0) filterOn = false;   // 无可显示则退出筛选
            document.querySelectorAll('.cell').forEach(cell => {
                const sel = !!markedState[cell.dataset.file];
                cell.style.display = (!filterOn || sel) ? '' : 'none';
            });
            viewList = filterOn ? photos.filter(p => markedState[p.filename]) : photos;
            selCountEl.classList.toggle('filtering', filterOn);
            renderSelLabel();
        }
        function toggleFilter() {
            if (selCount === 0 && !filterOn) return;   // 没有已选时不可进入
            filterOn = !filterOn;
            applyFilter();
            window.scrollTo(0, 0);
        }

        // Lazy Load Logic
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(e => {
                if(e.isIntersecting) {
                    const img = e.target;
                    img.src = img.dataset.src;
                    img.onload = () => img.classList.add('loaded');
                    obs.unobserve(img);
                }
            });
        }, {rootMargin: "200px"});
        document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));

        // Viewer Logic
        const viewer = document.getElementById('viewer');
        const vImg = document.getElementById('v-img');
        const markBtn = document.getElementById('mark-btn');
        const markIcon = document.getElementById('mark-icon');
        const origBtn = document.getElementById('orig-btn');
        const loadingOverlay = document.getElementById('loading-overlay');

        const ICONS = {
            empty: `''' + ICONS['star_empty'] + '''`,
            fill: `''' + ICONS['star_fill'] + '''`
        };

        function showLoading(show) {
            loadingOverlay.style.display = show ? 'flex' : 'none';
        }

        function openViewer(globalIdx) {
            // 传入的是相对完整列表的下标，映射到当前(可能已筛选的)列表
            const idx = viewList.indexOf(photos[globalIdx]);
            if (idx === -1) return;
            curIdx = idx;
            viewer.style.display = 'flex';
            loadPhoto();
        }

        function closeViewer() {
            viewer.style.display = 'none';
            vImg.src = '';
            showLoading(false);
            if (filterOn) applyFilter();  // 回到网格时刷新筛选(反映期间的取消收藏)
        }

        function loadPhoto() {
            // 每次切换图片，重置原图状态
            isOrig = false;
            showLoading(false);
            const p = viewList[curIdx];

            // 先用小图占位（网格多半已缓存，秒显）
            vImg.onerror = null;
            vImg.style.opacity = 0.3;
            vImg.src = p.preview;
            vImg.onload = () => { vImg.style.opacity = 1; };

            // 后台预加载清晰大图，成功后无缝替换（迟到/失败则保留小图）
            const gen = ++loadViewGen;
            const hi = new Image();
            hi.onload = () => {
                if (gen === loadViewGen && !isOrig) {
                    vImg.src = hi.src;
                    vImg.style.opacity = 1;
                }
            };
            hi.src = p.view;

            // [修改] 更新原图按钮状态（检查是否为 RAW）
            updateOrigUI();

            // 收藏状态已全量注入，直接渲染即可
            renderMark(!!markedState[p.filename]);
        }

        function next(e) {
            if(e) e.stopPropagation();
            if(curIdx < viewList.length - 1) {
                curIdx++;
                loadPhoto();
            }
        }

        function prev(e) {
            if(e) e.stopPropagation();
            if(curIdx > 0) {
                curIdx--;
                loadPhoto();
            }
        }

        function toggleOriginal(e) {
            e.stopPropagation();
            // 如果是 RAW 文件，直接忽略点击（虽然 CSS 已经禁用了 pointer-events，这里做双重保险）
            if (viewList[curIdx].is_raw) return;

            const isNowOriginal = !isOrig;
            isOrig = isNowOriginal;
            updateOrigUI();

            vImg.style.opacity = 0.5;

            if (isOrig) {
                showLoading(true);
                const tempImg = new Image();
                tempImg.onload = () => {
                    showLoading(false);
                    vImg.src = tempImg.src;
                    vImg.style.opacity = 1;
                };
                tempImg.onerror = () => {
                    showLoading(false);
                    alert('加载原图失败或文件不存在。');
                    vImg.style.opacity = 1;
                };
                tempImg.src = viewList[curIdx].original;
            } else {
                showLoading(false);
                const p = viewList[curIdx];
                vImg.onerror = () => { vImg.onerror = null; vImg.src = p.preview; };
                vImg.src = p.view;   // 退出原图回到清晰大图，失败回退小图
                vImg.style.opacity = 1;
            }
        }

        function updateOrigUI() {
            // [新增] 检查当前图片是否为 RAW
            const isRaw = viewList[curIdx].is_raw;

            if (isRaw) {
                // 如果是 RAW，禁用按钮并变灰
                origBtn.classList.add('disabled');
                origBtn.classList.remove('hd-active');
            } else {
                // 如果是普通图片，启用按钮
                origBtn.classList.remove('disabled');
                // 根据是否处于查看原图模式，切换高亮颜色
                if(isOrig) origBtn.classList.add('hd-active');
                else origBtn.classList.remove('hd-active');
            }
        }

        function toggleMark(e) {
            e.stopPropagation();
            const currentFile = viewList[curIdx].filename;
            const prevState = !!markedState[currentFile];
            const nextState = !prevState;

            // 乐观更新
            markedState[currentFile] = nextState;
            selCount += nextState ? 1 : -1;
            renderMark(nextState);
            updateSelCount();

            fetch(`/share/${token}/mark`, {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({filename:currentFile})
            }).then(r=>r.json()).then(d => {
                if(!d.success) {
                    markedState[currentFile] = prevState;
                    selCount += prevState ? 1 : -1;
                    renderMark(prevState);
                    updateSelCount();
                    alert('收藏操作失败，请检查网络。');
                    return;
                }
                // 以服务端为准校正（含并发场景下的计数）
                markedState[currentFile] = d.is_marked;
                if (typeof d.count === 'number') { selCount = d.count; }
                renderMark(d.is_marked);
                updateSelCount();
            }).catch(() => {
                markedState[currentFile] = prevState;
                selCount += prevState ? 1 : -1;
                renderMark(prevState);
                updateSelCount();
                alert('网络连接错误。');
            });
        }

        function clearSelection() {
            if (selCount === 0) return;
            if (!confirm('确定清空全部 ' + selCount + ' 张选择吗？')) return;
            fetch(`/share/${token}/clear_selection`, { method:'POST' })
                .then(r=>r.json()).then(d => {
                    if (!d.success) { alert('清空失败，请重试。'); return; }
                    markedState = {};
                    selCount = 0;
                    updateSelCount();
                    applyFilter();  // 退出筛选并恢复全部
                    if (viewer.style.display === 'flex') renderMark(false);
                }).catch(() => alert('网络连接错误。'));
        }

        function renderMark(isMarked) {
            markIcon.innerHTML = isMarked ? ICONS.fill : ICONS.empty;
            if(isMarked) markBtn.classList.add('active');
            else markBtn.classList.remove('active');
        }
    </script>
</body>
</html>
'''

# 中性落地页：不暴露相册名输入，避免枚举
LANDING_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>私有相册</title>
<style>''' + CSS_STYLE + '''</style>
</head>
<body>
    <div class="card-container">
        <div class="card">
            <h2>🔐 私有相册</h2>
            <p style="color:#aaa; font-size:15px; line-height:1.6; margin:10px 0 0;">
                请使用您收到的<strong>专属访问链接</strong>进入相册。<br>
                如无链接，请联系您的摄影师。
            </p>
        </div>
    </div>
</body>
</html>
'''

# 口令输入页：访问设了口令的相册时弹出
PASSCODE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>请输入访问口令</title>
<style>''' + CSS_STYLE + '''</style>
</head>
<body>
    <div class="card-container">
        <div class="card">
            <h2>🔑 访问口令</h2>
            {% if error %}
            <p style="color:#FF6B6B; font-size:14px; margin:10px 0 0;">口令错误，请重试。</p>
            {% endif %}
            <form action="/share/{{ token }}/unlock" method="post">
                <input name="passcode" type="text" placeholder="请输入 4 位访问口令"
                       autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
                       autofocus style="max-width: 280px;">
                <button>进入相册</button>
            </form>
        </div>
    </div>
</body>
</html>
'''
