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
.navbar { position: fixed; top: 0; width: 100%; height: 44px; z-index: 100;
    background: var(--bar-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 0.5px solid rgba(255,255,255,0.1);
    display: flex; align-items: center; justify-content: space-between;
    padding: env(safe-area-inset-top) 10px 0 10px; height: calc(44px + env(safe-area-inset-top)); }
.nav-btn { color: var(--accent); background: none; border: none; padding: 10px; cursor: pointer; display: flex; align-items: center;}
.nav-title { font-weight: 600; font-size: 17px; max-width: 60%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

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
.v-main { flex: 1; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
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
        <a href="/" class="nav-btn">''' + ICONS['back'] + '''&nbsp;返回</a>
        <div class="nav-title">{{ album_name }}</div>
        <div style="width: 44px;"></div>
    </div>

    <div class="grid">
        {% for photo in photos %}
        <div class="cell" onclick="openViewer({{ loop.index0 }})">
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

        let markedState = {};

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

        function openViewer(idx) {
            curIdx = idx;
            viewer.style.display = 'flex';
            loadPhoto();
        }

        function closeViewer() {
            viewer.style.display = 'none';
            vImg.src = '';
            showLoading(false);
        }

        function loadPhoto() {
            // 每次切换图片，重置原图状态
            isOrig = false;
            showLoading(false);

            // 加载预览图
            vImg.style.opacity = 0.3;
            vImg.src = photos[curIdx].preview;
            vImg.onload = () => vImg.style.opacity = 1;

            // [修改] 更新原图按钮状态（检查是否为 RAW）
            updateOrigUI();

            // 检查收藏状态
            const currentFile = photos[curIdx].filename;
            if (currentFile in markedState) {
                renderMark(markedState[currentFile]);
            } else {
                renderMark(false);
                fetch(`/a/${token}/check_mark?filename=${encodeURIComponent(currentFile)}`)
                    .then(r=>r.json()).then(d => {
                        markedState[currentFile] = d.is_marked;
                        if(curIdx === photos.findIndex(p => p.filename === currentFile)) {
                            renderMark(d.is_marked);
                        }
                    });
            }
        }

        function next(e) {
            if(e) e.stopPropagation();
            if(curIdx < photos.length - 1) {
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
            if (photos[curIdx].is_raw) return;

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
                tempImg.src = photos[curIdx].original;
            } else {
                showLoading(false);
                vImg.src = photos[curIdx].preview;
                vImg.style.opacity = 1;
            }
        }

        function updateOrigUI() {
            // [新增] 检查当前图片是否为 RAW
            const isRaw = photos[curIdx].is_raw;

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
            const currentFile = photos[curIdx].filename;
            const nextState = !markedState[currentFile];

            markedState[currentFile] = nextState;
            renderMark(nextState);

            fetch(`/a/${token}/mark`, {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({filename:currentFile})
            }).then(r=>r.json()).then(d => {
                if(!d.success) {
                    markedState[currentFile] = !nextState;
                    renderMark(markedState[currentFile]);
                    alert('收藏操作失败，请检查网络。');
                }
            }).catch(() => {
                markedState[currentFile] = !nextState;
                renderMark(markedState[currentFile]);
                alert('网络连接错误。');
            });
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
            <form action="/a/{{ token }}/unlock" method="post">
                <input name="passcode" type="password" inputmode="numeric" placeholder="请输入访问口令"
                       autocomplete="off" autofocus style="max-width: 280px;">
                <button>进入相册</button>
            </form>
        </div>
    </div>
</body>
</html>
'''
