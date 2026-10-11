#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人数据模型

该模块定义了联系人对象及其相关方法，包括联系人信息的验证、格式化和转换。

主要内容：
1. 国家区号映射表
2. 九键键盘映射表
3. Contact类：联系人数据模型
"""

import re
from typing import Any, Dict, List, Optional, Set

from validator import Validator

# 国家区号映射表，用于根据电话号码识别国家/地区
COUNTRY_CODES: Dict[str, str] = {
    '+86': '中国',
    '+1': '美国/加拿大',
    '+44': '英国',
    '+49': '德国',
    '+33': '法国',
    '+39': '意大利',
    '+81': '日本',
    '+82': '韩国',
    '+61': '澳大利亚',
    '+91': '印度',
    '+7': '俄罗斯',
    '+65': '新加坡',
    '+47': '挪威',
    '+46': '瑞典',
    '+45': '丹麦',
    '+31': '荷兰',
    '+43': '奥地利',
    '+34': '西班牙',
    '+41': '瑞士',
    '+64': '新西兰',
    '+27': '南非',
    '+55': '巴西',
    '+52': '墨西哥',
    '+886': '中国台湾',
    '+852': '中国香港',
    '+853': '中国澳门',
}

# 按区号长度降序排列后再做前缀匹配。
# 若直接用字典的插入顺序，'+886'（中国台湾）会先命中更短的 '+86'（中国）而被误判。
COUNTRY_CODES_BY_LENGTH: List[str] = sorted(COUNTRY_CODES, key=len, reverse=True)

# 电话号码中常见的分隔符，识别与比较前先剔除
_PHONE_SEPARATORS = re.compile(r'[\s\-()]')

# 九键键盘映射表：数字键对应字母集合
KEYPAD_MAPPING: Dict[str, Set[str]] = {
    '2': {'a', 'b', 'c'},
    '3': {'d', 'e', 'f'},
    '4': {'g', 'h', 'i'},
    '5': {'j', 'k', 'l'},
    '6': {'m', 'n', 'o'},
    '7': {'p', 'q', 'r', 's'},
    '8': {'t', 'u', 'v'},
    '9': {'w', 'x', 'y', 'z'},
}

# 反向映射：字母到数字，用于快速把文本转换为九键数字序列
LETTER_TO_KEY: Dict[str, str] = {
    letter: key for key, letters in KEYPAD_MAPPING.items() for letter in letters
}

# JSON 中常见的布尔写法，兼容其它工具导出的数据
_TRUE_LITERALS = {'true', '1', '是', 'yes'}
_FALSE_LITERALS = {'false', '0', '否', 'no'}


def coerce_is_frequent(value: Any) -> bool:
    """把各种常见的布尔写法统一成 bool

    手工编辑或由其它工具生成的 JSON 常把布尔写成 0/1、"true"/"false"。
    一律按类型错误拒绝会让整条联系人被静默跳过（乃至后续保存时丢失）；
    而简单套用 bool(value) 又会把字符串 "false" 判成 True。

    Args:
        value: 原始取值

    Returns:
        bool: 规范化后的布尔值

    Raises:
        TypeError: 取值无法解释为布尔
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE_LITERALS:
            return True
        if lowered in _FALSE_LITERALS:
            return False
    raise TypeError(f"is_frequent must be a boolean, got {value!r}")


