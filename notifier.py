#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户通知抽象

数据层（importer / exporter）不直接依赖 tkinter：只要在模块顶层导入 tkinter
或 openpyxl 这类可选依赖，整个模块就无法在无图形环境（命令行、单元测试、
CI）中导入和使用，而且 openpyxl 未安装时连主程序都无法启动。

因此数据层把提示信息通过 Notifier 回调交给调用方，由调用方决定落地方式：
GUI 层弹对话框，命令行/测试场景打印到日志。

约定：
    Notifier = Callable[[level, message], None]
    level 取 LEVEL_INFO / LEVEL_WARNING / LEVEL_ERROR
"""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

LEVEL_INFO = "info"
LEVEL_WARNING = "warning"
LEVEL_ERROR = "error"

# 通知回调类型：接收 (级别, 面向用户的消息文本)
Notifier = Callable[[str, str], None]

_LOG_BY_LEVEL = {
    LEVEL_INFO: logger.info,
    LEVEL_WARNING: logger.warning,
    LEVEL_ERROR: logger.error,
}


def notify(notifier: Optional[Notifier], level: str, message: str) -> None:
    """发送一条通知；未提供 notifier 时退化为写日志

    Args:
        notifier: 通知回调，为 None 时只记录日志
        level: LEVEL_INFO / LEVEL_WARNING / LEVEL_ERROR
        message: 面向用户的消息文本
    """
    if notifier is not None:
        notifier(level, message)
        return
    _LOG_BY_LEVEL.get(level, logger.info)("%s", message)
