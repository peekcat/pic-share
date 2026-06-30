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
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px; margin-bottom:12px; }
  .label { font-weight:600; margin-bottom:8px; }
  .row { display:flex; gap:8px; align-items:center; }
  input[type=text], select { flex:1; background:var(--card2); border:1px solid var(--line);
          color:var(--text); border-radius:8px; padding:7px 9px; font-size:13px; outline:none; }
  input:disabled { opacity:.45; }
  button { background:var(--accent); color:#fff; border:none; border-radius:8px; padding:7px 12px;
           font-size:13px; cursor:pointer; white-space:nowrap; }
  button:hover { filter:brightness(1.08); }
  button.ghost { background:var(--card2); color:var(--text); border:1px solid var(--line); }
  button.green { background:var(--green); } button.red { background:var(--red); }
  button.sm { padding:4px 8px; font-size:12px; }
  .muted { color:var(--sub); font-size:12px; }
  .ips .ip { display:block; width:100%; text-align:left; background:transparent; color:#5aa9ff;
             font-family:Consolas,Menlo,monospace; padding:5px 8px; border-radius:6px; }
  .ips .ip:hover { background:var(--card2); }
  .flexsplit { display:flex; justify-content:space-between; align-items:center; }

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
  .shareform { display:none; flex-direction:column; gap:7px; padding:9px; background:var(--card2); border-radius:8px; }
  .links { display:flex; flex-direction:column; }
  .link { border-top:1px solid var(--line); padding-top:8px; margin-top:2px; }
  .link .sub { color:var(--sub); font-size:11px; margin-bottom:6px; }
  .link.exp .sub { color:var(--amber); }
  .link .la { display:flex; gap:6px; flex-wrap:wrap; }
  .checkbox { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--sub); }

  .wrap { max-width:1100px; margin:0 auto; }
  .toprow { display:flex; gap:12px; align-items:flex-start; flex-wrap:wrap; }
  .toprow > .card { flex:1; min-width:280px; margin-bottom:12px; }

  /* 悬浮日志 */
  #logBtn { position:fixed; right:20px; bottom:20px; z-index:40; border-radius:99px; padding:9px 16px;
            box-shadow:0 4px 16px rgba(0,0,0,.45); }
  #logPanel { position:fixed; right:20px; bottom:64px; width:420px; max-width:calc(100vw - 40px); height:320px;
              background:var(--card); border:1px solid var(--line); border-radius:12px; box-shadow:0 10px 32px rgba(0,0,0,.55);
              display:none; flex-direction:column; overflow:hidden; z-index:41; }
  #logPanel.open { display:flex; }
  .lphead { display:flex; justify-content:space-between; align-items:center; padding:9px 12px; border-bottom:1px solid var(--line); font-size:13px; }
  #log { flex:1; background:#141417; overflow-y:auto; padding:8px 12px;
         font-family:Consolas,Menlo,monospace; font-size:12px; line-height:1.6; white-space:pre-wrap; }
  #log .warn { color:#E6A23C; } #log .ok { color:#67C26B; }

  /* 二维码弹层 */
  #qr { display:none; position:fixed; inset:0; background:rgba(0,0,0,.6); align-items:center; justify-content:center; z-index:50; }
  #qr .box { background:#fff; border-radius:14px; padding:18px; text-align:center; max-width:300px; }
  #qr img { width:240px; height:240px; image-rendering:pixelated; }
  #qr .u { color:#333; font-size:11px; word-break:break-all; margin:10px 0 4px; font-family:Consolas,monospace; }
  #qr .h { color:#666; font-size:12px; margin-bottom:8px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>IPv6 相册服务</h1>
  <div class="subtitle">极速预览 · 智能缓存 · 安全访问</div>

  <div class="toprow">
    <div class="card">
      <div class="label">📂 相册根目录</div>
      <div class="row">
        <input id="baseDir" type="text" readonly placeholder="尚未选择">
        <button onclick="chooseFolder()">选择</button>
      </div>
    </div>

    <div class="card">
      <div class="flexsplit" style="margin-bottom:6px">
        <span class="label" style="margin:0">🌐 公网访问地址</span>
        <span>
          <button class="ghost sm" onclick="refreshNetwork()">🔄 刷新</button>
          <button class="ghost sm" onclick="showHelp()">❓ 帮助</button>
        </span>
      </div>
      <div class="muted">点击地址复制完整链接</div>
      <div class="ips" id="ips"></div>
    </div>
  </div>

  <div class="card">
    <div class="flexsplit" style="margin-bottom:10px">
      <span class="label" style="margin:0">🔗 相册</span>
      <button class="ghost sm" onclick="loadAlbums()">🔄 刷新相册</button>
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

