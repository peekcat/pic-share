# ====== 2. Web 模板设计 (增加加载进度条) ======

# 现代 SVG 图标定义
ICONS = {
    'back': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
    'star_empty': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
    'star_fill': '<svg width="24" height="24" viewBox="0 0 24 24" fill="#FFD700" stroke="#FFD700" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
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

/* 看图器已改用 PhotoSwipe（photoswipe.css），旧自研看图器样式已删除 */

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
    <link rel="stylesheet" href="/static/photoswipe/photoswipe.css">
    <style>''' + CSS_STYLE + '''
    /* 底部操作栏：收藏 + 原图，手机拇指易触达 */
    .pf-actionbar {
        position:absolute; left:0; right:0; bottom:0; z-index:100;
        display:flex; justify-content:center; gap:14px;
        padding:12px 16px calc(14px + env(safe-area-inset-bottom));
        pointer-events:none;
    }
    .pf-act {
        pointer-events:auto; display:inline-flex; align-items:center; gap:7px;
        background:rgba(0,0,0,.5); color:#fff; border:none; border-radius:24px;
        padding:11px 20px; font-size:15px; font-weight:600; cursor:pointer;
        -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px);
    }
    .pf-act:active { transform:scale(.94); }
    .pf-act svg { width:22px; height:22px; }
    .pf-fav.on { color:#FFD700; }
    .pf-fav.on svg { fill:#FFD700; stroke:#FFD700; }
    .pf-orig-btn.on { background:#0A84FF; color:#fff; }
    /* 左右翻页箭头：桌面默认很淡、悬停才明显；触屏隐藏（用滑动翻页） */
    .pswp__button--arrow { opacity:.28 !important; transition:opacity .2s ease; }
    .pswp__button--arrow:hover { opacity:.95 !important; }
    @media (hover: none) { .pswp__button--arrow { display:none !important; } }
    .pswp__button--arrow:disabled, .pswp__button--arrow:disabled:hover { opacity:.1 !important; cursor:default; }
    /* 首/末张友好提示 */
    .pf-hint {
        position:absolute; left:50%; bottom:16%; transform:translateX(-50%);
        background:rgba(0,0,0,.72); color:#fff; padding:9px 18px; border-radius:20px;
        font-size:14px; opacity:0; transition:opacity .2s; pointer-events:none;
        z-index:99999; white-space:nowrap;
    }
    .pf-hint.show { opacity:1; }
    /* 指向底部操作栏的一次性提示（边界提示不用这套）：
       - 换成强调蓝：原本的半透明黑气泡压在黑色留白上等于隐形，一次性引导不能靠运气；
       - 下移到贴着操作栏（实测两者之间留 20px，够放下三角）；
       - 三角横向位置由 JS 按「收藏」按钮实测（--ax），否则会指到两个按钮中间的空隙。 */
    .pf-hint.point {
        bottom:calc(78px + env(safe-area-inset-bottom));
        background:var(--accent); font-weight:600;
    }
    .pf-hint.point::after {
        content:''; position:absolute; left:var(--ax, 50%); bottom:-6px; transform:translateX(-50%);
        border:6px solid transparent; border-top-color:var(--accent); border-bottom:0;
    }
    /* 生成高清时：保留当前大图，居中转圈 + 文字（覆盖层透明，不遮挡底图） */
    .pf-hdload {
        position:absolute; inset:0; z-index:99998; pointer-events:none;
        display:none; flex-direction:column; align-items:center; justify-content:center; gap:12px;
    }
    .pf-hdload.show { display:flex; }
    .pf-hdload .sp {
        width:40px; height:40px; border-radius:50%;
        border:3px solid rgba(255,255,255,.25); border-top-color:#fff;
        animation:pf-spin .8s linear infinite;
    }
    .pf-hdload .tx { color:#fff; font-size:13px; background:rgba(0,0,0,.55); padding:5px 14px; border-radius:14px; }
    @keyframes pf-spin { to { transform:rotate(360deg); } }

    /* 首次使用引导：一屏卡片，复用落地页/口令页那张 .card 的外观 */
    #guide { display:none; position:fixed; inset:0; z-index:200; background:rgba(0,0,0,.75);
             align-items:center; justify-content:center; padding:20px; }
    #guide.open { display:flex; }
    #guide .card { padding:24px 22px 20px; text-align:left; position:relative;
                   max-height:calc(100vh - 40px); overflow-y:auto; }
    #guide h2 { font-size:19px; margin:0 0 4px; }
    /* .card button 是满宽蓝按钮（给「开始选片」用的），✕ 要单独摘出来 */
    #guide .gx { position:absolute; top:8px; right:10px; width:auto; padding:6px 10px;
                 background:none; border:none; color:rgba(255,255,255,.5); font-size:19px;
                 border-radius:0; cursor:pointer; }
    #guide .gi { display:flex; gap:12px; margin:16px 0; }
    #guide .gi .em { font-size:22px; line-height:1.3; }
    #guide .gi b { display:block; font-size:15px; font-weight:600; margin-bottom:3px; }
    #guide .gi .tx { display:block; color:#aaa; font-size:13px; line-height:1.5; }

    /* 重看引导：圆圈只做 20px——顶栏总共才 44px 高，再大就抢「返回」的视线；
       外层按钮靠 padding 把触摸区撑到手机能稳稳点中的尺寸 */
    .nav-help { background:none; border:none; padding:11px 8px; margin-left:2px;
                cursor:pointer; display:flex; align-items:center; }
    .nav-help span { display:flex; align-items:center; justify-content:center;
                     width:20px; height:20px; border-radius:50%; font-size:12px; line-height:1;
                     color:rgba(255,255,255,.5); border:1px solid rgba(255,255,255,.28); }
    .nav-help:active span { color:#fff; border-color:#fff; }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="nav-side nav-left">
            <a href="/" class="nav-btn">''' + ICONS['back'] + '''&nbsp;返回</a>
            <button class="nav-help" type="button" onclick="openGuide()" aria-label="使用说明"><span>?</span></button>
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

    <!-- 首次使用引导：默认隐藏，由脚本决定弹不弹。脚本挂了就当没有这一层，
         不能让客户对着一块拆不掉的遮罩 -->
    <div id="guide" onclick="closeGuide(event)">
        <div class="card" onclick="event.stopPropagation()">
            <button class="gx" type="button" onclick="closeGuide()" aria-label="关闭">✕</button>
            <h2>📷 选片怎么用</h2>
            <div class="gi"><span class="em">👆</span>
                <div><b>点照片放大看</b><span class="tx">左右滑动翻看下一张</span></div></div>
            <div class="gi"><span class="em">⭐</span>
                <div><b>喜欢就点「收藏」</b><span class="tx">大图下方的星标，选择自动保存，不用提交</span></div></div>
            <div class="gi"><span class="em">✅</span>
                <div><b>顶部「已选 N」可以点</b><span class="tx">只看已选的照片，方便最后核对</span></div></div>
            <button type="button" onclick="closeGuide()">开始选片</button>
        </div>
    </div>

    <!-- 看图器由 PhotoSwipe 动态创建 -->

    <script type="module">
        import PhotoSwipe from '/static/photoswipe/photoswipe.esm.min.js';

        const photos = {{ photos | tojson }};
        const token = "{{ token }}";

        // 收藏图标（复用星标）
        const FAV_OFF = `''' + ICONS['star_empty'] + '''`;
        const FAV_ON  = `''' + ICONS['star_fill'] + '''`;

        // ── 新手引导的「看过了」标记 ──
        // 按浏览器记而不是按 token 记：同一个客户收到第二个相册链接时不该再弹一次。
        // 键名带版本号，以后文案有实质改动改成 v2 就能让老客户重看。
        const K_GUIDE = 'ps_guide_v1', K_FAVHINT = 'ps_favhint_v1';
        const memFlags = {};   // 无痕模式下 localStorage 可能直接抛错，至少保证本次会话不重弹
        function seen(k){ if (memFlags[k]) return true;
                          try { return localStorage.getItem(k) === '1'; } catch(e) { return false; } }
        function markSeen(k){ memFlags[k] = true;
                              try { localStorage.setItem(k, '1'); } catch(e) {} }

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

        // ── 首次使用引导 ──
        // ✕ / 点遮罩 / 「开始选片」/ ESC 四种关法都算看过，都写标记：客户手一滑关掉了，
        // 下次刷新再糊他一脸比不弹更烦人；真想再看有顶栏的 ?。
        function openGuide(){
            document.getElementById('guide').classList.add('open');
            document.body.style.overflow = 'hidden';
        }
        function closeGuide(e){
            if (e) e.stopPropagation();
            document.getElementById('guide').classList.remove('open');
            document.body.style.overflow = '';
            markSeen(K_GUIDE);
        }
        // 空相册不弹：对着一屏空网格讲「点照片放大看」只会让客户更懵
        if (photos.length && !seen(K_GUIDE)) openGuide();

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

        // ── 网格 cells 与 photos 同序，用于取缩略图比例 ──
        const cells = Array.from(document.querySelectorAll('.cell'));

        // ── 收藏（乐观更新 + 服务端校正）──
        function toggleFav(filename) {
            const prev = !!markedState[filename];
            const next = !prev;
            markedState[filename] = next;
            selCount += next ? 1 : -1;
            updateSelCount();
            return fetch(`/share/${token}/mark`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            }).then(r => r.json()).then(d => {
                if (!d.success) throw new Error('fail');
                markedState[filename] = d.is_marked;
                if (typeof d.count === 'number') selCount = d.count;
                updateSelCount();
                return d.is_marked;
            }).catch(() => {
                markedState[filename] = prev;
                selCount += prev ? 1 : -1;
                updateSelCount();
                alert('收藏操作失败，请检查网络。');
                return prev;
            });
        }

        // ── 尺寸：缩略图与大图同比例，用缩略图自然尺寸 ×4 估算 1600 档；未加载回退 3:2 ──
        function dimsFor(photo) {
            const gi = photos.indexOf(photo);
            const img = cells[gi] && cells[gi].querySelector('img');
            if (img && img.naturalWidth > 0) {
                return { w: img.naturalWidth * 4, h: img.naturalHeight * 4 };
            }
            return { w: 1600, h: 1067 };
        }
        function buildSlides() {
            return viewList.map(p => {
                const d = dimsFor(p);
                // 「原图」入口的实际图源按类型分流：RAW 没有可看的真原图，给 hd（按需生成的
                // 更大 JPEG）；非 RAW 给 original（真实原始文件）。UI 上统一叫「原图」。
                return { src: p.view, msrc: p.preview, width: d.w, height: d.h,
                         alt: p.filename, _file: p.filename,
                         _view: p.view, _orig: p.is_raw ? p.hd : p.original,
                         _vw: d.w, _vh: d.h, _showOrig: false };
            });
        }

        // ── PhotoSwipe 看图器 ──
        let pswp = null;
        // 安卓返回键/侧滑返回、iOS 边缘返回：打开看图器时压一条历史记录，让「返回」先关看图器
        // 而不是离开相册页。PhotoSwipe 5 已移除 v4 的 history 模块，需自行接管。
        let viewerHistoryPushed = false;
        let hintEl = null, hintTimer = null;
        // opts.ms 停留时长（默认 1200），opts.point 加一个指向底部操作栏的 ▼。
        // 边界提示（「前面没有更多了」）两个都不需要，保持原调用不变。
        function showEdgeHint(msg, opts) {
            opts = opts || {};
            if (!pswp || !pswp.element) return;
            if (!hintEl || hintEl.parentNode !== pswp.element) {
                hintEl = document.createElement('div');
                hintEl.className = 'pf-hint';
                pswp.element.appendChild(hintEl);
            }
            hintEl.textContent = msg;
            hintEl.classList.toggle('point', !!opts.point);
            hintEl.classList.add('show');
            clearTimeout(hintTimer);
            hintTimer = setTimeout(() => { if (hintEl) hintEl.classList.remove('show'); },
                                   opts.ms || 1200);
        }

        // 生成高清时的加载覆盖层（转圈 + 文字），保留底图不清空
        let hdLoadEl = null;
        function showHdLoading(show, msg) {
            if (!pswp || !pswp.element) return;
            if (!hdLoadEl || hdLoadEl.parentNode !== pswp.element) {
                hdLoadEl = document.createElement('div');
                hdLoadEl.className = 'pf-hdload';
                hdLoadEl.innerHTML = '<div class="sp"></div><div class="tx"></div>';
                pswp.element.appendChild(hdLoadEl);
            }
            if (msg) hdLoadEl.querySelector('.tx').textContent = msg;
            hdLoadEl.classList.toggle('show', show);
        }

        function openViewer(globalIdx) {
            const idx = viewList.indexOf(photos[globalIdx]);
            if (idx === -1) return;

            let favBtn = null, origBtn = null;
            let hdGen = 0;   // 防止在途高清加载迟到后错误替换
            pswp = new PhotoSwipe({
                dataSource: buildSlides(),
                index: idx,
                loop: false,                     // 不首尾循环
                bgOpacity: 1,
                wheelToZoom: true,               // 桌面滚轮缩放
                showHideAnimationType: 'fade',
            });

            const curData = () => (pswp && pswp.currSlide ? pswp.currSlide.data : null);
            function refreshActions() {
                const d = curData(); if (!d) return;
                if (favBtn) {
                    const on = !!markedState[d._file];
                    favBtn.classList.toggle('on', on);
                    favBtn.querySelector('.pf-label').textContent = on ? '已收藏' : '收藏';
                }
                if (origBtn) {
                    // 统一叫「原图」：RAW 给的其实是按需生成的更大 JPEG（非真原图），但客户不区分、
                    // 也拿不到/看不了真 RAW，统一叫法更专业省心。
                    origBtn.textContent = d._showOrig ? '退出原图' : '原图';
                    origBtn.classList.toggle('on', !!d._showOrig);   // 蓝色高亮"正在看原图"
                }
            }
            // 大图↔原图切换时保留当前缩放/平移：换图源会重建内容并回到「适应屏幕」，
            // 这里在重建后按自然尺寸比例换算等效缩放（显示尺寸 = 自然宽 × currZoomLevel，
            // 原图自然尺寸变大 → 缩放等比缩小），并沿用平移量，让用户停在放大的同一处。
            function swapSlideSource(d, src, w, h) {
                const s0 = pswp.currSlide;
                const oldW = d.width || w;
                const prevZoom = s0 ? s0.currZoomLevel : 0;
                const fit = s0 && s0.zoomLevels ? s0.zoomLevels.fit : 0;
                const wasZoomed = !!s0 && prevZoom > fit * 1.01;   // 原本就适应屏幕则不必还原
                const px = s0 ? s0.pan.x : 0, py = s0 ? s0.pan.y : 0;

                d.src = src; d.width = w; d.height = h;
                try { pswp.refreshSlideContent(pswp.currIndex); } catch (err) { return; }

                if (!wasZoomed) return;
                try {
                    const s = pswp.currSlide;
                    s.calculateSize();                       // 按新自然尺寸重算 zoomLevels
                    s.currZoomLevel = prevZoom * (oldW / w);  // 显示尺寸不变的等效缩放
                    s.bounds.update(s.currZoomLevel);         // 按该缩放重算平移边界
                    s.panTo(px, py);                          // 夹紧到新边界并应用（保持同一区域）
                } catch (err) {}
            }
            function showView(d) {
                d._showOrig = false;
                swapSlideSource(d, d._view, d._vw, d._vh);   // 已缓存，秒切
                refreshActions();
            }
            function toggleOriginalView() {
                const d = curData();
                if (!d) return;
                // 关闭高清/原图：切回大图（已缓存，秒切）
                if (d._showOrig) { hdGen++; showHdLoading(false); showView(d); return; }
                // 开启：保留当前大图不清空，转圈 + 「正在加载中…」，后台预加载，拉到再替换
                const gen = ++hdGen;
                showHdLoading(true, '正在加载中…');
                if (origBtn) { origBtn.textContent = '加载中…'; origBtn.disabled = true; }
                const hi = new Image();
                hi.onload = () => {
                    if (gen !== hdGen) return;                 // 期间翻页/又点了，忽略
                    showHdLoading(false);
                    if (origBtn) origBtn.disabled = false;
                    d._showOrig = true;
                    swapSlideSource(d, d._orig, d._vw * 3, d._vh * 3);   // 保留放大位置，秒切
                    refreshActions();
                };
                hi.onerror = () => {
                    if (gen !== hdGen) return;
                    showHdLoading(false);
                    if (origBtn) origBtn.disabled = false;
                    refreshActions();
                    showEdgeHint('原图加载失败');
                };
                hi.src = d._orig;   // 触发服务端生成 + 下载
            }

            // 翻页时取消在途的高清加载并收起转圈
            pswp.on('change', () => { hdGen++; showHdLoading(false); refreshActions(); });
            pswp.on('destroy', () => {
                pswp = null; hintEl = null; hdLoadEl = null;
                if (filterOn) applyFilter();
                // ✕/ESC/下滑关闭：弹掉打开时压入的历史记录，否则每看一次图就堆积一条空记录，
                // 客户要多按一次返回才能离开。返回键关闭已在 popstate 里清了标记，不会重复回退。
                if (viewerHistoryPushed) { viewerHistoryPushed = false; history.back(); }
            });

            pswp.init();

            // 同 URL 压栈：地址栏不变，只为多一条可回退的记录，让系统返回手势先关看图器。
            // 放在 init() 之后，避免 init 抛错时留下一条无人回收的历史记录。
            if (!viewerHistoryPushed) {
                history.pushState({ pswpOpen: true }, '', location.href);
                viewerHistoryPushed = true;
            }

            // 底部操作栏（手机拇指易触达）：收藏 + 原图（RAW 与普通图统一显示「原图」，
            // 由 refreshActions() 立即改写，这里的初始文案仅占位）
            const bar = document.createElement('div');
            bar.className = 'pf-actionbar';
            bar.innerHTML =
                '<button class="pf-act pf-fav" type="button">' + FAV_OFF + '<span class="pf-label">收藏</span></button>' +
                '<button class="pf-act pf-orig-btn" type="button">原图</button>';
            pswp.element.appendChild(bar);
            favBtn = bar.querySelector('.pf-fav');
            origBtn = bar.querySelector('.pf-orig-btn');
            favBtn.onclick = () => { const d = curData(); if (d) toggleFav(d._file).then(refreshActions); };
            origBtn.onclick = toggleOriginalView;
            refreshActions();

            // 「收藏」是选片的唯一动作，可它在网格页上压根不存在——只有这一刻能真正指给客户看。
            if (!seen(K_FAVHINT)) {
                showEdgeHint('喜欢就点「收藏」，自动保存', { ms: 3200, point: true });
                // hintEl 有值才说明真的挂上去了（showEdgeHint 会在没有 pswp.element 时空转），
                // 没显示成就别烧掉标记，否则这条提示从此再也不出现
                if (hintEl) {
                    markSeen(K_FAVHINT);
                    // 气泡居中、按钮不居中，三角得按实测位置摆，否则指向两个按钮之间的空隙
                    const b = favBtn.getBoundingClientRect(), h = hintEl.getBoundingClientRect();
                    hintEl.style.setProperty('--ax', (b.left + b.width / 2 - h.left) + 'px');
                }
            }
        }

        // 安卓返回键/侧滑返回、iOS 边缘返回：看图器开着时先关看图器，不离开相册页。
        // 先清标记再 close：close() 会触发 destroy，标记若还在就会多回退一格。
        window.addEventListener('popstate', () => {
            viewerHistoryPushed = false;
            if (pswp && pswp.isOpen) pswp.close();
        });

        // 桌面：空格恢复默认大小（复位缩放）
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.getElementById('guide').classList.contains('open')) {
                closeGuide();
                return;
            }
            if (!pswp || !pswp.isOpen) return;
            if (e.code === 'Space') {
                e.preventDefault();
                const s = pswp.currSlide;
                if (s && s.zoomLevels) s.zoomTo(s.zoomLevels.initial, undefined, 333);
                return;
            }
            const last = pswp.getNumItems() - 1;
            if (e.key === 'ArrowLeft' && pswp.currIndex === 0) showEdgeHint('前面没有更多了');
            else if (e.key === 'ArrowRight' && pswp.currIndex === last) showEdgeHint('后面没有更多了');
        });

        // 供 HTML onclick 调用（module 作用域需显式挂到 window）
        window.openViewer = openViewer;
        window.toggleFilter = toggleFilter;
        window.clearSelection = clearSelection;
        window.openGuide = openGuide;
        window.closeGuide = closeGuide;

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
                }).catch(() => alert('网络连接错误。'));
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
