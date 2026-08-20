# 管理端单页界面（pywebview 直接以 html= 加载，无需静态文件，打包友好）

ADMIN_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PicShare 管理</title>
<style>
  :root { --bg:#1b1b1e; --card:#242429; --card2:#2c2c33; --line:#36363d;
          --text:#eaeaea; --sub:#9a9aa3; --accent:#0A84FF; --green:#2FA572; --red:#C0392B; --amber:#E6A23C; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:"Microsoft YaHei UI","PingFang SC",-apple-system,sans-serif;
         background:var(--bg); color:var(--text); font-size:14px; }
  .wrap { padding:16px 18px 24px; }
  h1 { font-size:19px; margin:0; }
  .subtitle { color:var(--sub); font-size:12px; margin:2px 0 14px; }
  .ver { color:var(--sub); font-size:12px; font-weight:normal; margin-left:8px; vertical-align:middle; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px; margin-bottom:12px; }
  /* 对外服务启动失败的横幅：运行日志面板默认折叠，这类致命错误必须摆在主界面上 */
  .banner { display:none; background:rgba(192,57,43,.16); border:1px solid var(--red);
            border-radius:12px; padding:11px 14px; margin-bottom:12px; font-size:13px; line-height:1.6; }
  .banner.show { display:block; }
  .label { font-weight:600; margin-bottom:8px; }
  .row { display:flex; gap:8px; align-items:center; }
  input[type=text], select { flex:1; background:var(--card2); border:1px solid var(--line);
          color:var(--text); border-radius:8px; padding:7px 9px; font-size:13px; outline:none; }
  input:disabled { opacity:.45; }
  button { background:var(--accent); color:#fff; border:none; border-radius:8px; padding:7px 12px;
           font-size:13px; cursor:pointer; white-space:nowrap; }
  button:hover { filter:brightness(1.08); }
  button:disabled { opacity:.4; cursor:not-allowed; filter:none; }
  button.ghost { background:var(--card2); color:var(--text); border:1px solid var(--line); }
  button.green { background:var(--green); } button.red { background:var(--red); }
  button.sm { padding:4px 8px; font-size:12px; }
  .muted { color:var(--sub); font-size:12px; }
  .ipstatus { font-size:12px; color:var(--sub); margin:2px 0 6px; }
  .ipstatus.warn { color:#E06C6C; }
  .ips { max-height:230px; overflow-y:auto; }
  .ips .ip { display:block; width:100%; text-align:left; background:transparent; color:#5aa9ff;
             font-family:Consolas,Menlo,monospace; padding:5px 8px; border-radius:6px;
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .ips .ip:hover { background:var(--card2); }
  /* 地址按种类分组：公网与局域网的可达范围差别极大，必须各自带一句说明 */
  .kind { margin-top:10px; }
  .kind:first-child { margin-top:0; }
  .kind .kh { font-size:12px; font-weight:600; }
  .kind .kd { font-size:11px; color:var(--sub); margin:1px 0 4px; line-height:1.5; }
  .flexsplit { display:flex; justify-content:space-between; align-items:center; }
  .divider { border-top:1px solid var(--line); margin:11px -13px 0; padding:10px 13px 0; }

  button.ghost.danger { color:#e06c6c; }

  /* 相册卡片网格（简约） */
  #albums { display:grid; grid-template-columns:repeat(auto-fill,minmax(232px,1fr)); gap:12px; }
  .album { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:13px 14px; display:flex; flex-direction:column; gap:9px; }
  .ahead { display:flex; align-items:center; gap:9px; min-width:0; }
  .aicon { width:30px; height:30px; border-radius:8px; background:var(--card2); border:1px solid var(--line);
           display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; }
  .atext { min-width:0; }
  .aname { font-weight:600; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .ameta { color:var(--sub); font-size:12px; }
  .badge { align-self:flex-start; font-size:11px; padding:2px 9px; border-radius:99px; border:1px solid var(--line); color:var(--sub); }
  .badge.active { color:#7fe0a8; border-color:#2f5a44; }
  .badge.expired { color:#e6a35f; border-color:#5e4a2c; }
  .acts { display:flex; gap:6px; flex-wrap:wrap; }
  .empty { text-align:center; padding:38px 20px; color:var(--sub); }
  .empty .emoji { font-size:42px; margin-bottom:12px; }
  .empty .etitle { color:var(--text); font-size:16px; font-weight:600; margin-bottom:6px; }
  .empty .edesc { font-size:13px; line-height:1.7; max-width:440px; margin:0 auto 16px; }
  .shareform { display:none; flex-direction:column; gap:7px; padding:9px; background:var(--card2); border-radius:8px; }
  .links { display:flex; flex-direction:column; }
  .link { border-top:1px solid var(--line); padding-top:8px; margin-top:2px; }
  .link .sub { color:var(--sub); font-size:11px; margin-bottom:6px; }
  .link.exp .sub { color:var(--amber); }
  .link .la { display:flex; gap:6px; align-items:stretch; }
  .link .la .grow { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .iconbtn { padding:5px 9px; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; }
  .iconbtn svg { display:block; }
  .pcopy { color:#9fd0ff; cursor:pointer; border-bottom:1px dashed rgba(159,208,255,.45); }
  .link.exp .pcopy { color:#e6a35f; border-bottom-color:rgba(230,163,95,.45); }
  .checkbox { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--sub); }

  .wrap { max-width:1100px; margin:0 auto; }
  .topbar { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:14px; }
  .topactions { position:relative; display:flex; gap:8px; align-items:center; }
  .chip { background:var(--card2); border:1px solid var(--line); color:var(--text); border-radius:99px;
          padding:6px 13px; font-size:13px; }
  .chip.ok { color:#7fe0a8; border-color:#2f5a44; }
  .chip.warn { color:#e06c6c; border-color:#5e3a3a; }
  .chip.alert { color:#e6a35f; border-color:#5e4a30; }
  /* setChip 跑之前的初始态：半透明。探测挂掉时按钮不会伪装成「一切正常」 */
  .chip.dim { opacity:.55; }
  .toppop { display:none; position:absolute; right:0; top:calc(100% + 6px); width:360px; max-width:84vw;
            background:var(--card); border:1px solid var(--line); border-radius:12px;
            box-shadow:0 12px 32px rgba(0,0,0,.55); padding:11px 13px; z-index:30; }
  .toppop.open { display:block; }
  #helpPop { width:430px; }
  #helpText { font-size:12.5px; line-height:1.7; color:var(--sub); white-space:pre-wrap; max-height:360px; overflow-y:auto; }
  .nphead { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }

  /* 悬浮日志 */
  #logBtn { position:fixed; right:20px; bottom:20px; z-index:40; border-radius:99px; padding:9px 16px;
            box-shadow:0 4px 16px rgba(0,0,0,.45); }
  #logPanel { position:fixed; right:20px; bottom:64px; width:420px; max-width:calc(100vw - 40px); height:320px;
              background:var(--card); border:1px solid var(--line); border-radius:12px; box-shadow:0 10px 32px rgba(0,0,0,.55);
              display:none; flex-direction:column; overflow:hidden; z-index:41; }
  #logPanel.open { display:flex; }
  .lphead { display:flex; justify-content:space-between; align-items:center; padding:9px 12px; border-bottom:1px solid var(--line); font-size:13px; }
  #log { flex:1; background:#141417; overflow-y:auto; padding:8px 12px;
         font-family:Consolas,Menlo,monospace; font-size:12px; line-height:1.6; }
  #log > div { overflow-wrap:anywhere; }
  #log .warn { color:#E6A23C; } #log .ok { color:#67C26B; }

  /* 首次使用向导：独立遮罩，走完三步才进主界面 */
  #wiz { display:none; position:fixed; inset:0; background:rgba(0,0,0,.72); align-items:center;
         justify-content:center; z-index:60; padding:20px; }
  #wiz.open { display:flex; }
  #wiz .box { background:var(--card); border:1px solid var(--line); border-radius:16px;
              width:520px; max-width:100%; max-height:100%; overflow-y:auto; padding:22px 24px 18px;
              box-shadow:0 18px 48px rgba(0,0,0,.6); }
  #wiz .dots { display:flex; gap:6px; justify-content:center; margin-bottom:16px; }
  #wiz .dots i { width:7px; height:7px; border-radius:99px; background:var(--line); }
  #wiz .dots i.on { background:var(--accent); }
  #wiz h2 { font-size:18px; margin:0 0 6px; }
  #wiz .wdesc { color:var(--sub); font-size:13px; line-height:1.75; margin-bottom:14px; white-space:pre-wrap; }
  #wiz .wbody { min-height:120px; }
  #wiz .wfoot { display:flex; justify-content:space-between; align-items:center; margin-top:18px; }
  #wiz .picked { background:var(--card2); border:1px solid var(--line); border-radius:8px;
                 padding:8px 10px; font-size:12px; word-break:break-all; margin-top:9px; color:var(--sub); }
  #wiz .picked.ok { color:var(--text); }

  /* 二维码弹层 */
  #qr { display:none; position:fixed; inset:0; background:rgba(0,0,0,.6); align-items:center; justify-content:center; z-index:50; }
  #qr .box { background:#fff; border-radius:14px; padding:18px; text-align:center; max-width:300px; }
  #qr img { width:240px; height:240px; image-rendering:pixelated; }
  #qr .u { color:#333; font-size:11px; word-break:break-all; margin:10px 0 4px; font-family:Consolas,monospace; }
  #qr .h { color:#666; font-size:12px; margin-bottom:8px; }
  #qrSwitch { display:flex; gap:6px; justify-content:center; margin-bottom:10px; }
  #qrSwitch:empty { display:none; }
</style>
</head>
<body>
<div class="wrap">
  <div id="srvErr" class="banner">
    <span id="srvErrMsg"></span>
    <button class="ghost sm" style="margin-left:6px" onclick="openPortSetting(event)">去改端口</button>
  </div>
  <div class="topbar">
    <div>
      <h1>私有相册服务<span class="ver">v__PICSHARE_VERSION__</span></h1>
      <div class="subtitle">极速预览 · 智能缓存 · 安全访问</div>
    </div>
    <div class="topactions">
      <button id="netChip" class="chip dim" onclick="toggleNet(event)">🌐 网络</button>
      <button class="ghost sm" onclick="toggleHelp(event)">❓ 帮助</button>
      <div id="netPop" class="toppop">
        <div class="nphead">
          <span class="label" style="margin:0">网络与访问</span>
          <button class="ghost sm" onclick="refreshNetwork()">🔄 刷新</button>
        </div>
        <div class="ips" id="ips"></div>
        <!-- 端口和访问地址本就是一件事：链接里含端口号。放在一起，也不占首页位置 -->
        <div class="divider">
          <div class="label" style="font-size:13px">🔌 服务端口</div>
          <div class="row">
            <input id="portInput" type="text" inputmode="numeric" placeholder="5000">
            <button class="sm" onclick="applyPort()">应用</button>
          </div>
          <div class="muted" style="margin-top:7px; line-height:1.6">
            端口被占用时可改用其它端口。改完请把链接重新复制发给客户。
          </div>
        </div>
      </div>
      <div id="helpPop" class="toppop">
        <div class="nphead">
          <span class="label" style="margin:0">使用帮助</span>
          <span>
            <button class="ghost sm" onclick="replayWizard()">重看引导</button>
            <button class="ghost sm" onclick="toggleHelp()">关闭</button>
          </span>
        </div>
        <div id="helpText"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="label">📂 相册根目录</div>
    <div class="row">
      <input id="baseDir" type="text" readonly placeholder="尚未选择">
      <button onclick="chooseFolder()">选择</button>
    </div>
  </div>

  <div class="card">
    <div class="flexsplit" style="margin-bottom:10px">
      <span class="label" style="margin:0">🔗 相册</span>
      <button class="ghost sm" onclick="loadAlbums(true)">🔄 刷新相册</button>
    </div>
    <div id="albums"></div>
  </div>
</div>

<button id="logBtn" class="ghost" onclick="toggleLog()">📜 运行日志</button>
<div id="logPanel">
  <div class="lphead">
    <span class="label" style="margin:0">运行日志</span>
    <span>
      <button class="ghost sm" onclick="clearLog()">清空</button>
      <button class="ghost sm" onclick="toggleLog()">关闭</button>
    </span>
  </div>
  <div id="log"></div>
</div>

<div id="wiz">
  <div class="box">
    <div class="dots"><i id="d1"></i><i id="d2"></i><i id="d3"></i></div>
    <h2 id="wizTitle"></h2>
    <div class="wdesc" id="wizDesc"></div>
    <div class="wbody" id="wizBody"></div>
    <div class="wfoot">
      <button class="ghost sm" onclick="wizSkip()">跳过</button>
      <button id="wizNext" onclick="wizNext()">下一步</button>
    </div>
  </div>
</div>

<div id="qr" onclick="closeQr(event)">
  <div class="box">
    <div class="h">扫码打开 / 转发给客户</div>
    <img id="qrImg" alt="qr">
    <div class="u" id="qrUrl"></div>
    <div id="qrSwitch"></div>
    <button class="ghost sm" id="qrClose" onclick="closeQr()">关闭</button>
  </div>
</div>

<script>
  let api = null;
  const IC_QR='<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM12 12h3v3h-3zM18 12h3v3h-3zM12 18h3v3h-3zM18 18h3v3h-3z"/></svg>';
  const IC_TRASH='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V5h6v2M7 7l1 13h8l1-13"/></svg>';

  function copyText(text){
    try { const ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); } catch(e){}
  }
  function flash(el,msg){ const o=el.textContent; el.textContent='✅ '+msg; setTimeout(()=>{el.textContent=o;},900); }

  async function refreshState(){
    const s=await api.get_state();
    document.getElementById('baseDir').value=s.base_dir||'';
    // 对外服务没起来时把原因摆在最顶上；绑定只在启动时发生一次，无需轮询
    const b=document.getElementById('srvErr');
    document.getElementById('srvErrMsg').textContent='⚠️ '+(s.server_error||'');
    b.classList.toggle('show', !!s.server_error);
    document.getElementById('portInput').value=s.port||'';
    return s;
  }

  // 端口被占用时改端口是唯一的自救手段，横幅必须能直接把人带到那个输入框。
  // 必须 stopPropagation：文档上挂着「点 .topactions 之外就关闭浮层」的监听，
  // 这个按钮在横幅里、不在 .topactions 内，不拦住冒泡就会开了立刻被关掉。
  function openPortSetting(e){
    if(e) e.stopPropagation();
    document.getElementById('helpPop').classList.remove('open');
    document.getElementById('netPop').classList.add('open');
    const i=document.getElementById('portInput'); i.focus(); i.select();
  }

  async function applyPort(){
    const v=document.getElementById('portInput').value.trim();
    if(!confirm('改端口后，之前发出去的链接里的端口号就过时了，需要重新复制发给客户。\n'
              + '（客户已选的照片和口令不受影响）\n\n确定改为 '+v+' 吗？')) return;
    const r=await api.set_port(v);
    if(!r.ok){ alert(r.error); return; }
    await refreshState();   // 撤掉可能存在的启动失败横幅，并回填实际端口
    loadAlbums();           // 链接 URL 含端口号，需按新端口重新渲染
  }
  async function chooseFolder(){ const p=await api.choose_folder(); if(p){ document.getElementById('baseDir').value=p; loadAlbums(); } }

  // 文案固定为「网络」：常态下顶栏只需要一个干净的入口，地址明细都在弹层里。
  // 但它同时是状态灯——只有局域网地址时，链接发给不在现场的客户是打不开的——
  // 所以两种异常都追加 ⚠️，不让颜色单独承载警告（扫一眼或色觉差异时颜色靠不住）。
  function setChip(addrs){
    const c=document.getElementById('netChip');
    const pub=addrs.some(a=>a.kind==='public'), lan=addrs.some(a=>a.kind==='lan');
    if(pub){ c.className='chip ok'; c.textContent='🌐 网络';
             c.title='公网地址可用，客户在任何网络下都能打开'; }
    else if(lan){ c.className='chip alert'; c.textContent='🌐 网络 ⚠️';
             c.title='只有局域网地址，链接发给不在现场的客户打不开'; }
    else { c.className='chip warn'; c.textContent='🌐 网络 ⚠️';
             c.title='未检测到任何可用地址，请检查网络连接'; }
  }
  function toggleNet(e){ if(e) e.stopPropagation();
    document.getElementById('helpPop').classList.remove('open');
    document.getElementById('netPop').classList.toggle('open'); }

  let helpLoaded=false;
  async function toggleHelp(e){ if(e) e.stopPropagation();
    if(!helpLoaded){ document.getElementById('helpText').textContent=await api.help_text(); helpLoaded=true; }
    document.getElementById('netPop').classList.remove('open');
    document.getElementById('helpPop').classList.toggle('open'); }

  // 两种地址的可达范围差别极大，界面上一律成对出现：标题 + 一句人话
  const KIND = {
    public: { icon:'🌐', name:'公网', desc:'客户在任何网络下都能打开' },
    lan:    { icon:'📶', name:'局域网', desc:'只有连同一个 WiFi / 路由器的人能打开，适合当面选片' }
  };
  let lastAddrs=[];

  async function refreshNetwork(){
    document.getElementById('ips').innerHTML='<div class="ipstatus">检测中…</div>';
    renderAddrs(await api.get_addresses(true));
  }
  function ipRow(o){
    const b=document.createElement('button'); b.className='ip'; b.textContent=o.url; b.title='点击复制 '+o.url;
    b.onclick=()=>{ copyText(o.url); flash(b,'已复制'); }; return b;
  }
  function renderAddrs(addrs){
    lastAddrs=addrs;
    setChip(addrs);
    const box=document.getElementById('ips'); box.innerHTML='';
    if(!addrs.length){
      const w=document.createElement('div'); w.className='ipstatus warn';
      w.textContent='⚠️ 未检测到任何可用地址，请检查网络连接'; box.appendChild(w); return;
    }
    ['public','lan'].forEach(k=>{
      const group=addrs.filter(a=>a.kind===k);
      if(!group.length) return;
      const g=document.createElement('div'); g.className='kind';
      const h=document.createElement('div'); h.className='kh';
      h.textContent=KIND[k].icon+' '+KIND[k].name; g.appendChild(h);
      const d=document.createElement('div'); d.className='kd'; d.textContent=KIND[k].desc; g.appendChild(d);
      group.forEach(o=>g.appendChild(ipRow(o)));
      box.appendChild(g);
    });
    if(!addrs.some(a=>a.kind==='public')){
      const w=document.createElement('div'); w.className='ipstatus warn'; w.style.marginTop='8px';
      w.textContent='⚠️ 没有公网 IPv6，链接发给不在现场的客户打不开';
      box.appendChild(w);
    }
  }

  function badgeText(a){
    if(a.badge==='active') return a.days_left==null ? '🔗 永久有效' : ('🔗 有效 · 剩 '+a.days_left+' 天');
    if(a.badge==='expired') return '链接已过期';
    return '未分享';
  }

  function emptyState(emoji, title, desc, btnText, ghost){
    const box=document.getElementById('albums');
    box.innerHTML='';
    const d=document.createElement('div'); d.className='empty';
    const e=document.createElement('div'); e.className='emoji'; e.textContent=emoji; d.appendChild(e);
    const t=document.createElement('div'); t.className='etitle'; t.textContent=title; d.appendChild(t);
    const p=document.createElement('div'); p.className='edesc'; p.textContent=desc; d.appendChild(p);
    const b=document.createElement('button'); b.textContent=btnText; if(ghost) b.className='ghost';
    b.onclick=chooseFolder; d.appendChild(b);
    box.appendChild(d);
  }

  // force=true 由「🔄 刷新相册」传入：丢弃后端张数缓存重新点数，加了照片能立刻看到
  async function loadAlbums(force=false){
    const data=await api.get_albums(force);
    if(!data.base_dir_ok){
      if(data.reason==='missing')
        emptyState('📁','找不到上次的根目录','原来的相册根目录可能被移动或删除了，请重新选择。','重新选择文件夹', false);
      else
        emptyState('📁','选择照片根目录开始','指定一个存放各相册子文件夹的主目录，PicShare 会自动列出其中的相册并生成分享链接。','选择文件夹', false);
      return;
    }
    if(!data.albums.length){
      emptyState('🗂️','这个目录下还没有相册','在根目录下为每个相册建一个子文件夹（例如「2025春季婚礼」），把照片放进去，再点右上角「🔄 刷新相册」。','更换根目录', true);
      return;
    }
    const box=document.getElementById('albums');
    box.innerHTML='';
    data.albums.forEach(a=>box.appendChild(buildCard(a)));
  }

  function buildCard(a){
    const el=document.createElement('div'); el.className='album';

    const head=document.createElement('div'); head.className='ahead';
    const ic=document.createElement('div'); ic.className='aicon'; ic.textContent='📁'; head.appendChild(ic);
    const txt=document.createElement('div'); txt.className='atext';
    const nm=document.createElement('div'); nm.className='aname'; nm.textContent=a.name; nm.title=a.name; txt.appendChild(nm);
    const meta=document.createElement('div'); meta.className='ameta'; meta.textContent=a.photos+' 张 · 已选 '+a.marked; txt.appendChild(meta);
    head.appendChild(txt); el.appendChild(head);

    const badge=document.createElement('div'); badge.className='badge '+a.badge; badge.textContent=badgeText(a); el.appendChild(badge);

    const acts=document.createElement('div'); acts.className='acts';
    const bShare=document.createElement('button'); bShare.className='sm'; bShare.textContent='分享'; acts.appendChild(bShare);
    const bOpen=document.createElement('button'); bOpen.className='sm ghost'; bOpen.textContent='收藏夹';
    bOpen.onclick=()=>api.open_marked_folder(a.name); acts.appendChild(bOpen);
    el.appendChild(acts);

    // 就地分享表单
    const form=document.createElement('div'); form.className='shareform';
    form.innerHTML='<div class="row"><span class="muted">有效期</span>'+
      '<select><option value="3">3 天</option><option value="7">7 天</option><option value="14">14 天</option></select></div>'+
      '<label class="checkbox"><input type="checkbox"> 加访问口令</label>'+
      '<input type="text" placeholder="默认口令为空" disabled>'+
      '<div style="text-align:right"><button class="sm">生成并复制</button></div>';
    const sel=form.querySelector('select');
    const cb=form.querySelector('input[type=checkbox]');
    const pw=form.querySelector('input[type=text]');
    cb.onchange=()=>{ pw.disabled=!cb.checked; if(cb.checked && !pw.value.trim()) api.generate_passcode().then(p=>pw.value=p); if(!cb.checked) pw.value=''; };
    form.querySelector('button').onclick=async ()=>{
      const r=await api.create_token(a.name, sel.value, cb.checked?pw.value:'');
      if(!r.ok){ alert(r.error||'生成失败'); return; }
      copyText(r.urls[0].url);          // urls 已按公网优先排好
      showQr(r.urls, r.passcode);
      loadAlbums();
    };
    bShare.onclick=()=>{ form.style.display = form.style.display==='flex' ? 'none' : 'flex'; };
    el.appendChild(form);

    // 该相册的链接列表
    if(a.links.length){
      const links=document.createElement('div'); links.className='links';
      a.links.forEach(l=>links.appendChild(buildLink(l)));
      el.appendChild(links);
    }
    return el;
  }

  function buildLink(l){
    const d=document.createElement('div'); d.className='link'+(l.expired?' exp':'');

    const sub=document.createElement('div'); sub.className='sub';
    sub.appendChild(document.createTextNode(l.expired ? '已过期' : ('有效期至 '+(l.expires||'永久'))));
    if(l.passcode){
      sub.appendChild(document.createTextNode(' · 口令 '));
      const pc=document.createElement('span'); pc.className='pcopy'; pc.textContent=l.passcode; pc.title='点击复制口令';
      pc.onclick=()=>{ copyText(l.passcode); const o=pc.textContent; pc.textContent='✅ 已复制'; setTimeout(()=>{pc.textContent=o;},900); };
      sub.appendChild(pc);
    } else {
      sub.appendChild(document.createTextNode(' · 无口令'));
    }
    d.appendChild(sub);

    const la=document.createElement('div'); la.className='la';
    // 只有一种地址时保持原样一个「复制链接」；两种都有时才分开，免得常见情况平白多个按钮
    const kinds=[...new Set(l.urls.map(u=>u.kind))];
    kinds.forEach(k=>{
      const u=l.urls.find(x=>x.kind===k);
      const b=document.createElement('button'); b.className='sm grow';
      b.textContent = kinds.length>1 ? ('复制'+KIND[k].name) : '复制链接';
      b.title = KIND[k].desc+'\n'+u.url;
      b.onclick=()=>{ copyText(u.url); flash(b,'已复制'); };
      la.appendChild(b);
    });
    const bq=document.createElement('button'); bq.className='sm ghost iconbtn'; bq.innerHTML=IC_QR; bq.title='二维码';
    bq.onclick=()=>showQr(l.urls, l.passcode); la.appendChild(bq);
    const br=document.createElement('button'); br.className='sm ghost iconbtn danger'; br.innerHTML=IC_TRASH; br.title='撤销';
    br.onclick=()=>{ if(confirm('撤销后该链接立即失效，确定吗？')) api.revoke_token(l.token).then(()=>loadAlbums()); };
    la.appendChild(br);
    d.appendChild(la);
    return d;
  }

  // urls 为 [{kind,url}]，默认展示第一个（公网优先）；两种都有时给个切换
  async function showQr(urls, passcode, idx){
    idx = idx || 0;
    const cur = urls[idx] || urls[0];
    const uri = await api.make_qr(cur.url);
    document.getElementById('qrImg').src=uri;
    document.getElementById('qrUrl').textContent=cur.url+(passcode?'  （口令 '+passcode+'）':'');
    const sw=document.getElementById('qrSwitch'); sw.innerHTML='';
    if(urls.length>1){
      urls.forEach((u,i)=>{
        const b=document.createElement('button'); b.className='sm'+(i===idx?'':' ghost');
        b.textContent=KIND[u.kind].icon+' '+KIND[u.kind].name; b.title=KIND[u.kind].desc;
        b.onclick=()=>showQr(urls, passcode, i);
        sw.appendChild(b);
      });
    }
    document.getElementById('qr').style.display='flex';
  }
  function closeQr(e){
    // 仅在点击遮罩背景或「关闭」按钮时关闭。这里必须认 id 而不是 tagName——
    // 框里还有切换地址的按钮，按 tagName 判断会把它们也当成关闭。
    if(e && e.target.id!=='qr' && e.target.id!=='qrClose') return;
    document.getElementById('qr').style.display='none';
  }

  function toggleLog(){ document.getElementById('logPanel').classList.toggle('open'); }

  let logGen=0;
  function renderLogs(logs){
    const box=document.getElementById('log');
    box.textContent='';
    for(const l of logs){
      const d=document.createElement('div');
      d.className=/⚠️|❌|🚨/.test(l.msg)?'warn':'ok';
      d.textContent='['+l.time+'] '+l.msg;
      box.appendChild(d);
    }
    box.scrollTop=box.scrollHeight;
  }
  function clearLog(){ logGen++; api.clear_logs().then(()=>renderLogs([])); }
  async function pollLogs(){
    const g=logGen;
    try{ const logs=await api.get_logs(); if(g===logGen) renderLogs(logs); }catch(e){}
  }

  // ====== 首次使用向导 ======
  // 只做「探测 + 说明」，不让用户选协议——摄影师不知道该选哪个，程序自己能测出来。
  let wizStep=0, wizDir='';

  function wizOpen(){ wizStep=0; document.getElementById('wiz').classList.add('open'); wizRender(); }
  function wizClose(){ document.getElementById('wiz').classList.remove('open'); }
  async function wizSkip(){ await api.finish_onboarding(); wizClose(); }
  async function replayWizard(){ document.getElementById('helpPop').classList.remove('open'); wizOpen(); }

  async function wizNext(){
    if(wizStep<2){ wizStep++; wizRender(); return; }
    await api.finish_onboarding();
    wizClose();
    refreshState(); loadAlbums();
  }

  function wizRender(){
    for(let i=1;i<=3;i++) document.getElementById('d'+i).className = (i===wizStep+1?'on':'');
    const title=document.getElementById('wizTitle'), desc=document.getElementById('wizDesc');
    const body=document.getElementById('wizBody'), next=document.getElementById('wizNext');
    body.innerHTML=''; next.textContent = wizStep===2 ? '开始使用' : '下一步';

    if(wizStep===0){
      title.textContent='欢迎使用 PicShare';
      desc.textContent='把照片放在自己电脑上，生成一条专属链接发给客户，'
                     + '客户在浏览器里浏览、标记想要的照片。照片不上传任何云端。\n\n'
                     + '第一步：选一个「照片根目录」——存放各个相册子文件夹的主目录。';
      const b=document.createElement('button'); b.textContent='选择文件夹';
      const picked=document.createElement('div'); picked.className='picked';
      picked.textContent = wizDir || '尚未选择';
      if(wizDir) picked.classList.add('ok');
      b.onclick=async ()=>{
        const pth=await api.choose_folder();
        if(pth){ wizDir=pth; picked.textContent=pth; picked.classList.add('ok'); next.disabled=false; }
      };
      body.appendChild(b); body.appendChild(picked);
      next.disabled=!wizDir;
      return;
    }

    next.disabled=false;
    if(wizStep===1){
      title.textContent='看看你的网络能做什么';
      desc.textContent='PicShare 会自动探测客户能用哪些地址访问你的电脑，你不用选。';
      const box=document.createElement('div'); box.className='ips'; box.id='wizIps';
      box.innerHTML='<div class="ipstatus">检测中…</div>';
      body.appendChild(box);
      api.get_addresses(true).then(addrs=>{
        renderAddrs(addrs);                       // 顺带把顶栏 chip 和弹层一起刷新
        box.innerHTML='';
        if(!addrs.length){
          box.innerHTML='<div class="ipstatus warn">⚠️ 没有探测到可用地址。'
                      + '先确认网线或 WiFi 已连上，再点右上角「网络」里的「刷新」重试。</div>';
          return;
        }
        ['public','lan'].forEach(k=>{
          const g=addrs.filter(a=>a.kind===k);
          if(!g.length) return;
          const d=document.createElement('div'); d.className='kind';
          d.innerHTML='<div class="kh">'+KIND[k].icon+' '+KIND[k].name+' · 可用</div>'
                     +'<div class="kd">'+KIND[k].desc+'</div>';
          box.appendChild(d);
        });
        if(!addrs.some(a=>a.kind==='public')){
          const w=document.createElement('div'); w.className='ipstatus warn'; w.style.marginTop='8px';
          w.textContent='没有公网 IPv6，说明你的宽带或路由器还没开通 IPv6。'
                      + '现在只能当面选片；想远程发给客户，需要先开通 IPv6。';
          box.appendChild(w);
        }
      });
      return;
    }

    title.textContent='接下来这样用';
    desc.textContent='';
    const ol=document.createElement('div'); ol.className='wdesc'; ol.style.marginBottom='0';
    ol.textContent='1. 在刚才选的根目录下，为每个相册建一个子文件夹（例如「2025春季婚礼」），把照片放进去。\n'
                 + '2. 回到主界面点「🔄 刷新相册」，相册就会列出来。\n'
                 + '3. 在相册上点「分享」，设好有效期（需要的话加个访问口令），生成并复制链接。\n'
                 + '4. 把链接发给客户。加了口令的话，口令要另外发，别和链接放在一起。\n\n'
                 + '客户选完之后，点相册上的「收藏夹」就能把选中的原图导出到本地。';
    ol.style.whiteSpace='pre-wrap';
    body.appendChild(ol);
  }

  function init(){
    api=window.pywebview.api;
    refreshState().then(s=>{
      loadAlbums();
      wizDir = s.base_dir || '';
      if(!s.onboarded) wizOpen();     // 没走完引导就先弹，走完/跳过后才进主界面
    });
    refreshNetwork(); pollLogs(); setInterval(pollLogs,1500);
    // 点空白处关闭顶部浮层（网络 / 帮助）
    document.addEventListener('click', e=>{ if(!e.target.closest('.topactions')){
      document.getElementById('netPop').classList.remove('open');
      document.getElementById('helpPop').classList.remove('open'); } });
  }
  window.addEventListener('pywebviewready', init);
</script>
</body>
</html>'''
