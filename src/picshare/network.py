"""探测客户可以用来访问本机的地址。

两种地址，用途完全不同，界面上必须分开讲：

- **公网 IPv6**：客户在任何网络下都能打开，是远程交付的路径。
- **局域网 IPv4**：只有连同一个网络的人能打开，用于当面选片。
  不做公网 IPv4——国内家宽绝大多数是 CGNAT，外部根本连不进来，
  给出一个"看起来像公网"的 IPv4 只会换来"链接打不开"。
"""

import os
import re
import sys
import time
import socket
import threading
import subprocess

# Windows 下 GUI 程序 spawn 子进程(ipconfig 等)会闪一个控制台黑框；
# 加 CREATE_NO_WINDOW 规避。该标志仅 Windows 有，其它平台取 0（默认，无副作用）。
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

# 地址会变（临时地址 / 前缀更新 / 切换网络），但短时间内稳定。
# 用「短时效缓存」避免每次「复制/生成链接」都同步 spawn 子进程卡住 UI，
# 同时通过 TTL 让地址变化能在 _CACHE_TTL 秒内自动跟上；「刷新网络」可强制重查。
_CACHE_TTL = 60.0  # 秒
_cache_lock = threading.Lock()
_cached_addrs = None
_cached_at = 0.0

# 地址种类。界面按这个分组，并给出各自的适用说明。
KIND_PUBLIC = "public"   # 公网 IPv6
KIND_LAN = "lan"         # 局域网 IPv4


# ====== 解析 ======
# 三个 _parse_* 都是纯函数（喂字符串、出地址），便于直接测；真正 spawn 子进程的
# 只有 _query_addresses 一处。

def _keep_ipv6(ip):
    """过滤掉对客户没有意义的 IPv6：链路本地、回环。返回规范化地址或 None。"""
    ip = ip.split('%')[0].strip()       # 去掉 %en0 之类的 scope 后缀
    if not ip or ip == '::' or ip.startswith(('fe80:', '::1')):
        return None
    return ip


def is_private_ipv4(ip):
    """是否为 RFC1918 私网地址（10/8、172.16/12、192.168/16）。

    只认这三段是有意的。开着 VPN / 代理的 TUN 模式时，默认路由的出口地址可能落在
    100.64/10（CGNAT）或 198.18/15（基准测试段）这类地方——那些地址同一个 WiFi 下
    的客户根本连不到，当成「局域网地址」发出去就是个打不开的链接。
    """
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return False
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)


def _parse_ifconfig(output):
    """解析 macOS ``ifconfig``，返回 (ipv6 集合, 私网 ipv4 集合)。

    典型行：``inet6 2604:xxxx::1 prefixlen 64 autoconf secured``
            ``inet 192.168.1.5 netmask 0xffffff00 broadcast 192.168.1.255``
    """
    v6, v4 = set(), set()
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        if parts[0] == 'inet6':
            ip = _keep_ipv6(parts[1])
            if ip:
                v6.add(ip)
        elif parts[0] == 'inet' and is_private_ipv4(parts[1]):
            v4.add(parts[1])
    return v6, v4


def _parse_ip_addr(output):
    """解析 Linux ``ip addr``，返回 (ipv6 集合, 私网 ipv4 集合)。"""
    v6, v4 = set(), set()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('inet6 ') and 'global' in line:
            m = re.search(r'inet6\s+([0-9a-fA-F:]+)/\d+', line)
            if m:
                ip = _keep_ipv6(m.group(1))
                if ip:
                    v6.add(ip)
        elif line.startswith('inet '):
            m = re.search(r'inet\s+([\d.]+)/\d+', line)
            if m and is_private_ipv4(m.group(1)):
                v4.add(m.group(1))
    return v6, v4


def _parse_ipconfig(output):
    """解析 Windows ``ipconfig``，返回 (ipv6 集合, 私网 ipv4 集合)。

    按 "IPv4" / "IPv6" 这两个**与界面语言无关**的词匹配，而不是"IPv6 地址"整串
    ——中文系统写"IPv6 地址"、英文系统写"IPv6 Address"，写死中文会让非中文系统
    一个地址都探测不到。
    """
    v6, v4 = set(), set()
    for line in output.splitlines():
        label, sep, value = line.partition(':')
        if not sep:
            continue
        value = value.strip().rstrip('(首选)').strip()
        if 'IPv6' in label:
            ip = _keep_ipv6(value)
            if ip:
                v6.add(ip)
        elif 'IPv4' in label and is_private_ipv4(value):
            v4.add(value)
    return v6, v4


