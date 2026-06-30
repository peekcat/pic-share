import os
import re
import sys
import time
import threading
import subprocess

# IPv6 地址会变（临时地址 / 前缀更新 / 切换网络），但短时间内稳定。
# 用「短时效缓存」避免每次「复制/生成链接」都同步 spawn 子进程卡住 UI，
# 同时通过 TTL 让地址变化能在 _CACHE_TTL 秒内自动跟上；「刷新网络」可强制重查。
_CACHE_TTL = 60.0  # 秒
_cache_lock = threading.Lock()
_cached_addrs = None
_cached_at = 0.0


def _parse_ifconfig_ipv6(output):
    """从 macOS `ifconfig` 输出中解析全局 IPv6 地址。

    典型行格式： ``inet6 2604:xxxx::1 prefixlen 64 autoconf secured``
    或带 scope 的链路本地： ``inet6 fe80::1%en0 prefixlen 64 scopeid 0x4``
    """
    addrs = set()
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith('inet6'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ip = parts[1].split('%')[0].strip()  # 去掉 %en0 之类的 scope 后缀
        if ip.startswith(('fe80:', '::1')):  # 跳过链路本地与回环地址
            continue
        addrs.add(ip)
    return addrs


def get_ipv6_addresses_v2(force_refresh=False):
    """返回全局 IPv6 地址列表（带 TTL 缓存）。

    force_refresh=True 时无视缓存立即重查（供「刷新网络」按钮使用）。
    建议在后台线程调用：底层会 spawn ``ipconfig``/``ifconfig``/``ip`` 子进程。
    """
    global _cached_addrs, _cached_at
    now = time.monotonic()
    with _cache_lock:
        if (not force_refresh and _cached_addrs is not None
                and now - _cached_at < _CACHE_TTL):
            return _cached_addrs

    addrs = _query_ipv6_addresses()

    with _cache_lock:
        _cached_addrs = addrs
        _cached_at = time.monotonic()
    return addrs


def _query_ipv6_addresses():
    addrs = set()
    try:
        if os.name == 'nt':
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk', errors='ignore',
                                    check=False)
            lines = result.stdout.splitlines()
            for line in lines:
                if 'IPv6 地址' in line:
                    ip = line.split()[-1].strip()
                    if not ip.startswith(('fe80:', '::1')):
                        ip = ip.split('%')[0].strip()
                        addrs.add(ip)
        elif sys.platform == 'darwin':
            # macOS 没有 Linux 的 `ip` 命令，改用 ifconfig 解析 inet6 地址
            result = subprocess.run(['ifconfig'], capture_output=True, text=True, check=False)
            addrs |= _parse_ifconfig_ipv6(result.stdout)
        else:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, check=False)
            lines = result.stdout.splitlines()
            for line in lines:
                if 'inet6' in line and 'global' in line:
                    match = re.search(r'inet6\s+([\w:]+)/\d+', line)
                    if match:
                        addrs.add(match.group(1).strip())
    except Exception:
        pass
    return list(addrs)
