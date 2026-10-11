#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人数据验证模块

该模块提供联系人数据的验证功能，包括姓名、电话、邮箱和备注的验证，
以及完整联系人数据的综合验证。

主要功能：
1. 邮箱格式验证
2. 电话号码验证
3. 姓名格式验证
4. 备注信息验证
5. 完整联系人数据验证

设计说明：
    is_valid_xxx / validate_xxx 是同一套判定标准的两种返回形式。
    is_valid_xxx 直接委托 validate_xxx，避免两处规则各自演化后互相矛盾。
"""

import re
from typing import Optional, Tuple

# 电话中允许出现的字符：数字、空格、横杠、括号，可带 + 国际区号。
# 位数是否合法由 validate_phone 统一判断，这样报错原因才能与真实问题一致。
_PHONE_ALLOWED_PATTERN = re.compile(r'^\+?[0-9\s\-()]+$')
_PHONE_DIGITS = re.compile(r'\D')

# 姓名允许：中文、字母、数字、空格以及常见的连接与修饰符号
_NAME_PATTERN = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9\s._'\"()&·-]+$")

# 邮箱长度上限，超过 RFC 5321 限制的地址没有实际意义
_MAX_EMAIL_LENGTH = 254
_MAX_NAME_LENGTH = 50
_MAX_REMARK_LENGTH = 200
_MIN_PHONE_DIGITS = 7
_MAX_PHONE_DIGITS = 15


class Validator:
    """联系人数据验证类

    该类提供了一系列静态方法，用于验证联系人数据的各个字段。
    """

    # 邮箱验证正则表达式，支持标准邮箱格式
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    # 电话验证正则表达式（字符集校验，位数校验见 validate_phone）
    PHONE_PATTERN = _PHONE_ALLOWED_PATTERN

    # 姓名验证正则表达式
    NAME_PATTERN = _NAME_PATTERN

    # ------------------------------------------------------------------
    # 邮箱
    # ------------------------------------------------------------------
    @staticmethod
    def validate_email(email: Optional[str]) -> Tuple[bool, str]:
        """验证邮箱格式并返回详细错误信息

        Args:
            email: 要验证的邮箱地址（可为空）

        Returns:
            Tuple[bool, str]: (验证结果, 错误信息)
        """
        if email is None or (isinstance(email, str) and not email.strip()):
            return True, ""  # 邮箱为可选字段

        if not isinstance(email, str):
            return False, "邮箱必须是字符串类型"

        email = email.strip()
        if len(email) > _MAX_EMAIL_LENGTH:
            return False, f"邮箱长度不能超过 {_MAX_EMAIL_LENGTH} 个字符"

        if not Validator.EMAIL_PATTERN.match(email):
            return False, "邮箱格式不正确，应为 example@domain.com"

        return True, ""

    @staticmethod
    def is_valid_email(email: Optional[str]) -> bool:
        """验证邮箱格式

        Args:
            email: 要验证的邮箱地址

        Returns:
            bool: 邮箱格式是否有效（空值视为有效）
        """
        return Validator.validate_email(email)[0]

    # ------------------------------------------------------------------
    # 电话
    # ------------------------------------------------------------------
    @staticmethod
    def validate_phone(phone: Optional[str]) -> Tuple[bool, str]:
        """验证电话号码格式并返回详细错误信息

        支持 +8613800138000、13800138000、010-12345678、(010)12345678 等写法。

        Args:
            phone: 要验证的电话号码

        Returns:
            Tuple[bool, str]: (验证结果, 错误信息)
        """
        if phone is None or (isinstance(phone, str) and not phone.strip()):
            return False, "电话号码不能为空"

        if not isinstance(phone, str):
            return False, "电话号码必须是字符串类型"

        phone = phone.strip()
        if not Validator.PHONE_PATTERN.match(phone):
            return False, "电话号码只能包含数字、空格、横杠和括号，且只能以 + 开头表示国际区号"

        digits = _PHONE_DIGITS.sub("", phone)
        if not _MIN_PHONE_DIGITS <= len(digits) <= _MAX_PHONE_DIGITS:
            return False, (
                f"电话号码位数不正确（当前 {len(digits)} 位，"
                f"应为 {_MIN_PHONE_DIGITS}-{_MAX_PHONE_DIGITS} 位）"
            )

        return True, ""

    @staticmethod
    def is_valid_phone(phone: Optional[str]) -> bool:
        """验证电话号码格式

        Args:
            phone: 要验证的电话号码

        Returns:
            bool: 电话号码格式是否有效
        """
        return Validator.validate_phone(phone)[0]

    # ------------------------------------------------------------------
    # 姓名
    # ------------------------------------------------------------------
    @staticmethod
    def validate_name(name: Optional[str]) -> Tuple[bool, str]:
        """验证姓名格式并返回详细错误信息

        Args:
            name: 要验证的姓名

        Returns:
            Tuple[bool, str]: (验证结果, 错误信息)
        """
        if name is None or not isinstance(name, str):
            return False, "姓名不能为空且必须是字符串类型"

        name = name.strip()
        if not name:
            return False, "姓名不能为空"

        if len(name) > _MAX_NAME_LENGTH:
            return False, f"姓名长度不能超过 {_MAX_NAME_LENGTH} 个字符"

        if not Validator.NAME_PATTERN.match(name):
            return False, "姓名只能包含中文、字母、数字、空格以及 . _ - ' \" ( ) & · 这些符号"

        return True, ""

    @staticmethod
    def is_valid_name(name: Optional[str]) -> bool:
        """验证姓名格式

        Args:
            name: 要验证的姓名

        Returns:
            bool: 姓名格式是否有效
        """
        return Validator.validate_name(name)[0]

    # ------------------------------------------------------------------
    # 备注
    # ------------------------------------------------------------------
    @staticmethod
    def validate_remark(remark: Optional[str]) -> Tuple[bool, str]:
        """验证备注信息

        Args:
            remark: 要验证的备注信息（可为空）

        Returns:
            Tuple[bool, str]: (验证结果, 错误信息)
        """
        if remark is None or (isinstance(remark, str) and not remark.strip()):
            return True, ""  # 备注为可选字段

        if not isinstance(remark, str):
            return False, "备注必须是字符串类型"

        if len(remark) > _MAX_REMARK_LENGTH:
            return False, f"备注长度不能超过 {_MAX_REMARK_LENGTH} 个字符"

        return True, ""

    # ------------------------------------------------------------------
    # 组合校验
    # ------------------------------------------------------------------
    @staticmethod
    def validate_contact_data(
        name: str, phone: str, email: str = "", remark: str = ""
    ) -> Tuple[bool, str]:
        """验证完整的联系人数据

        Args:
            name: 联系人姓名
            phone: 联系人电话
            email: 联系人邮箱（可选）
            remark: 联系人备注（可选）

        Returns:
            Tuple[bool, str]: (验证结果, 错误信息)；全部通过时错误信息为空串
        """
        for valid, msg in (
            Validator.validate_name(name),
            Validator.validate_phone(phone),
            Validator.validate_email(email),
            Validator.validate_remark(remark),
        ):
            if not valid:
                return False, msg

        return True, ""
