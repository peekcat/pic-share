# 管理端单页界面（pywebview 直接以 html= 加载，无需静态文件，打包友好）

ADMIN_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PicShare 管理</title>
<style>
  :root { --bg:#1b1b1e; --card:#242429; --card2:#2c2c33; --line:#36363d;
          --text:#eaeaea; --sub:#9a9aa3; --accent:#0A84FF; --green:#2FA572; --red:#C0392B; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:"Microsoft YaHei UI","PingFang SC",-apple-system,sans-serif;
         background:var(--bg); color:var(--text); font-size:14px; }
  .wrap { padding:18px 20px 24px; }
  h1 { font-size:20px; margin:0; }
  .subtitle { color:var(--sub); font-size:12px; margin:2px 0 16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:14px 16px; margin-bottom:14px; }
  .label { font-weight:600; margin-bottom:8px; }
  .row { display:flex; gap:8px; align-items:center; }
  input[type=text], select { flex:1; background:var(--card2); border:1px solid var(--line);
          color:var(--text); border-radius:8px; padding:8px 10px; font-size:13px; outline:none; }
  input:disabled { opacity:.45; }
  button { background:var(--accent); color:#fff; border:none; border-radius:8px;
           padding:8px 14px; font-size:13px; cursor:pointer; white-space:nowrap; }
  button:hover { filter:brightness(1.08); }
  button.ghost { background:var(--card2); color:var(--text); border:1px solid var(--line); }
  button.green { background:var(--green); }
  button.red { background:var(--red); }
  button.sm { padding:5px 9px; font-size:12px; }
  .ips .ip { display:block; width:100%; text-align:left; background:transparent; color:#5aa9ff;
             font-family:Consolas,Menlo,monospace; padding:6px 8px; border-radius:6px; }
  .ips .ip:hover { background:var(--card2); }
  .muted { color:var(--sub); font-size:12px; }
  .grid2 { display:grid; grid-template-columns:auto 1fr; gap:10px 12px; align-items:center; }
  .tok { background:var(--card2); border:1px solid var(--line); border-radius:10px;
         padding:10px 12px; margin-top:8px; }
  .tok .name { font-weight:600; }
  .tok .sub { color:var(--sub); font-size:12px; margin:2px 0 8px; }
  .tok .acts { display:flex; gap:6px; flex-wrap:wrap; }
  #log { background:#141417; border:1px solid var(--line); border-radius:8px; height:150px;
         overflow-y:auto; padding:8px 10px; font-family:Consolas,Menlo,monospace; font-size:12px;
         line-height:1.6; white-space:pre-wrap; }
  #log .warn { color:#E6A23C; } #log .ok { color:#67C26B; }
  .checkbox { display:flex; align-items:center; gap:6px; }
  .flexsplit { display:flex; justify-content:space-between; align-items:center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>IPv6 相册服务</h1>
  <div class="subtitle">极速预览 · 智能缓存 · 安全访问</div>

  <div class="card">
    <div class="label">📂 相册根目录</div>
    <div class="row">
      <input id="baseDir" type="text" readonly placeholder="尚未选择">
      <button onclick="chooseFolder()">选择</button>
    </div>
  </div>

  <div class="card">
    <div class="label">🌐 公网访问地址</div>
    <div class="muted" id="ipHint">点击任意地址复制完整链接</div>
    <div class="ips" id="ips"></div>
    <div class="row" style="margin-top:10px">
      <button class="ghost" onclick="refreshNetwork()">🔄 刷新网络</button>
      <button class="ghost" onclick="showHelp()">❓ 帮助</button>
    </div>
  </div>

  <div class="card">
    <div class="label">🔗 相册访问管理</div>
    <div class="grid2">
      <span>相册</span>
      <select id="album"></select>
      <span>有效期</span>
      <select id="expiry">
        <option value="3">3 天</option><option value="7">7 天</option><option value="14">14 天</option>
      </select>
      <span>口令</span>
      <div class="row">
        <label class="checkbox"><input type="checkbox" id="usePass" onchange="togglePass()"></label>
        <input id="passcode" type="text" placeholder="默认口令为空" disabled>
      </div>
    </div>
    <div style="text-align:right; margin-top:12px">
      <button class="green" onclick="generate()">生成并复制链接</button>
    </div>
    <div id="tokens" style="margin-top:8px"></div>
  </div>

  <div class="card">
    <div class="flexsplit" style="margin-bottom:8px">
      <span class="label" style="margin:0">运行日志</span>
      <button class="ghost sm" onclick="api.clear_logs().then(()=>{document.getElementById('log').textContent=''})">清空</button>
    </div>
    <div id="log"></div>
  </div>
</div>

<script>
  let api = null;

  function copyText(text) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta);
    } catch (e) {}
  }

  async function refreshState() {
    const s = await api.get_state();
    document.getElementById('baseDir').value = s.base_dir || '';
  }

  async function chooseFolder() {
    const p = await api.choose_folder();
    if (p) { document.getElementById('baseDir').value = p; loadAlbums(); }
  }

  async function refreshNetwork() {
    document.getElementById('ips').innerHTML = '<div class="muted">检测中…</div>';
    renderIps(await api.get_ipv6(true));
  }

  function renderIps(ips) {
    const box = document.getElementById('ips');
    if (!ips.length) {
      box.innerHTML = '<div class="muted" style="color:#E06C6C">⚠️ 未检测到 IPv6 地址</div>';
      return;
    }
    box.innerHTML = '';
    ips.forEach(o => {
      const b = document.createElement('button');
      b.className = 'ip'; b.textContent = o.url;
      b.onclick = () => { copyText(o.url); flash(b, '已复制'); };
      box.appendChild(b);
    });
  }

  function flash(el, msg) {
    const old = el.textContent; el.textContent = '✅ ' + msg;
    setTimeout(() => { el.textContent = old; }, 900);
  }

  async function loadAlbums() {
    const albums = await api.list_albums();
    const sel = document.getElementById('album');
    sel.innerHTML = '';
    if (!albums.length) {
      const o = document.createElement('option'); o.textContent = '(无相册)'; o.value = ''; sel.appendChild(o);
    } else {
      albums.forEach(a => { const o = document.createElement('option'); o.textContent = a; o.value = a; sel.appendChild(o); });
    }
    loadTokens();
  }

  function togglePass() {
    const on = document.getElementById('usePass').checked;
    const inp = document.getElementById('passcode');
    inp.disabled = !on;
    if (on && !inp.value.trim()) api.generate_passcode().then(p => inp.value = p);
    if (!on) inp.value = '';
  }

  async function generate() {
    const album = document.getElementById('album').value;
    const days = document.getElementById('expiry').value;
    const usePass = document.getElementById('usePass').checked;
    const passcode = usePass ? document.getElementById('passcode').value : '';
    const r = await api.create_token(album, days, passcode);
    if (!r.ok) { alert(r.error || '生成失败'); return; }
    copyText(r.url);
    document.getElementById('usePass').checked = false; togglePass();
    alert('链接已复制：\n' + r.url + (r.passcode ? '\n\n访问口令：' + r.passcode + '\n（口令需与链接分开发送）' : ''));
    loadTokens();
  }

  async function loadTokens() {
    const toks = await api.list_tokens();
    const box = document.getElementById('tokens');
    if (!toks.length) { box.innerHTML = '<div class="muted" style="padding:10px 2px">暂无链接，请在上方生成。</div>'; return; }
    box.innerHTML = '';
    toks.forEach(t => {
      const div = document.createElement('div');
      div.className = 'tok';
      const sub = '有效期至 ' + (t.expires || '永久') + (t.passcode ? ' · 口令 ' + t.passcode : ' · 无口令');
      div.innerHTML = `<div class="name"></div><div class="sub"></div><div class="acts"></div>`;
      div.querySelector('.name').textContent = t.label;
      div.querySelector('.sub').textContent = sub;
      const acts = div.querySelector('.acts');
      const bc = document.createElement('button'); bc.className = 'sm'; bc.textContent = '复制链接';
      bc.onclick = () => { copyText(t.url); flash(bc, '已复制'); }; acts.appendChild(bc);
      if (t.passcode) {
        const bp = document.createElement('button'); bp.className = 'sm ghost'; bp.textContent = '复制口令';
        bp.onclick = () => { copyText(t.passcode); flash(bp, '已复制'); }; acts.appendChild(bp);
      }
      const br = document.createElement('button'); br.className = 'sm red'; br.textContent = '撤销';
      br.onclick = () => { if (confirm('撤销后该链接立即失效，确定吗？')) api.revoke_token(t.token).then(loadTokens); };
      acts.appendChild(br);
      box.appendChild(div);
    });
  }

  async function showHelp() { alert(await api.help_text()); }

  async function pollLogs() {
    try {
      const logs = await api.get_logs();
      const box = document.getElementById('log');
      box.innerHTML = logs.map(l => {
        const warn = /⚠️|❌|🚨/.test(l.msg);
        return `<span class="${warn ? 'warn' : 'ok'}">[${l.time}] ${l.msg}</span>`;
      }).join('\n');
      box.scrollTop = box.scrollHeight;
    } catch (e) {}
  }

  function init() {
    api = window.pywebview.api;
    refreshState().then(loadAlbums);
    refreshNetwork();
    pollLogs();
    setInterval(pollLogs, 1500);
  }
  window.addEventListener('pywebviewready', init);
</script>
</body>
</html>'''
