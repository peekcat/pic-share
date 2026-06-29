"""GUI 状态广播。

后台模块(预览生成、Flask 路由)通过 ``update_global_status`` 上报状态,
GUI 启动时把自身注册为 ``gui_app``。这样底层模块无需 import GUI,
避免循环导入。
"""

gui_app = None


def update_global_status(message):
    if gui_app:
        gui_app.update_status(message)
