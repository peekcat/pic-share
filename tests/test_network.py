"""地址探测。

三个 _parse_* 是纯函数，喂真实命令输出直接测；真正 spawn 子进程的只有
_query_addresses 一处，用 mock 挡住，测试不依赖跑测试那台机器的网络环境。
"""

import unittest
from unittest import mock

from picshare import network


class PrivateIPv4Test(unittest.TestCase):
    def test_accepts_rfc1918(self):
        for ip in ("10.0.0.1", "10.255.255.254", "172.16.0.1", "172.31.255.1",
                   "192.168.1.5", "192.168.50.216"):
            self.assertTrue(network.is_private_ipv4(ip), ip)

    def test_rejects_addresses_clients_cannot_reach(self):
        """把非私网地址当「局域网地址」发出去，就是一条打不开的链接。

        198.18/15 是 VPN/代理 TUN 模式常用的假网段（本机实测默认路由就落在
        198.18.0.1）；100.64/10 是运营商 CGNAT。两者客户都连不到。
        """
        for ip in ("198.18.0.1", "100.64.0.1", "8.8.8.8", "172.15.0.1",
                   "172.32.0.1", "192.169.1.1", "127.0.0.1", "169.254.1.1"):
            self.assertFalse(network.is_private_ipv4(ip), ip)

    def test_rejects_garbage(self):
        for bad in ("", "192.168.1", "1.2.3.4.5", "192.168.1.999", "a.b.c.d",
                    "192.168.1.x"):
            self.assertFalse(network.is_private_ipv4(bad), repr(bad))


class ParseIfconfigTest(unittest.TestCase):
    SAMPLE = """lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
	inet 127.0.0.1 netmask 0xff000000
	inet6 ::1 prefixlen 128
	inet6 fe80::1%lo0 prefixlen 64 scopeid 0x1
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
	inet6 fe80::c1b:5ff:fe00:1%en0 prefixlen 64 secured scopeid 0x4
	inet6 2604:1380:4601:a00::5 prefixlen 64 autoconf secured
	inet 192.168.50.216 netmask 0xffffff00 broadcast 192.168.50.255
utun4: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1500
	inet 198.18.0.1 --> 198.18.0.1 netmask 0xffff0000
"""

    def test_extracts_global_ipv6_and_private_ipv4(self):
        v6, v4 = network._parse_ifconfig(self.SAMPLE)
        self.assertEqual(v6, {"2604:1380:4601:a00::5"})
        self.assertEqual(v4, {"192.168.50.216"})

    def test_drops_loopback_and_link_local(self):
        v6, v4 = network._parse_ifconfig(self.SAMPLE)
        self.assertNotIn("::1", v6)
        self.assertNotIn("127.0.0.1", v4)
        self.assertFalse([ip for ip in v6 if ip.startswith("fe80")])

    def test_drops_vpn_tunnel_address(self):
        """VPN 的 utun 网卡地址不能混进局域网地址里，客户连不到。"""
        _, v4 = network._parse_ifconfig(self.SAMPLE)
        self.assertNotIn("198.18.0.1", v4)


class ParseIpAddrTest(unittest.TestCase):
    SAMPLE = """1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536
    inet 127.0.0.1/8 scope host lo
    inet6 ::1/128 scope host
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    inet 10.0.0.23/24 brd 10.0.0.255 scope global eth0
    inet6 2001:db8::1234/64 scope global dynamic
    inet6 fe80::42:acff:fe11:2/64 scope link
"""

    def test_parses_both_families(self):
        v6, v4 = network._parse_ip_addr(self.SAMPLE)
        self.assertEqual(v6, {"2001:db8::1234"})
        self.assertEqual(v4, {"10.0.0.23"})


