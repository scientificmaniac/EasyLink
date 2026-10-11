#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""存储层（DataStorage / SQLiteStorage）的单元测试"""

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from contact import Contact
from storage import DataStorage, SQLiteStorage


def sample_contacts():
    """构造一组测试联系人"""
    return [
        Contact("张明", "13800138000", "zhang@example.com", "大学同学", True),
        Contact("Emma Wilson", "+8613555222222", "emma@example.com", "", False),
        Contact("李四", "13900139000", "", "同事", False),
    ]


class StorageContractMixin:
    """两种存储实现都应满足的行为契约"""

    storage: object

    def make_storage(self):
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = self.make_storage()

    def test_starts_empty(self):
        self.assertEqual(self.storage.get_contacts_count(), 0)

    def test_add_and_persist(self):
        contact = sample_contacts()[0]
        self.storage.add_contact(contact)
        self.assertEqual(self.storage.get_contacts_count(), 1)
        self.assertIs(self.storage.get_contact_by_phone(contact.phone), contact)

        reopened = self.make_storage()
        self.assertEqual(reopened.get_contacts_count(), 1)
        self.assertEqual(reopened.contacts[0].name, contact.name)
        self.assertTrue(reopened.contacts[0].is_frequent)

    def test_update_persists(self):
        for contact in sample_contacts():
            self.storage.add_contact(contact)

        updated = Contact("张明改", "13800138000", "new@example.com", "改过", False)
        self.storage.update_contact(0, updated)
        self.assertEqual(self.storage.contacts[0].name, "张明改")

        reopened = self.make_storage()
        self.assertEqual(reopened.contacts[0].name, "张明改")
        self.assertEqual(reopened.contacts[0].email, "new@example.com")

    def test_delete_persists(self):
        for contact in sample_contacts():
            self.storage.add_contact(contact)

        self.storage.delete_contact(1)
        self.assertEqual(self.storage.get_contacts_count(), 2)
        self.assertIsNone(self.storage.get_contact_by_phone("+8613555222222"))
        self.assertEqual(self.make_storage().get_contacts_count(), 2)

    def test_clear_persists(self):
        self.storage.add_contacts(sample_contacts())
        self.storage.clear_contacts()
        self.assertEqual(self.storage.get_contacts_count(), 0)
        self.assertEqual(self.make_storage().get_contacts_count(), 0)

    def test_invalid_index_raises(self):
        with self.assertRaises(IndexError):
            self.storage.delete_contact(0)
        with self.assertRaises(IndexError):
            self.storage.update_contact(5, sample_contacts()[0])

    def test_non_contact_object_rejected(self):
        with self.assertRaises(TypeError):
            self.storage.add_contact("not a contact")

    def test_get_contact_by_phone_type_check(self):
        with self.assertRaises(TypeError):
            self.storage.get_contact_by_phone(13800138000)

    def test_batch_add(self):
        self.storage.add_contacts(sample_contacts())
        self.assertEqual(self.storage.get_contacts_count(), 3)
        self.assertEqual(self.make_storage().get_contacts_count(), 3)

    def test_batch_add_empty_is_noop(self):
        self.storage.add_contacts([])
        self.assertEqual(self.storage.get_contacts_count(), 0)


class TestDataStorage(StorageContractMixin, unittest.TestCase):
    """JSON 文件存储"""

    def make_storage(self):
        return DataStorage(os.path.join(self.tmp.name, "contacts.json"))


class TestSQLiteStorage(StorageContractMixin, unittest.TestCase):
    """SQLite 数据库存储"""

    def make_storage(self):
        return SQLiteStorage(os.path.join(self.tmp.name, "contacts.db"))


