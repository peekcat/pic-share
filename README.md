# PicShare

> A self-hosted, IPv6-native photo **proofing & delivery** tool for photographers. Clients browse and mark their favorites in a modern web album — no cloud upload, no messenger recompression.

![version](https://img.shields.io/badge/version-0.8.2-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![license](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-green)

**English** · [中文](README.zh-CN.md)

<!-- Screenshot: drop one in and uncomment, e.g. docs/screenshot.png
![PicShare](docs/screenshot.png)
-->

## Features

- **Professional proofing UI** — an iOS-style album that elevates your brand, with a PhotoSwipe viewer (zoom / pan / gestures / keyboard).
- **Full RAW support** — auto-generates previews for CR2 / CR3 / NEF / ARW / DNG / ORF / RW2 / PEF / SR2, decoded with bundled libraw (via `rawpy`) — no external tools to install.
- **One-tap selection** — clients favorite photos in the browser; picks are kept as a per-album manifest (no file copying until you export).
- **Direct IPv6 access** — generates a public share link automatically, no port-forwarding or NAT setup.
- **Works everywhere** — phones, tablets, and desktop browsers.
- **Fast tiered cache** — multi-threaded thumbnail prewarm, plus on-demand large (1600px) and RAW "original" (HD) tiers with lazy loading.

## Quickstart

### Requirements

The desktop window uses your OS's native WebView (via [pywebview](https://pywebview.flowrene.org/)):

- **macOS** — WKWebView, built in. Nothing to install.
- **Windows** — the **WebView2 Runtime** (bundled with Windows 10/11; if the window won't open, install the [Evergreen WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)).
- **Linux** — **WebKit2GTK**, e.g. `sudo apt install gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0` (package names vary by distro).

### Install

```bash
pip install -e .
```

### Run

```bash
picshare        # or: python -m picshare
```

Then, in the desktop window:

1. Click **Select** to choose your photo **root directory** (the folder that holds your album subfolders).
2. Click **🔄 Refresh network** and confirm an IPv6 address appears under "public access address".
3. In **🔗 Share management**, pick an album, set an expiry → **Generate & copy link** (no passcode by default; enable one for sensitive albums).
4. Send the **link** (`http://[...]:5000/share/<token>`) to your client. If you added a passcode, send it **separately** (buttons let you re-copy the link / passcode anytime).

## How it works

- **Photographer** — run the app, choose your photo root, then generate a **dedicated share link** (with optional expiry and passcode) for an album and send it to the matching client.
- **Client** — open the link to browse, mark favorites, and view full-resolution photos (RAW is served as an on-demand high-res JPEG). No album name to type.
- **Collect** — click **Export** in the desktop app to copy the selected originals into `被标记的照片/<album>/`, then it opens in your file manager.

## Access Control

PicShare uses a **capability-URL** model rather than guessable album names:

- Each album is bound to an unguessable random token (`/share/<token>`); the album is derived server-side, so clients **cannot specify an album name in the URL** and can neither see nor guess others' albums.
- The token is a strong random credential (192-bit). For most cases **one link is enough** — no passcode needed.
- Optionally add a **passcode** for sensitive albums (off by default): a random 4-character alphanumeric code, sent **separately** from the link (it is **not** embedded in the URL, so forwarding the link doesn't leak it). The client types it once in the browser.
- Links can carry an **expiry** (3 / 7 / 14 days, default 3; auto-invalidates).
- You can **revoke** any link at any time, or re-copy its link / passcode.
- Tokens and passcodes (if set) live in `<root>/._picshare/tokens.json` (a local hidden file), managed by the desktop app and read-only-verified by the web server.

## Project Layout

> This repo has been refactored from the original single file into a standard `src`-layout Python project.

```
src/picshare/
├── __main__.py        # `python -m picshare` entry
├── desktop.py         # desktop entry: pywebview admin window + waitress public server
├── config.py          # ServerState config, extensions, cache/data dirs
├── settings.py        # user-level settings persistence (remembers the root dir, etc.)
├── status.py          # unified logging (logging → console / file / run-log panel)
├── network.py         # IPv6 address detection (Windows / macOS / Linux)
├── paths.py           # safe_join path-safety helper
├── preview.py         # thumbnail / large / RAW-HD generation (rawpy fallback + cache version stamp)
├── tokens.py          # access-token storage & verification (capability URLs)
├── selections.py      # client selection manifest storage
├── admin/             # admin side (pywebview, in-process js_api, no public HTTP endpoints)
│   ├── api.py         # Python API exposed to the admin page
│   └── templates.py   # admin single-page HTML (album cards / sharing / run log)
└── web/               # public web service (client /share access)
    ├── app.py         # Flask app & token-scoped routes
    ├── templates.py   # album / landing / passcode page templates
    └── static/photoswipe/   # bundled PhotoSwipe viewer (offline)
```

## Security Notes

Access control is token-based (see above), which is far stronger than "guess the album name." A few inherent limits still apply:

- **The link is the credential** — a capability URL is a bearer secret; **anyone with the link can access it**. For sensitive albums, add a **passcode** and/or **expiry**, and avoid sharing links on public channels.
- **Plain HTTP** — TLS is not enabled; an on-path attacker could intercept tokens and photos. Strong encryption needs a reverse proxy / tunnel (e.g. Caddy, Cloudflare Tunnel) — a future direction.
- **No passcode rate-limiting** — passcode checks aren't rate-limited yet, so a short passcode is theoretically brute-forceable by an attacker who already holds the token; rate-limiting / lockout is a planned hardening.

Always make sure the chosen photo root contains only the photos you're willing to deliver.

## License

Source-available under the **[PolyForm Noncommercial License 1.0.0](LICENSE)** — you may use, modify, and share it for **noncommercial purposes only**. **Commercial use is not permitted.**

> Note: because of the noncommercial restriction, this is *source-available*, not OSI "open source."