class ParseIpconfigTest(unittest.TestCase):
    CHINESE = """以太网适配器 以太网:

   连接特定的 DNS 后缀 . . . . . . . :
   IPv6 地址 . . . . . . . . . . . . : 2408:8207:1234::9
   临时 IPv6 地址. . . . . . . . . . : 2408:8207:1234::abcd
   本地链接 IPv6 地址. . . . . . . . : fe80::1c2d:3e4f%12
   IPv4 地址 . . . . . . . . . . . . : 192.168.1.7
   子网掩码  . . . . . . . . . . . . : 255.255.255.0
   默认网关. . . . . . . . . . . . . : 192.168.1.1
"""
    ENGLISH = """Ethernet adapter Ethernet:

   IPv6 Address. . . . . . . . . . . : 2408:8207:1234::9
   Link-local IPv6 Address . . . . . : fe80::1c2d:3e4f%12
   IPv4 Address. . . . . . . . . . . : 192.168.1.7
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
"""

    def test_chinese_locale(self):
        v6, v4 = network._parse_ipconfig(self.CHINESE)
        self.assertIn("2408:8207:1234::9", v6)
        self.assertEqual(v4, {"192.168.1.7"})
        self.assertFalse([ip for ip in v6 if ip.startswith("fe80")])

    def test_english_locale(self):
        """按 "IPv4"/"IPv6" 这两个与界面语言无关的词匹配。

        以前写死的是"IPv6 地址"整串，英文系统上一个地址都探测不到。
        """
        v6, v4 = network._parse_ipconfig(self.ENGLISH)
        self.assertEqual(v6, {"2408:8207:1234::9"})
        self.assertEqual(v4, {"192.168.1.7"})


class AccessAddressesTest(unittest.TestCase):
    def setUp(self):
        network._cached_addrs = None      # 每条用例都从冷缓存开始
        network._cached_at = 0.0

    tearDown = setUp

    def test_public_comes_before_lan(self):
        """公网在前：生成链接时取第一个当主地址，远程可用的那个必须排前面。"""
        with mock.patch.object(network, "_query_addresses",
                               return_value=(["2604::5"], ["192.168.1.7"])), \
             mock.patch.object(network, "get_default_route_ipv4", return_value=None):
            addrs = network.get_access_addresses(force_refresh=True)
        self.assertEqual([a["kind"] for a in addrs],
                         [network.KIND_PUBLIC, network.KIND_LAN])
        self.assertEqual(addrs[0]["ip"], "2604::5")

    def test_default_route_lan_address_ranks_first(self):
        """多网卡时，默认路由那张排最前——猜错了客户就打不开。"""
        with mock.patch.object(network, "_query_addresses",
                               return_value=([], ["10.0.0.5", "192.168.1.7"])), \
             mock.patch.object(network, "get_default_route_ipv4", return_value="192.168.1.7"):
            addrs = network.get_access_addresses(force_refresh=True)
        self.assertEqual([a["ip"] for a in addrs], ["192.168.1.7", "10.0.0.5"])

    def test_no_addresses_returns_empty(self):
        with mock.patch.object(network, "_query_addresses", return_value=([], [])), \
             mock.patch.object(network, "get_default_route_ipv4", return_value=None):
            self.assertEqual(network.get_access_addresses(force_refresh=True), [])

    def test_result_is_cached(self):
        """缓存的意义：每次「复制链接」都同步 spawn 子进程会卡住界面。"""
        q = mock.Mock(return_value=([], ["192.168.1.7"]))
        with mock.patch.object(network, "_query_addresses", q), \
             mock.patch.object(network, "get_default_route_ipv4", return_value=None):
            network.get_access_addresses(force_refresh=True)
            network.get_access_addresses()
            network.get_access_addresses()
        self.assertEqual(q.call_count, 1)

    def test_force_refresh_bypasses_cache(self):
        q = mock.Mock(return_value=([], ["192.168.1.7"]))
        with mock.patch.object(network, "_query_addresses", q), \
             mock.patch.object(network, "get_default_route_ipv4", return_value=None):
            network.get_access_addresses(force_refresh=True)
            network.get_access_addresses(force_refresh=True)
        self.assertEqual(q.call_count, 2)


class DefaultRouteTest(unittest.TestCase):
    def test_rejects_non_private_result(self):
        """开着 VPN 时这里会拿到隧道地址（实测 198.18.0.1），必须丢掉。"""
        fake = mock.MagicMock()
        fake.getsockname.return_value = ("198.18.0.1", 0)
        with mock.patch("socket.socket", return_value=fake):
            self.assertIsNone(network.get_default_route_ipv4())

    def test_returns_private_result(self):
        fake = mock.MagicMock()
        fake.getsockname.return_value = ("192.168.1.7", 0)
        with mock.patch("socket.socket", return_value=fake):
            self.assertEqual(network.get_default_route_ipv4(), "192.168.1.7")

    def test_no_route_returns_none(self):
        fake = mock.MagicMock()
        fake.connect.side_effect = OSError("Network is unreachable")
        with mock.patch("socket.socket", return_value=fake):
            self.assertIsNone(network.get_default_route_ipv4())


if __name__ == "__main__":
    unittest.main()
