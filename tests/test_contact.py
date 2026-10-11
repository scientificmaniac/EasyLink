#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contact 数据模型的单元测试"""

import unittest

from contact import LETTER_TO_KEY, Contact


class TestCountryDetection(unittest.TestCase):
    """国家/地区识别"""

    def test_taiwan_is_not_matched_as_mainland(self):
        """回归：区号曾按字典插入顺序匹配，'+886' 被更短的 '+86' 抢先命中"""
        self.assertEqual(Contact("A", "+886912345678").country, "中国台湾")

    def test_hongkong_and_macau(self):
        self.assertEqual(Contact("A", "+85212345678").country, "中国香港")
        self.assertEqual(Contact("A", "+85312345678").country, "中国澳门")

    def test_mainland_mobile(self):
        self.assertEqual(Contact("A", "+8613800138000").country, "中国")
        self.assertEqual(Contact("A", "13800138000").country, "中国")

    def test_usa(self):
        self.assertEqual(Contact("A", "+16551234567").country, "美国/加拿大")

    def test_unrecognized_number(self):
        self.assertEqual(Contact("A", "+9991234567").country, "未知")

    def test_eleven_digits_not_starting_with_one(self):
        """11 位但不以 1 开头的号码不应被当作国内手机号"""
        self.assertEqual(Contact("A", "01012345678").country, "未知")


class TestPhoneNormalization(unittest.TestCase):
    """号码规范化"""

    def test_separators_removed(self):
        for raw in ("+86 138 0013 8000", "138-0013-8000", "(010)12345678"):
            with self.subTest(raw=raw):
                normalized = Contact.normalize_phone(raw)
                self.assertNotIn(" ", normalized)
                self.assertNotIn("-", normalized)
                self.assertNotIn("(", normalized)


class TestFormatPhone(unittest.TestCase):
    """电话显示格式化"""

    def test_local_mobile_gets_country_prefix(self):
        self.assertEqual(Contact("A", "13800138000").format_phone(), "+86 13800138000")

    def test_prefixed_number_has_no_double_space(self):
        """回归：区号后已带空格时，格式化曾产生两个连续空格"""
        self.assertEqual(Contact("A", "+86 13800138000").format_phone(), "+86 13800138000")
        self.assertEqual(Contact("A", "+886 912345678").format_phone(), "+886 912345678")

    def test_landline_kept_as_is(self):
        self.assertEqual(Contact("A", "010-12345678").format_phone(), "010-12345678")

    def test_empty_phone(self):
        # phone 为必填，这里直接验证空值分支的健壮性
        contact = Contact("A", "13800138000")
        contact.phone = ""
        self.assertEqual(contact.format_phone(), "")


class TestSerialization(unittest.TestCase):
    """序列化与反序列化"""

    def test_roundtrip(self):
        original = Contact("张明", "+8613800138000", "a@b.com", "大学同学", True)
        restored = Contact.from_dict(original.to_dict())
        self.assertEqual(restored.to_dict(), original.to_dict())
        self.assertEqual(restored.country, original.country)

    def test_from_dict_accepts_common_boolean_spellings(self):
        """回归：只接受严格 bool，导致 0/1、'true' 等写法的整条记录被静默跳过"""
        for raw, expected in ((True, True), (False, False), (1, True), (0, False),
                              ("true", True), ("False", False), ("是", True), ("否", False),
                              (None, False)):
            with self.subTest(value=raw):
                contact = Contact.from_dict(
                    {"name": "张明", "phone": "13800138000", "is_frequent": raw}
                )
                self.assertIs(contact.is_frequent, expected)

    def test_from_dict_rejects_invalid_boolean(self):
        with self.assertRaises(TypeError):
            Contact.from_dict({"name": "张明", "phone": "13800138000", "is_frequent": "maybe"})

    def test_from_dict_missing_required_field(self):
        with self.assertRaises(ValueError):
            Contact.from_dict({"name": "张明"})

    def test_from_dict_wrong_type(self):
        with self.assertRaises(TypeError):
            Contact.from_dict(["not", "a", "dict"])
        with self.assertRaises(TypeError):
            Contact.from_dict({"name": 123, "phone": "13800138000"})

    def test_from_dict_optional_fields_default_to_empty(self):
        contact = Contact.from_dict({"name": "张明", "phone": "13800138000"})
        self.assertEqual(contact.email, "")
        self.assertEqual(contact.remark, "")
        self.assertFalse(contact.is_frequent)


class TestContactUpdate(unittest.TestCase):
    """update 方法"""

    def test_partial_update_keeps_other_fields(self):
        contact = Contact("张明", "13800138000", "a@b.com", "同学")
        contact.update(email="new@b.com")
        self.assertEqual(contact.email, "new@b.com")
        self.assertEqual(contact.name, "张明")
        self.assertEqual(contact.remark, "同学")

    def test_update_recomputes_country(self):
        contact = Contact("张明", "13800138000")
        self.assertEqual(contact.country, "中国")
        contact.update(phone="+16551234567")
        self.assertEqual(contact.country, "美国/加拿大")

    def test_invalid_update_is_rejected_without_mutating(self):
        contact = Contact("张明", "13800138000")
        with self.assertRaises(ValueError):
            contact.update(phone="abc")
        self.assertEqual(contact.phone, "13800138000")

    def test_constructor_rejects_invalid_data(self):
        with self.assertRaises(ValueError):
            Contact("", "13800138000")


class TestKeypadMapping(unittest.TestCase):
    """九键映射表"""

    def test_all_letters_mapped(self):
        for letter in "abcdefghijklmnopqrstuvwxyz":
            self.assertIn(letter, LETTER_TO_KEY)

    def test_mapping_values(self):
        self.assertEqual(LETTER_TO_KEY["a"], "2")
        self.assertEqual(LETTER_TO_KEY["s"], "7")
        self.assertEqual(LETTER_TO_KEY["z"], "9")


if __name__ == "__main__":
    unittest.main()