class TestDataStorageSpecifics(unittest.TestCase):
    """JSON 存储专有行为"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "contacts.json")

    def test_missing_file_initializes_empty(self):
        self.assertEqual(DataStorage(self.path).get_contacts_count(), 0)

    def test_atomic_write_leaves_no_temp_file(self):
        storage = DataStorage(self.path)
        storage.add_contact(sample_contacts()[0])
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_invalid_json_raises_value_error(self):
        Path(self.path).write_text("{ not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            DataStorage(self.path)

    def test_non_list_json_raises_value_error(self):
        Path(self.path).write_text('{"name": "x"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            DataStorage(self.path)

    def test_path_is_directory_raises(self):
        with self.assertRaises(IsADirectoryError):
            DataStorage(self.tmp.name)

    def test_non_string_path_rejected(self):
        with self.assertRaises(TypeError):
            DataStorage(123)

    def test_invalid_records_are_skipped(self):
        payload = [
            {"name": "张明", "phone": "13800138000"},
            {"name": "缺少电话"},
            {"name": "李四", "phone": "not-a-phone"},
        ]
        Path(self.path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        storage = DataStorage(self.path)
        self.assertEqual(storage.get_contacts_count(), 1)
        self.assertEqual(len(storage._skipped_records), 2)

    def test_backup_created_before_overwriting_skipped_data(self):
        """回归：跳过无效记录后一旦保存，被跳过的原始数据会被永久覆盖"""
        payload = [
            {"name": "张明", "phone": "13800138000"},
            {"name": "缺少电话"},
            {"name": "李四", "phone": "not-a-phone"},
        ]
        Path(self.path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        storage = DataStorage(self.path)
        self.assertEqual([p for p in os.listdir(self.tmp.name) if p.endswith(".bak")], [])

        storage.add_contact(Contact("王五", "13700137000"))

        backups = [p for p in os.listdir(self.tmp.name) if p.endswith(".bak")]
        self.assertEqual(len(backups), 1, "覆盖写之前应自动备份原文件")
        original = json.loads(Path(os.path.join(self.tmp.name, backups[0])).read_text(encoding="utf-8"))
        self.assertEqual(len(original), 3, "备份应保留覆盖前的全部原始记录")

    def test_backup_created_only_once(self):
        """回归：备份标记未清空会导致每次保存都重复生成备份文件"""
        payload = [{"name": "张明", "phone": "13800138000"}, {"name": "缺少电话"}]
        Path(self.path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        storage = DataStorage(self.path)
        storage.add_contact(Contact("王五", "13700137000"))
        storage.add_contact(Contact("赵六", "13600136000"))

        backups = [p for p in os.listdir(self.tmp.name) if p.endswith(".bak")]
        self.assertEqual(len(backups), 1)


class TestSQLiteStorageSpecifics(unittest.TestCase):
    """SQLite 存储专有行为"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "contacts.db")
        self.storage = SQLiteStorage(self.path)

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.path)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def test_duplicate_phone_rejected(self):
        self.storage.add_contact(sample_contacts()[0])
        with self.assertRaises(ValueError):
            self.storage.add_contact(sample_contacts()[0])
        self.assertEqual(self.storage.get_contacts_count(), 1)

    def test_update_to_taken_phone_rejected(self):
        for contact in sample_contacts()[:2]:
            self.storage.add_contact(contact)

        with self.assertRaises(ValueError):
            self.storage.update_contact(0, Contact("冲突", "+8613555222222"))
        self.assertEqual(self.storage.contacts[0].phone, "13800138000")

    def test_update_missing_row_raises_instead_of_silent_loss(self):
        """回归：UPDATE 影响 0 行时曾静默提交，界面提示成功而数据并未写入"""
        self.storage.add_contact(sample_contacts()[0])
        # 制造「内存与数据库不一致」：内存中的号码在库里并不存在
        self.storage.contacts[0].phone = "19999999999"

        with self.assertRaises(KeyError):
            self.storage.update_contact(0, Contact("张明改", "19999999999", "new@example.com"))

        rows = self.query("SELECT email FROM contacts WHERE phone=?", ("13800138000",))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "zhang@example.com", "数据库内容不应被改动")

    def test_delete_missing_row_raises(self):
        self.storage.add_contact(sample_contacts()[0])
        self.storage.contacts[0].phone = "19999999999"

        with self.assertRaises(KeyError):
            self.storage.delete_contact(0)
        self.assertEqual(self.storage.get_contacts_count(), 1)

    def test_batch_add_rolls_back_on_duplicate(self):
        self.storage.add_contact(sample_contacts()[0])
        batch = [Contact("新一", "13700137000"), Contact("重复", "13800138000")]

        with self.assertRaises(ValueError):
            self.storage.add_contacts(batch)
        self.assertEqual(self.storage.get_contacts_count(), 1, "整批应回滚，不留部分写入")
        self.assertEqual(len(self.query("SELECT id FROM contacts")), 1)

    def test_single_add_keeps_existing_ids(self):
        """回归：曾每次增删改都整表 DELETE+INSERT，使自增 id 无限膨胀"""
        for contact in sample_contacts():
            self.storage.add_contact(contact)
        before = [row[0] for row in self.query("SELECT id FROM contacts ORDER BY id")]

        self.storage.add_contact(Contact("王五", "13700137000"))

        after = [row[0] for row in self.query("SELECT id FROM contacts ORDER BY id")]
        self.assertEqual(len(after), 4)
        self.assertEqual(after[:3], before, "已有记录的 id 不应被重排")

    def test_country_persisted_and_reused(self):
        contact = Contact("A", "+886912345678")
        self.storage.add_contact(contact)
        reopened = SQLiteStorage(self.path)
        self.assertEqual(reopened.contacts[0].country, "中国台湾")


if __name__ == "__main__":
    unittest.main()
