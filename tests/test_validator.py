#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validator 数据校验的单元测试"""

import unittest

from validator import Validator


class TestEmailValidation(unittest.TestCase):
    """邮箱校验"""

    def test_valid_emails(self):
        for email in ("a@b.com", "first.last+tag@sub.example.cn", "user_name@domain.org"):
            with self.subTest(email=email):
                self.assertTrue(Validator.is_valid_email(email))
                self.assertEqual(Validator.validate_email(email), (True, ""))

    def test_invalid_emails(self):
        for email in ("plain", "a@b", "a@@b.com", "@b.com", "a b@c.com"):
            with self.subTest(email=email):
                self.assertFalse(Validator.is_valid_email(email))

    def test_empty_email_is_optional(self):
        for empty in ("", None):
            with self.subTest(value=empty):
                self.assertTrue(Validator.is_valid_email(empty))

    def test_email_too_long(self):
        ok, msg = Validator.validate_email("a" * 250 + "@b.com")
        self.assertFalse(ok)
        self.assertIn("长度", msg)


class TestPhoneValidation(unittest.TestCase):
    """电话校验"""

    def test_accepted_formats(self):
        for phone in (
            "+8613800138000",
            "13800138000",
            "010-12345678",
            "(010)12345678",
            "+86 138 0013 8000",
            "+886 912345678",
        ):
            with self.subTest(phone=phone):
                ok, msg = Validator.validate_phone(phone)
                self.assertTrue(ok, f"{phone} 应被接受，实际被拒: {msg}")

    def test_rejected_formats(self):
        for phone in ("", None, "   ", "abc", "+", "123", "138_0013_8000", "13800138000x"):
            with self.subTest(phone=phone):
                self.assertFalse(Validator.is_valid_phone(phone))

    def test_length_error_mentions_digit_count(self):
        """回归：位数不足时曾一律报「格式不正确」，与真实原因不符"""
        ok, msg = Validator.validate_phone("123")
        self.assertFalse(ok)
        self.assertIn("位数", msg)

    def test_too_many_digits_rejected(self):
        self.assertFalse(Validator.is_valid_phone("12345678901234567890"))


class TestNameValidation(unittest.TestCase):
    """姓名校验"""

    def test_accepted_names(self):
        for name in ("张明", "Emma Wilson", "张三(同事)", "李四_2", "O'Brien", "安娜·卡列尼娜", "A.B-C"):
            with self.subTest(name=name):
                ok, msg = Validator.validate_name(name)
                self.assertTrue(ok, f"{name} 应被接受，实际被拒: {msg}")

    def test_rejected_names(self):
        for name in ("", None, "   ", "x" * 51, "张三<script>"):
            with self.subTest(name=name):
                self.assertFalse(Validator.is_valid_name(name))

    def test_surrounding_whitespace_is_trimmed(self):
        self.assertTrue(Validator.is_valid_name("  张明  "))


class TestRemarkValidation(unittest.TestCase):
    """备注校验"""

    def test_remark_is_optional(self):
        for value in ("", None):
            with self.subTest(value=value):
                self.assertEqual(Validator.validate_remark(value), (True, ""))

    def test_remark_too_long(self):
        ok, msg = Validator.validate_remark("备" * 201)
        self.assertFalse(ok)
        self.assertIn("备注", msg)


class TestValidatorConsistency(unittest.TestCase):
    """is_valid_xxx 与 validate_xxx 必须给出完全一致的判定"""

    def test_email(self):
        for value in ("", None, "a@b.com", "bad", "x" * 300 + "@b.com"):
            self.assertEqual(
                Validator.is_valid_email(value), Validator.validate_email(value)[0], repr(value)
            )

    def test_name(self):
        for value in ("", None, "   ", "张明", "张三(同事)", "x" * 51):
            self.assertEqual(
                Validator.is_valid_name(value), Validator.validate_name(value)[0], repr(value)
            )

    def test_phone(self):
        for value in ("", None, "13800138000", "(010)12345678", "abc", "123"):
            self.assertEqual(
                Validator.is_valid_phone(value), Validator.validate_phone(value)[0], repr(value)
            )


class TestContactDataValidation(unittest.TestCase):
    """完整联系人数据校验"""

    def test_valid_contact(self):
        self.assertEqual(
            Validator.validate_contact_data("张明", "13800138000", "a@b.com", "同学"), (True, "")
        )

    def test_reports_name_error_first(self):
        ok, msg = Validator.validate_contact_data("", "13800138000")
        self.assertFalse(ok)
        self.assertIn("姓名", msg)

    def test_reports_phone_error(self):
        ok, msg = Validator.validate_contact_data("张明", "abc")
        self.assertFalse(ok)
        self.assertIn("电话", msg)

    def test_reports_remark_error(self):
        ok, msg = Validator.validate_contact_data("张明", "13800138000", "", "备" * 201)
        self.assertFalse(ok)
        self.assertIn("备注", msg)


if __name__ == "__main__":
    unittest.main()
