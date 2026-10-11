#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼音支持模块的单元测试

覆盖点：
1. 常见姓氏与姓名能正确转换为拼音字母
2. 中英混排、标点与数字的处理
3. 姓氏异读表的有效性（读音必须与默认读音不同）
4. 未安装 pypinyin 时的降级行为
"""

import os
import tempfile
import unittest
from unittest import mock

import pinyin
from contact import Contact
from contact_manager import ContactManager
from storage import DataStorage


class TestToLetters(unittest.TestCase):
    """汉字与拉丁字母混合转换"""

    def test_common_surnames(self):
        expected = {
            "张": "zhang", "王": "wang", "李": "li", "赵": "zhao", "陈": "chen",
            "刘": "liu", "杨": "yang", "黄": "huang", "周": "zhou", "吴": "wu",
            "徐": "xu", "孙": "sun", "马": "ma", "朱": "zhu", "胡": "hu",
            "郭": "guo", "何": "he", "林": "lin", "罗": "luo", "郑": "zheng",
        }
        for char, letters in expected.items():
            with self.subTest(char=char):
                self.assertEqual(pinyin.to_letters(char), letters)

    def test_full_name(self):
        self.assertEqual(pinyin.to_letters("张明"), "zhangming")
        self.assertEqual(pinyin.to_letters("王小雨"), "wangxiaoyu")

    def test_latin_text_is_lowercased_and_kept(self):
        self.assertEqual(pinyin.to_letters("Emma"), "emma")
        self.assertEqual(pinyin.to_letters("David Wang"), "davidwang")

    def test_mixed_chinese_and_latin(self):
        self.assertEqual(pinyin.to_letters("David 张"), "davidzhang")
        self.assertEqual(pinyin.to_letters("张Emma"), "zhangemma")

    def test_separators_and_digits_are_dropped(self):
        self.assertEqual(pinyin.to_letters("张-明"), "zhangming")
        self.assertEqual(pinyin.to_letters("张 明"), "zhangming")
        self.assertEqual(pinyin.to_letters("张3"), "zhang")

    def test_empty_input(self):
        self.assertEqual(pinyin.to_letters(""), "")
        self.assertEqual(pinyin.to_letters(None), "")


class TestSurnameReadings(unittest.TestCase):
    """姓氏异读表"""

    def test_known_readings(self):
        self.assertEqual(pinyin.surname_reading("单"), "shan")
        self.assertEqual(pinyin.surname_reading("解"), "xie")
        self.assertEqual(pinyin.surname_reading("仇"), "qiu")
        self.assertEqual(pinyin.surname_reading("曾"), "zeng")

    def test_regular_surname_has_no_alternate_reading(self):
        for char in ("张", "王", "李", "陈", "刘"):
            with self.subTest(char=char):
                self.assertIsNone(pinyin.surname_reading(char))

    def test_every_reading_differs_from_default_pronunciation(self):
        """异读表里收录的读音必须与默认读音不同，否则这条记录毫无意义"""
        for char, reading in pinyin.SURNAME_READINGS.items():
            with self.subTest(char=char):
                self.assertNotEqual(
                    pinyin.to_letters(char), reading,
                    f"「{char}」的默认读音与异读表相同，应从表中移除",
                )

    def test_readings_are_lowercase_letters(self):
        for char, reading in pinyin.SURNAME_READINGS.items():
            with self.subTest(char=char):
                self.assertTrue(reading.isascii() and reading.isalpha() and reading.islower())


class TestAvailability(unittest.TestCase):
    """依赖可用性"""

    def test_is_available_in_this_environment(self):
        self.assertTrue(pinyin.is_available(), "本环境应已安装 pypinyin")

    def test_install_hint_mentions_command(self):
        self.assertIn("pip install", pinyin.install_hint())


class TestFallbackWithoutPypinyin(unittest.TestCase):
    """未安装 pypinyin 时降级为「仅拉丁字母」，而不是崩溃"""

    def test_latin_letters_are_preserved(self):
        with mock.patch.object(pinyin, "lazy_pinyin", None):
            self.assertFalse(pinyin.is_available())
            self.assertEqual(pinyin.to_letters("Emma Wilson"), "emmawilson")

    def test_chinese_yields_empty(self):
        with mock.patch.object(pinyin, "lazy_pinyin", None):
            self.assertEqual(pinyin.to_letters("张明"), "")

    def test_manager_still_searches_latin_names(self):
        """英文姓名的九键搜索不应因为缺少 pypinyin 而失效"""
        with tempfile.TemporaryDirectory() as tmp:
            manager = ContactManager(DataStorage(os.path.join(tmp, "c.json")))
            with mock.patch.object(pinyin, "lazy_pinyin", None):
                manager.add_contact(Contact("Emma Wilson", "13800138000"))
                self.assertEqual(
                    [c.name for c in manager.search_by_keypad("3662")], ["Emma Wilson"]
                )

    def test_manager_ignores_chinese_names_gracefully(self):
        """缺少 pypinyin 时中文姓名不参与九键匹配，但不抛异常"""
        with tempfile.TemporaryDirectory() as tmp:
            manager = ContactManager(DataStorage(os.path.join(tmp, "c.json")))
            with mock.patch.object(pinyin, "lazy_pinyin", None):
                manager.add_contact(Contact("张明", "13800138000"))
                self.assertEqual(manager.convert_to_keypad_code("张明"), "")
                self.assertEqual(manager.search_by_keypad("942"), [])


if __name__ == "__main__":
    unittest.main()