<div id="qr" onclick="closeQr(event)">
  <div class="box">
    <div class="h">扫码打开 / 转发给客户</div>
    <img id="qrImg" alt="qr">
    <div class="u" id="qrUrl"></div>
    <button class="ghost sm" onclick="closeQr()">关闭</button>
  </div>
</div>

<script>
  let api = null;

  function copyText(text){
    try { const ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); } catch(e){}
  }
  function flash(el,msg){ const o=el.textContent; el.textContent='✅ '+msg; setTimeout(()=>{el.textContent=o;},900); }

  async function refreshState(){ const s=await api.get_state(); document.getElementById('baseDir').value=s.base_dir||''; }
  async function chooseFolder(){ const p=await api.choose_folder(); if(p){ document.getElementById('baseDir').value=p; loadAlbums(); } }

  async function refreshNetwork(){ document.getElementById('ips').innerHTML='<div class="muted">检测中…</div>'; renderIps(await api.get_ipv6(true)); }
  function renderIps(ips){
    const box=document.getElementById('ips');
    if(!ips.length){ box.innerHTML='<div class="muted" style="color:#E06C6C">⚠️ 未检测到 IPv6 地址</div>'; return; }
    box.innerHTML='';
    ips.forEach(o=>{ const b=document.createElement('button'); b.className='ip'; b.textContent=o.url;
      b.onclick=()=>{ copyText(o.url); flash(b,'已复制'); }; box.appendChild(b); });
  }

  function badgeText(a){
    if(a.badge==='active') return a.days_left==null ? '🔗 永久有效' : ('🔗 有效 · 剩 '+a.days_left+' 天');
    if(a.badge==='expired') return '链接已过期';
    return '未分享';
  }

  async function loadAlbums(){
    const data=await api.get_albums();
    const box=document.getElementById('albums');
    if(!data.base_dir_ok){ box.innerHTML='<div class="muted" style="padding:6px 2px">请先选择有效的相册根目录。</div>'; return; }
    if(!data.albums.length){ box.innerHTML='<div class="muted" style="padding:6px 2px">根目录下没有相册子文件夹。</div>'; return; }
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
      copyText(r.url);
      showQr(r.url, r.passcode);
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
    sub.textContent=(l.expired?'已过期 · ':'有效期至 '+(l.expires||'永久'))+(l.passcode?' · 口令 '+l.passcode:' · 无口令');
    d.appendChild(sub);
    const la=document.createElement('div'); la.className='la';
    const bc=document.createElement('button'); bc.className='sm'; bc.textContent='复制链接';
    bc.onclick=()=>{ copyText(l.url); flash(bc,'已复制'); }; la.appendChild(bc);
    const bq=document.createElement('button'); bq.className='sm ghost'; bq.textContent='二维码';
    bq.onclick=()=>showQr(l.url, l.passcode); la.appendChild(bq);
    if(l.passcode){ const bp=document.createElement('button'); bp.className='sm ghost'; bp.textContent='复制口令';
      bp.onclick=()=>{ copyText(l.passcode); flash(bp,'已复制'); }; la.appendChild(bp); }
    const br=document.createElement('button'); br.className='sm ghost danger'; br.textContent='撤销';
    br.onclick=()=>{ if(confirm('撤销后该链接立即失效，确定吗？')) api.revoke_token(l.token).then(loadAlbums); };
    la.appendChild(br);
    d.appendChild(la);
    return d;
  }

  async function showQr(url, passcode){
    const uri=await api.make_qr(url);
    document.getElementById('qrImg').src=uri;
    document.getElementById('qrUrl').textContent=url+(passcode?'  （口令 '+passcode+'）':'');
    document.getElementById('qr').style.display='flex';
  }
  function closeQr(e){
    // 仅在点击遮罩背景或「关闭」按钮时关闭；点框内的图/文字不关闭
    if(e && e.target.id!=='qr' && e.target.tagName!=='BUTTON') return;
    document.getElementById('qr').style.display='none';
  }

  async function showHelp(){ alert(await api.help_text()); }

  function toggleLog(){ document.getElementById('logPanel').classList.toggle('open'); }
  function clearLog(){ api.clear_logs().then(()=>{ document.getElementById('log').textContent=''; }); }

  async function pollLogs(){
    try{ const logs=await api.get_logs(); const box=document.getElementById('log');
      box.innerHTML=logs.map(l=>{ const w=/⚠️|❌|🚨/.test(l.msg); return '<span class="'+(w?'warn':'ok')+'">['+l.time+'] '+l.msg+'</span>'; }).join('\n');
      box.scrollTop=box.scrollHeight; }catch(e){}
  }

  function init(){ api=window.pywebview.api; refreshState().then(loadAlbums); refreshNetwork(); pollLogs(); setInterval(pollLogs,1500); }
  window.addEventListener('pywebviewready', init);
</script>
</body>
</html>'''
