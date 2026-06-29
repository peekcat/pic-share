import os
import re
import sys
import subprocess


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


def get_ipv6_addresses_v2():
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
