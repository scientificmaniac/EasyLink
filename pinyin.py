#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汉字拼音支持

为九键搜索提供中文姓名的拼音编码，基于 pypinyin 实现。

主要功能：
1. 把文本转换为「拼音 + 拉丁字母」的字母序列
2. 提供姓氏异读表（单、解、仇 等作姓氏时读音与常用读音不同）

设计说明：
1. pypinyin 采用**惰性导入**：未安装时程序仍可正常启动，只是一次转换只剩
   拉丁字母（英文姓名的九键搜索不受影响），中文姓名则检索不到，并给出安装提示。
   这与 openpyxl 的处理方式保持一致。
2. 姓氏异读不在本模块内做合并，而是把读音作为候选交给调用方：
   ContactManager 会为这类姓名同时保留「常用读音」与「姓氏读音」两套编码，
   用户按任一种读音输入都能搜到。
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# pypinyin 是可选依赖，缺失时降级为「仅拉丁字母」
try:
    from pypinyin import lazy_pinyin
except ImportError:  # pragma: no cover - 取决于运行环境是否安装
    lazy_pinyin = None
    logger.info("未安装 pypinyin，中文姓名的九键搜索将不可用")

_INSTALL_HINT = "缺少 pypinyin 依赖，无法为中文姓名生成九键编码。请执行: pip install -r requirements.txt"

# 姓氏异读表：这些字作为姓氏时读音与常用读音不同。
# 仅收录「九键编码确实不同」的字，读音相同的不必列出。
SURNAME_READINGS: Dict[str, str] = {
    "单": "shan",
    "解": "xie",
    "仇": "qiu",
    "查": "zha",
    "朴": "piao",
    "区": "ou",
    "折": "she",
    "乐": "yue",
    "覃": "qin",
    "秘": "bi",
    "尉": "yu",
    "盖": "ge",
    "种": "chong",
    "句": "gou",
    "繁": "po",
    "曾": "zeng",
    "召": "shao",
    "员": "yun",
}


def is_available() -> bool:
    """当前是否具备拼音转换能力

    Returns:
        bool: 已安装 pypinyin 时返回 True
    """
    return lazy_pinyin is not None


def install_hint() -> str:
    """返回缺少依赖时面向用户的安装提示"""
    return _INSTALL_HINT


def surname_reading(char: str) -> Optional[str]:
    """查询某字作姓氏时的读音

    Args:
        char: 单个汉字

    Returns:
        Optional[str]: 姓氏读音（不带声调）；无特殊读音时返回 None
    """
    return SURNAME_READINGS.get(char)


def to_letters(text: str) -> str:
    """把文本转换为小写字母序列

    汉字转换为拼音，拉丁字母原样保留；空格、标点、数字等一律剔除。
    这样「张明」「Emma Wilson」「David 张」得到的是同一种可直接映射到九键的形式。

    Args:
        text: 待转换文本

    Returns:
        str: 仅由 a-z 组成的字母序列；未安装 pypinyin 时只保留输入中的拉丁字母
    """
    if not text:
        return ""

    if lazy_pinyin is None:
        # 降级：中文无法转换，但英文姓名的九键搜索应继续可用
        return "".join(ch for ch in text.lower() if "a" <= ch <= "z")

    # errors 回调让非汉字字符逐字符返回，便于与拼音混排后统一处理
    pieces = lazy_pinyin(text, errors=lambda item: list(item))
    return "".join(ch for ch in "".join(pieces).lower() if "a" <= ch <= "z")