class Contact:
    """联系人数据模型类

    该类定义了联系人的属性和方法，包括数据验证、格式化和转换。

    属性：
        name: 联系人姓名
        phone: 联系人电话
        email: 联系人邮箱
        remark: 联系人备注
        is_frequent: 是否为常用联系人
        country: 根据电话号码自动识别的国家/地区
    """

    def __init__(
        self,
        name: str,
        phone: str,
        email: str = "",
        remark: str = "",
        is_frequent: bool = False,
    ) -> None:
        """初始化联系人对象

        Args:
            name: 联系人姓名
            phone: 联系人电话
            email: 联系人邮箱（可选）
            remark: 联系人备注（可选）
            is_frequent: 是否为常用联系人（可选，默认为 False）

        Raises:
            ValueError: 如果联系人数据无效
        """
        valid, msg = Validator.validate_contact_data(name, phone, email, remark)
        if not valid:
            raise ValueError(f"Invalid contact data: {msg}")

        self.name: str = name.strip()
        self.phone: str = phone.strip()
        self.email: str = email.strip()
        self.remark: str = remark.strip()
        self.is_frequent: bool = is_frequent
        self.country: str = self.get_country_from_phone()

    def __repr__(self) -> str:
        return f"Contact(name={self.name!r}, phone={self.phone!r})"

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """剔除电话号码中的空格、横杠与括号

        Args:
            phone: 原始电话号码

        Returns:
            str: 规范化后的号码
        """
        return _PHONE_SEPARATORS.sub("", phone or "")

    def get_country_from_phone(self) -> str:
        """根据电话号码推断国家/地区

        Returns:
            str: 国家/地区名称；无法识别时返回 '未知'
        """
        if not self.phone:
            return '未知'

        normalized = self.normalize_phone(self.phone)

        # 按区号长度降序匹配，避免 +886 被 +86 抢先命中
        for code in COUNTRY_CODES_BY_LENGTH:
            if normalized.startswith(code):
                return COUNTRY_CODES[code]

        # 无国际区号的 11 位国内手机号（以 1 开头）
        if normalized.isdigit() and len(normalized) == 11 and normalized.startswith('1'):
            return '中国'

        return '未知'

    def format_phone(self) -> str:
        """格式化电话号码用于显示：区号与号码之间加一个空格

        Returns:
            str: 格式化后的电话号码
        """
        if not self.phone:
            return ""

        phone = self.phone.strip()

        for code in COUNTRY_CODES_BY_LENGTH:
            if phone.startswith(code):
                rest = phone[len(code):]
                # 区号后若已带分隔符，不再重复补空格（否则会出现两个空格）
                separator = "" if rest[:1] in (" ", "-") else " "
                return f"{code}{separator}{rest}"

        digits = self.normalize_phone(phone)
        if digits.isdigit() and len(digits) == 11 and digits.startswith('1'):
            return f"+86 {digits}"

        return phone

    def to_dict(self) -> Dict[str, Any]:
        """将联系人对象转换为字典，用于序列化存储

        Returns:
            Dict[str, Any]: 联系人字典
        """
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "remark": self.remark,
            "is_frequent": self.is_frequent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """从字典创建联系人对象，用于反序列化

        Args:
            data: 包含联系人信息的字典

        Returns:
            Contact: 联系人对象

        Raises:
            TypeError: 如果 data 不是字典，或字段类型不正确
            ValueError: 如果缺少必填字段
        """
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary")

        for field in ("name", "phone"):
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
            if not isinstance(data[field], str):
                raise TypeError(f"Field '{field}' must be a string")

        email = data.get("email") or ""
        if not isinstance(email, str):
            raise TypeError("email must be a string")

        remark = data.get("remark") or ""
        if not isinstance(remark, str):
            raise TypeError("remark must be a string")

        return cls(
            data["name"],
            data["phone"],
            email,
            remark,
            coerce_is_frequent(data.get("is_frequent", False)),
        )

    def update(
        self,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        remark: Optional[str] = None,
        is_frequent: Optional[bool] = None,
    ) -> None:
        """更新联系人信息（校验通过后一次性生效）

        Args:
            name: 新的姓名（可选）
            phone: 新的电话（可选）
            email: 新的邮箱（可选）
            remark: 新的备注（可选）
            is_frequent: 是否为常用联系人（可选）

        Raises:
            ValueError: 如果更新后的联系人数据无效
        """
        new_name = name.strip() if name is not None else self.name
        new_phone = phone.strip() if phone is not None else self.phone
        new_email = email.strip() if email is not None else self.email
        new_remark = remark.strip() if remark is not None else self.remark
        new_is_frequent = is_frequent if is_frequent is not None else self.is_frequent

        valid, msg = Validator.validate_contact_data(new_name, new_phone, new_email, new_remark)
        if not valid:
            raise ValueError(f"Invalid contact data: {msg}")

        self.name = new_name
        self.phone = new_phone
        self.email = new_email
        self.remark = new_remark
        self.is_frequent = new_is_frequent
        self.country = self.get_country_from_phone()
