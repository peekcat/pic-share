"""桌面管理端（pywebview 宿主 + js_api 桥）。

管理操作全部走进程内的 js_api 调用，不暴露任何管理 HTTP 端点，
安全边界与原 tkinter 版一致：对外只有客户端 ``/share`` 服务。
"""
