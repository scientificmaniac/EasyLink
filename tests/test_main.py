#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序入口（main.py）的迁移逻辑测试

main.py 在导入时不会创建窗口，因此可以在无图形交互的情况下测试其中的纯逻辑函数。
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main as main_module
from contact import Contact
from storage import SQLiteStorage


class TestJsonToSqliteMigration(unittest.TestCase):
    """contacts.json → contacts.db 的首次迁移"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.json_path = Path(self.tmp.name) / "contacts.json"
        self.db_path = Path(self.tmp.name) / "contacts.db"

    def write_json(self, payload):
        self.json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def run_migration(self):
        with mock.patch.object(main_module, "JSON_FILE", self.json_path), \
                mock.patch.object(main_module, "DB_FILE", self.db_path):
            main_module.migrate_data_from_json_to_sqlite()

    def open_database(self):
        return SQLiteStorage(str(self.db_path))

    def test_migrates_json_into_database(self):
        self.write_json([
            {"name": "张明", "phone": "13800138000", "is_frequent": True},
            {"name": "李四", "phone": "13900139000"},
        ])

        self.run_migration()

        self.assertTrue(self.db_path.exists())
        storage = self.open_database()
        self.assertEqual(storage.get_contacts_count(), 2)
        self.assertTrue(storage.get_contact_by_phone("13800138000").is_frequent)

    def test_missing_json_creates_nothing(self):
        self.run_migration()
        self.assertFalse(self.db_path.exists())

    def test_skips_when_database_already_has_data(self):
        self.write_json([{"name": "张明", "phone": "13800138000"}])
        existing = self.open_database()
        existing.add_contact(Contact("已有", "13700137000"))

        self.run_migration()

        storage = self.open_database()
        self.assertEqual(storage.get_contacts_count(), 1)
        self.assertEqual(storage.contacts[0].name, "已有")

    def test_backfills_when_database_exists_but_is_empty(self):
        """数据库已存在但为空时仍应补迁移，否则用户会看到一个空通讯录"""
        self.write_json([{"name": "张明", "phone": "13800138000"}])
        self.open_database()  # 仅创建空库

        self.run_migration()

        self.assertEqual(self.open_database().get_contacts_count(), 1)

    def test_single_bad_record_does_not_abort_the_rest(self):
        """回归：迁移中任一条失败即中断，后续联系人全部迁移不过去"""
        self.write_json([
            {"name": "张明", "phone": "13800138000"},
            {"name": "重复号码", "phone": "13800138000"},  # 触发唯一约束
            {"name": "李四", "phone": "13900139000"},
        ])

        self.run_migration()

        storage = self.open_database()
        self.assertEqual(storage.get_contacts_count(), 2, "单条失败不应中断后续迁移")
        self.assertEqual([c.name for c in storage.contacts], ["张明", "李四"])

    def test_unparseable_json_is_skipped_without_crashing(self):
        self.json_path.write_text("{ not json", encoding="utf-8")

        self.run_migration()  # 不应抛出异常

        self.assertFalse(self.db_path.exists())

    def test_empty_json_list_is_noop(self):
        self.write_json([])

        self.run_migration()

        self.assertFalse(self.db_path.exists())


class TestDatabasePaths(unittest.TestCase):
    """数据文件应锚定在脚本目录，而不是进程当前工作目录"""

    def test_paths_are_absolute_and_beside_the_script(self):
        script_dir = Path(main_module.__file__).resolve().parent
        for path in (main_module.JSON_FILE, main_module.DB_FILE, main_module.LOG_FILE):
            with self.subTest(path=path):
                self.assertTrue(path.is_absolute())
                self.assertEqual(path.parent, script_dir)


if __name__ == "__main__":
    unittest.main()
