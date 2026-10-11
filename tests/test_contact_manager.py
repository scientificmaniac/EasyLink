#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ContactManager 业务逻辑的单元测试"""

import os
import tempfile
import unittest

from contact import Contact
from contact_manager import ContactManager
from storage import DataStorage, SQLiteStorage


def make_contacts():
    return [
        Contact("张明", "13800138000", "zhang@example.com", "大学同学", True),
        Contact("Emma Wilson", "+8613555222222", "emma@example.com", "", False),
        Contact("David Wang", "13700137000", "david@example.com", "客户", True),
        Contact("李四", "13900139000", "", "同事", False),
    ]


class TestContactManager(unittest.TestCase):
    """基于 JSON 存储的管理器行为"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = DataStorage(os.path.join(self.tmp.name, "contacts.json"))
        self.manager = ContactManager(self.storage)

    def seed(self):
        imported, skipped = self.manager.add_contacts(make_contacts())
        self.assertEqual((imported, skipped), (4, 0))

    # ------------------------------------------------------------------
    # 构造与增删改
    # ------------------------------------------------------------------
    def test_rejects_none_storage(self):
        with self.assertRaises(ValueError):
            ContactManager(None)

    def test_rejects_non_storage_object(self):
        with self.assertRaises(TypeError):
            ContactManager(object())

    def test_add_contact(self):
        ok, msg = self.manager.add_contact(make_contacts()[0])
        self.assertTrue(ok, msg)
        self.assertEqual(self.manager.get_contacts_count(), 1)

    def test_add_duplicate_phone_rejected(self):
        self.manager.add_contact(make_contacts()[0])
        ok, msg = self.manager.add_contact(make_contacts()[0])
        self.assertFalse(ok)
        self.assertIn("已存在", msg)
        self.assertEqual(self.manager.get_contacts_count(), 1)

    def test_add_non_contact_raises(self):
        with self.assertRaises(TypeError):
            self.manager.add_contact("not a contact")

    def test_update_contact(self):
        self.seed()
        ok, msg = self.manager.update_contact(
            0, Contact("张明改", "13800138000", "new@example.com", "改过", False)
        )
        self.assertTrue(ok, msg)
        self.assertEqual(self.storage.contacts[0].name, "张明改")

    def test_update_to_taken_phone_rejected(self):
        self.seed()
        ok, msg = self.manager.update_contact(0, Contact("冲突", "13900139000"))
        self.assertFalse(ok)
        self.assertIn("已被其他联系人使用", msg)
        self.assertEqual(self.storage.contacts[0].name, "张明")

    def test_update_keeping_own_phone_is_allowed(self):
        """回归：曾用 list.index() 按值定位，合法修改可能被自我否决"""
        self.seed()
        ok, msg = self.manager.update_contact(
            0, Contact("张明改", "13800138000", "new@example.com", "大学同学", True)
        )
        self.assertTrue(ok, msg)

    def test_update_invalid_index_raises(self):
        self.seed()
        with self.assertRaises(IndexError):
            self.manager.update_contact(99, make_contacts()[0])

    def test_delete_contact(self):
        self.seed()
        ok, msg = self.manager.delete_contact(1)
        self.assertTrue(ok, msg)
        self.assertEqual(self.manager.get_contacts_count(), 3)
        self.assertIsNone(self.manager.storage.get_contact_by_phone("+8613555222222"))

    def test_delete_invalid_index_raises(self):
        with self.assertRaises(IndexError):
            self.manager.delete_contact(0)

    # ------------------------------------------------------------------
    # 批量导入
    # ------------------------------------------------------------------
    def test_batch_add_reports_counts(self):
        imported, skipped = self.manager.add_contacts(make_contacts())
        self.assertEqual((imported, skipped), (4, 0))

    def test_batch_add_skips_existing_and_duplicate_phones(self):
        self.manager.add_contact(make_contacts()[0])
        batch = [
            Contact("重复张明", "13800138000"),
            Contact("新人", "13600136000"),
            Contact("又一个新人", "13600136000"),  # 批次内重复
        ]
        imported, skipped = self.manager.add_contacts(batch)
        self.assertEqual(imported, 1)
        self.assertEqual(skipped, 2)
        self.assertEqual(self.manager.get_contacts_count(), 2)

    def test_batch_add_empty(self):
        self.assertEqual(self.manager.add_contacts([]), (0, 0))

    # ------------------------------------------------------------------
    # 常用标记
    # ------------------------------------------------------------------
    def test_set_frequent(self):
        self.seed()
        ok, msg = self.manager.set_frequent(1, True)
        self.assertTrue(ok, msg)
        self.assertTrue(self.storage.contacts[1].is_frequent)
        self.assertIn("Emma Wilson", [c.name for c in self.manager.get_frequent_contacts()])

    def test_set_frequent_no_change_is_noop(self):
        self.seed()
        ok, _ = self.manager.set_frequent(0, True)
        self.assertTrue(ok)
        self.assertTrue(self.storage.contacts[0].is_frequent)

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------
    def test_search_by_name_is_case_insensitive_substring(self):
        self.seed()
        self.assertEqual([c.name for c in self.manager.search_by_name("emma")], ["Emma Wilson"])
        self.assertEqual([c.name for c in self.manager.search_by_name("wang")], ["David Wang"])
        self.assertEqual(self.manager.search_by_name("不存在"), [])

    def test_search_by_phone_substring(self):
        self.seed()
        self.assertEqual([c.name for c in self.manager.search_by_phone("138001")], ["张明"])
        # 四个号码都包含 "13"
        self.assertEqual(len(self.manager.search_by_phone("13")), 4)

    def test_search_by_email(self):
        self.seed()
        self.assertEqual(len(self.manager.search_by_email("example.com")), 3)
        self.assertEqual([c.name for c in self.manager.search_by_email("DAVID@")], ["David Wang"])
        self.assertEqual(self.manager.search_by_email("nobody@"), [])

    def test_search_with_empty_keyword_returns_empty(self):
        self.seed()
        for search in (self.manager.search_by_name, self.manager.search_by_phone,
                       self.manager.search_by_email, self.manager.search_by_keypad):
            with self.subTest(search=search.__name__):
                self.assertEqual(search(""), [])

    def test_search_type_errors(self):
        with self.assertRaises(TypeError):
            self.manager.search_by_name(None)
        with self.assertRaises(TypeError):
            self.manager.search_by_phone(13800138000)

    def test_keypad_search_uses_prefix_matching(self):
        """回归：曾用子串匹配，输入单个数字会命中编码中段含该数字的其他人"""
        self.seed()
        # David Wang -> "328439264"
        self.assertEqual([c.name for c in self.manager.search_by_keypad("328")], ["David Wang"])
        # Emma Wilson -> "3662945766"
        self.assertEqual([c.name for c in self.manager.search_by_keypad("36")], ["Emma Wilson"])
        # 没有任何人的九键编码以 9 开头
        self.assertEqual(self.manager.search_by_keypad("9"), [])

    def test_keypad_search_rejects_non_digits(self):
        with self.assertRaises(ValueError):
            self.manager.search_by_keypad("abc")

    def test_keypad_code_for_chinese_name_is_empty(self):
        """中文姓名没有拉丁编码，九键搜索不应误命中它们"""
        self.seed()
        self.assertEqual(self.manager.convert_to_keypad_code("张明"), "")
        self.assertEqual(self.manager.search_by_keypad("364"), [])

    def test_search_all_combines_sources_without_duplicates(self):
        self.seed()
        self.assertEqual([c.name for c in self.manager.search_all("emma")], ["Emma Wilson"])
        self.assertEqual([c.name for c in self.manager.search_all("13900139000")], ["李四"])
        # 数字关键词同时可能命中电话与九键编码，结果不能重复
        results = self.manager.search_all("138")
        self.assertEqual(len(results), len({id(c) for c in results}))

    # ------------------------------------------------------------------
    # 缓存一致性
    # ------------------------------------------------------------------
    def test_cache_updated_after_add(self):
        self.seed()
        self.assertEqual(self.manager.search_by_name("王五"), [])
        self.manager.add_contact(Contact("王五", "13600136000"))
        self.assertEqual(len(self.manager.search_by_name("王五")), 1)

    def test_cache_updated_after_delete(self):
        self.seed()
        self.assertEqual(len(self.manager.search_by_name("张明")), 1)
        self.manager.delete_contact(0)
        self.assertEqual(self.manager.search_by_name("张明"), [])

    def test_cache_updated_after_update(self):
        self.seed()
        self.manager.update_contact(0, Contact("改名了", "13800138000"))
        self.assertEqual(self.manager.search_by_name("张明"), [])
        self.assertEqual(len(self.manager.search_by_name("改名了")), 1)

    def test_all_contacts_returns_copy(self):
        self.seed()
        contacts = self.manager.get_all_contacts()
        contacts.append(Contact("多余", "13500135000"))
        self.assertEqual(self.manager.get_contacts_count(), 4)

    def test_get_contact_by_index(self):
        self.seed()
        self.assertEqual(self.manager.get_contact_by_index(0).name, "张明")
        self.assertIsNone(self.manager.get_contact_by_index(99))


class TestContactManagerWithSQLite(unittest.TestCase):
    """管理器与 SQLite 存储组合时的关键路径"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = SQLiteStorage(os.path.join(self.tmp.name, "contacts.db"))
        self.manager = ContactManager(self.storage)

    def test_set_frequent_failure_keeps_original_state(self):
        """回归：就地翻转 is_frequent 后若保存失败，内存对象会停留在被改过的状态"""
        self.manager.add_contact(Contact("张明", "13800138000", is_frequent=True))
        # 制造写库失败：内存中的号码在数据库中并不存在
        self.storage.contacts[0].phone = "19999999999"

        ok, msg = self.manager.set_frequent(0, False)

        self.assertFalse(ok)
        self.assertTrue(self.storage.contacts[0].is_frequent, "保存失败时不应改动原对象")
        self.assertNotEqual(msg, "")

    def test_delete_reports_failure_instead_of_raising(self):
        self.manager.add_contact(Contact("张明", "13800138000"))
        self.storage.contacts[0].phone = "19999999999"

        ok, msg = self.manager.delete_contact(0)

        self.assertFalse(ok)
        self.assertIn("删除失败", msg)
        self.assertEqual(self.manager.get_contacts_count(), 1)

    def test_batch_import_then_persist(self):
        imported, _ = self.manager.add_contacts(make_contacts())
        self.assertEqual(imported, 4)

        reopened = SQLiteStorage(self.storage.db_path)
        self.assertEqual(len(reopened.contacts), 4)


if __name__ == "__main__":
    unittest.main()
