"""统一日志。

标准 ``logging`` 为唯一入口：各模块用 ``logging.getLogger(__name__)`` 记录
（都落在 ``picshare`` 命名空间下）。``setup_logging()`` 在启动时把 ``picshare``
日志器接到三处输出：

- 控制台（开发期可见）；
- 滚动文件（持久化，打包后 ``console=False`` 也能事后排查）；
- 管理端「运行日志」面板（经 GUI 处理器转发，例如 RAW 解码失败会在此显示）。

``update_global_status()`` 保留为便捷函数，等价于向 ``picshare`` 日志器写一条 INFO，
供后台模块上报状态而无需 import GUI（避免循环导入）。
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "picshare"
_gui_sink = None


class _GuiLogHandler(logging.Handler):
    """把日志记录转发到管理端「运行日志」面板。"""

    def emit(self, record):
        sink = _gui_sink
        if sink is None:
            return
        try:
            sink(record.getMessage())
        except Exception:
            pass


def set_gui_sink(sink):
    """注册运行日志面板的写入回调（GUI 启动时传入 ``Api.log``）。"""
    global _gui_sink
    _gui_sink = sink


def setup_logging(log_file: Path | None = None):
    """配置 ``picshare`` 日志器（幂等）。控制台/GUI 取 INFO，文件取 DEBUG（更全）。"""
    logger = logging.getLogger(_LOGGER_NAME)
    if getattr(logger, "_configured", False):
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except Exception:
            pass

    gui = _GuiLogHandler()
    gui.setLevel(logging.INFO)
    logger.addHandler(gui)

    logger._configured = True
    return logger


def update_global_status(message):
    """便捷状态上报：写入标准日志（同时进文件与运行日志面板）。"""
    logging.getLogger(_LOGGER_NAME).info(message)