def _query_addresses():
    """跑一次系统命令，同时取回 IPv6 与私网 IPv4，返回 (ipv6 列表, ipv4 列表)。

    两种地址一起解析而不是各查一次：本来就是同一份输出，能省一半子进程。
    排序只为稳定——调用方要拿「第一个」当主地址，别让它每次随机换一个。
    """
    try:
        if os.name == 'nt':
            out = subprocess.run(['ipconfig'], capture_output=True, text=True,
                                 encoding='gbk', errors='ignore', check=False,
                                 creationflags=_NO_WINDOW).stdout
            v6, v4 = _parse_ipconfig(out)
        elif sys.platform == 'darwin':
            # macOS 没有 Linux 的 `ip` 命令，改用 ifconfig
            out = subprocess.run(['ifconfig'], capture_output=True, text=True,
                                 check=False, creationflags=_NO_WINDOW).stdout
            v6, v4 = _parse_ifconfig(out)
        else:
            out = subprocess.run(['ip', 'addr'], capture_output=True, text=True,
                                 check=False, creationflags=_NO_WINDOW).stdout
            v6, v4 = _parse_ip_addr(out)
    except Exception:
        return [], []
    return sorted(v6), sorted(v4)


# ====== 对外接口 ======

def get_default_route_ipv4():
    """返回走默认路由时使用的本机 IPv4；拿不到或不是私网地址则返回 None。

    做法是拿一个 UDP socket 去 "connect" 一个外部地址，再问它 ``getsockname()``
    ——等于问系统「走默认路由出去时用哪个本机地址」。UDP 的 connect 只是记下目的地，
    不发任何数据包，目标也不需要真的可达。

    只用来**决定多个局域网地址里哪个排第一**，不作为唯一来源：开着 VPN/代理时
    这里会返回隧道地址（本机实测拿到过 198.18.0.1），那种地址客户连不上，
    所以非私网一律丢弃。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        return None            # 没有 IPv4 路由（纯 IPv6 网络，或断网）
    finally:
        s.close()
    return ip if ip and is_private_ipv4(ip) else None


def _order_lan(v4):
    """把默认路由那张网卡的地址排到最前，其余保持字典序。"""
    primary = get_default_route_ipv4()
    if primary and primary in v4:
        return [primary] + [ip for ip in v4 if ip != primary]
    return list(v4)


def get_ipv6_addresses():
    """查询全局 IPv6 地址列表（不带缓存，缓存在 get_access_addresses 那层）。"""
    return _query_addresses()[0]


def get_lan_ipv4_addresses():
    """查询局域网（私网）IPv4 地址列表，默认路由那张网卡排第一。

    返回多个而不是猜一个：装了 VPN、同时插网线又连 WiFi、或者有虚拟机网卡时，
    本机会有好几个私网地址，猜错了客户就打不开。列出来让摄影师挑，
    比替他做一个可能错的决定更好。
    """
    return _order_lan(_query_addresses()[1])


def get_access_addresses(force_refresh=False):
    """返回客户可用来访问本机的地址，公网在前（带 TTL 缓存）。

    形如 ``[{"kind": "public", "ip": "2604:..."}, {"kind": "lan", "ip": "192.168.1.5"}]``。
    不拼 URL：端口属于配置，由调用方（``admin.api``）补上，免得本模块反向依赖 config。

    force_refresh=True 时无视缓存立即重查（供「刷新网络」按钮使用）。
    建议在后台线程调用：底层会 spawn ``ipconfig``/``ifconfig``/``ip`` 子进程。
    """
    global _cached_addrs, _cached_at
    now = time.monotonic()
    with _cache_lock:
        if (not force_refresh and _cached_addrs is not None
                and now - _cached_at < _CACHE_TTL):
            return _cached_addrs

    v6, v4 = _query_addresses()
    addrs = ([{"kind": KIND_PUBLIC, "ip": ip} for ip in v6]
             + [{"kind": KIND_LAN, "ip": ip} for ip in _order_lan(v4)])

    with _cache_lock:
        _cached_addrs = addrs
        _cached_at = time.monotonic()
    return addrs
