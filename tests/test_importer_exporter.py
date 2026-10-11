#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入导出的单元测试

重点验证「导出后再导入」的往返一致性 —— 这是数据备份/迁移功能的正确性底线。
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from contact import Contact
from contact_manager import ContactManager
from exporter import ExcelExporter, MDExporter, TXTExporter
from importer import DataImporter, ExcelImporter, JSONImporter, MDImporter, TXTImporter
from storage import DataStorage

try:
    import openpyxl  # noqa: F401
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class NotifierSpy:
    """替代 GUI 对话框的通知收集器"""

    def __init__(self):
        self.messages = []

    def __call__(self, level, message):
        self.messages.append((level, message))

    @property
    def levels(self):
        return [level for level, _ in self.messages]

    @property
    def last_message(self):
        return self.messages[-1][1] if self.messages else ""


def sample_contacts():
    return [
        Contact("张明", "13800138000", "zhang@example.com", "大学同学", True),
        # 备注为空，用于回归「空单元格被丢弃」的问题
        Contact("Emma Wilson", "+8613555222222", "emma@example.com", "", False),
        Contact("李四", "13900139000", "", "备注里有竖线 | 和反斜杠 \\", False),
    ]


class RoundTripMixin:
    """导出后必须能原样导入回来"""

    tmp: tempfile.TemporaryDirectory

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    @staticmethod
    def fields(contact):
        return (contact.name, contact.phone, contact.email, contact.remark, contact.is_frequent)

    def assertRoundTrip(self, original, restored):
        self.assertEqual(len(restored), len(original), "往返后的记录条数应一致")
        for src, dst in zip(original, restored):
            self.assertEqual(self.fields(dst), self.fields(src))


class TestTxtRoundTrip(RoundTripMixin, unittest.TestCase):
    """TXT 导出/导入"""

    def test_roundtrip(self):
        path = os.path.join(self.tmp.name, "contacts.txt")
        original = sample_contacts()

        self.assertTrue(TXTExporter.export_to_txt(original, path))
        ok, restored = TXTImporter.import_from_txt(path)

        self.assertTrue(ok)
        self.assertRoundTrip(original, restored)

    def test_record_numbering_is_continuous(self):
        """回归：导出时跳过非 Contact 对象会用到 enumerate 的序号，导致编号跳号"""
        path = os.path.join(self.tmp.name, "contacts.txt")
        TXTExporter.export_to_txt([sample_contacts()[0], "脏数据", sample_contacts()[2]], path)

        content = Path(path).read_text(encoding="utf-8")
        self.assertIn("联系人 1:", content)
        self.assertIn("联系人 2:", content)
        self.assertNotIn("联系人 3:", content)

    def test_incomplete_record_is_skipped(self):
        path = os.path.join(self.tmp.name, "partial.txt")
        Path(path).write_text(
            "个人通讯录\n\n联系人 1:\n姓名: 只有姓名\n\n联系人 2:\n姓名: 张三\n电话: 13800138000\n",
            encoding="utf-8",
        )
        ok, restored = TXTImporter.import_from_txt(path)
        self.assertTrue(ok)
        self.assertEqual([c.name for c in restored], ["张三"])

    def test_fields_do_not_leak_between_records(self):
        """回归：新记录标题出现时未重置缓冲，上一条的字段会污染下一条"""
        path = os.path.join(self.tmp.name, "leak.txt")
        Path(path).write_text(
            "联系人 1:\n姓名: 甲\n电话: 13800138000\n备注: 第一条的备注\n\n"
            "联系人 2:\n姓名: 乙\n电话: 13900139000\n",
            encoding="utf-8",
        )
        ok, restored = TXTImporter.import_from_txt(path)
        self.assertTrue(ok)
        self.assertEqual(restored[1].remark, "", "第二条不应继承第一条的备注")


class TestMdRoundTrip(RoundTripMixin, unittest.TestCase):
    """Markdown 导出/导入"""

    def test_roundtrip_including_empty_remark(self):
        """回归：解析时丢弃空单元格并要求至少 6 段，空备注的联系人被整行静默丢弃"""
        path = os.path.join(self.tmp.name, "contacts.md")
        original = sample_contacts()

        self.assertTrue(MDExporter.export_to_md(original, path))
        ok, restored = MDImporter.import_from_md(path)

        self.assertTrue(ok)
        self.assertRoundTrip(original, restored)

    def test_pipe_in_remark_is_escaped_and_restored(self):
        """回归：备注中的竖线会撑破表格列，导出需转义、导入需还原"""
        path = os.path.join(self.tmp.name, "pipe.md")
        original = [Contact("李四", "13900139000", "", "含竖线 | 的备注")]

        MDExporter.export_to_md(original, path)
        raw = Path(path).read_text(encoding="utf-8")
        self.assertIn("\\|", raw, "导出时应转义竖线")

        ok, restored = MDImporter.import_from_md(path)
        self.assertTrue(ok)
        self.assertEqual(restored[0].remark, "含竖线 | 的备注")

    def test_separator_width_may_change(self):
        """分隔行不应依赖固定列宽"""
        path = os.path.join(self.tmp.name, "wide.md")
        Path(path).write_text(
            "# 通讯录\n\n"
            "| 姓名 | 电话 | 邮箱 | 国家/地区 | 备注 | 常用联系人 |\n"
            "|:-----|:-----|:-----|:----------|:-----|:-----------|\n"
            "| 张三 | 13800138000 | a@b.com | 中国 | 朋友 | 是 |\n",
            encoding="utf-8",
        )
        ok, restored = MDImporter.import_from_md(path)
        self.assertTrue(ok)
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].name, "张三")
        self.assertEqual(restored[0].remark, "朋友")
        self.assertTrue(restored[0].is_frequent)


class TestJsonImport(unittest.TestCase):
    """JSON 导入"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, data):
        path = os.path.join(self.tmp.name, name)
        Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_import_list(self):
        path = self.write("c.json", [
            {"name": "张明", "phone": "13800138000", "is_frequent": 1},
            {"name": "李四", "phone": "13900139000", "is_frequent": "false"},
        ])
        ok, contacts = JSONImporter.import_from_json(path)
        self.assertTrue(ok)
        self.assertEqual(len(contacts), 2)
        self.assertTrue(contacts[0].is_frequent)
        self.assertFalse(contacts[1].is_frequent)

    def test_invalid_entries_are_skipped(self):
        path = self.write("c.json", [
            {"name": "张明", "phone": "13800138000"},
            {"name": "缺少电话"},
            {"name": "电话非法", "phone": "abc"},
            "不是字典",
        ])
        ok, contacts = JSONImporter.import_from_json(path)
        self.assertTrue(ok)
        self.assertEqual([c.name for c in contacts], ["张明"])

    def test_non_list_json_is_rejected(self):
        path = self.write("c.json", {"name": "张明"})
        notifier = NotifierSpy()
        ok, contacts = JSONImporter.import_from_json(path, notifier=notifier)
        self.assertFalse(ok)
        self.assertEqual(contacts, [])
        self.assertEqual(notifier.levels, ["error"])


class TestImportFailures(unittest.TestCase):
    """导入失败路径"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_missing_file(self):
        notifier = NotifierSpy()
        ok, contacts = TXTImporter.import_from_txt(
            os.path.join(self.tmp.name, "none.txt"), notifier=notifier
        )
        self.assertFalse(ok)
        self.assertEqual(contacts, [])
        self.assertIn("不存在", notifier.last_message)

    def test_wrong_extension(self):
        path = os.path.join(self.tmp.name, "data.txt")
        Path(path).write_text("x", encoding="utf-8")
        notifier = NotifierSpy()
        ok, _ = MDImporter.import_from_md(path, notifier=notifier)
        self.assertFalse(ok)
        self.assertIn(".md", notifier.last_message)

    def test_directory_is_not_a_file(self):
        notifier = NotifierSpy()
        ok, _ = TXTImporter.import_from_txt(self.tmp.name, notifier=notifier)
        self.assertFalse(ok)

    def test_unsupported_extension(self):
        path = os.path.join(self.tmp.name, "data.csv")
        Path(path).write_text("a,b", encoding="utf-8")

        manager = ContactManager(DataStorage(os.path.join(self.tmp.name, "c.json")))
        notifier = NotifierSpy()
        self.assertFalse(DataImporter.import_contacts(path, manager, notifier=notifier))
        self.assertIn("不支持", notifier.last_message)

    def test_non_string_path(self):
        manager = ContactManager(DataStorage(os.path.join(self.tmp.name, "c.json")))
        notifier = NotifierSpy()
        self.assertFalse(DataImporter.import_contacts(123, manager, notifier=notifier))


class TestDataImporterEndToEnd(unittest.TestCase):
    """统一导入入口与管理器的协作"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manager = ContactManager(DataStorage(os.path.join(self.tmp.name, "c.json")))
        self.txt_path = os.path.join(self.tmp.name, "contacts.txt")
        TXTExporter.export_to_txt(sample_contacts(), self.txt_path)

    def test_import_into_empty_manager(self):
        notifier = NotifierSpy()
        ok = DataImporter.import_contacts(self.txt_path, self.manager, notifier=notifier)

        self.assertTrue(ok)
        self.assertEqual(self.manager.get_contacts_count(), 3)
        self.assertIn("info", notifier.levels)

    def test_second_import_skips_duplicates(self):
        DataImporter.import_contacts(self.txt_path, self.manager)
        notifier = NotifierSpy()

        ok = DataImporter.import_contacts(self.txt_path, self.manager, notifier=notifier)

        self.assertFalse(ok, "没有任何新增时应返回 False")
        self.assertEqual(self.manager.get_contacts_count(), 3)
        self.assertIn("跳过 3 个", notifier.last_message)

    def test_empty_source_file_warns(self):
        empty = os.path.join(self.tmp.name, "empty.txt")
        Path(empty).write_text("个人通讯录\n", encoding="utf-8")

        notifier = NotifierSpy()
        self.assertFalse(DataImporter.import_contacts(empty, self.manager, notifier=notifier))
        self.assertEqual(notifier.levels, ["warning"])


class TestExportFailures(unittest.TestCase):
    """导出失败路径"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_export_empty_list_warns(self):
        notifier = NotifierSpy()
        ok = TXTExporter.export_to_txt([], os.path.join(self.tmp.name, "c.txt"), notifier=notifier)
        self.assertFalse(ok)
        self.assertEqual(notifier.levels, ["warning"])

    def test_export_requires_list(self):
        notifier = NotifierSpy()
        ok = MDExporter.export_to_md("not a list", os.path.join(self.tmp.name, "c.md"), notifier=notifier)
        self.assertFalse(ok)
        self.assertEqual(notifier.levels, ["error"])

    def test_export_to_directory_reports_error(self):
        notifier = NotifierSpy()
        ok = TXTExporter.export_to_txt(sample_contacts(), self.tmp.name, notifier=notifier)
        self.assertFalse(ok)
        self.assertEqual(notifier.levels, ["error"])


@unittest.skipUnless(HAS_OPENPYXL, "未安装 openpyxl，跳过 Excel 往返测试")
class TestExcelRoundTrip(RoundTripMixin, unittest.TestCase):
    """Excel 导出/导入"""

    def test_roundtrip(self):
        path = os.path.join(self.tmp.name, "contacts.xlsx")
        original = sample_contacts()

        self.assertTrue(ExcelExporter.export_to_excel(original, path))
        ok, restored = ExcelImporter.import_from_excel(path)

        self.assertTrue(ok)
        self.assertRoundTrip(original, restored)

    def test_numeric_phone_cell_is_not_treated_as_float(self):
        """回归：Excel 中数字格式的电话号码会被读成 13800138000.0"""
        path = os.path.join(self.tmp.name, "numeric.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["姓名", "电话", "邮箱", "国家/地区", "备注", "常用联系人"])
        ws.append(["张三", 13800138000, "a@b.com", "中国", "朋友", "是"])
        wb.save(path)

        ok, restored = ExcelImporter.import_from_excel(path)
        self.assertTrue(ok)
        self.assertEqual(restored[0].phone, "13800138000")


class TestExcelWithoutOpenpyxl(unittest.TestCase):
    """未安装 openpyxl 时应给出可操作的提示，而不是直接崩溃"""

    @unittest.skipIf(HAS_OPENPYXL, "本机已安装 openpyxl")
    def test_export_reports_missing_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            notifier = NotifierSpy()
            ok = ExcelExporter.export_to_excel(
                sample_contacts(), os.path.join(tmp, "c.xlsx"), notifier=notifier
            )
            self.assertFalse(ok)
            self.assertIn("openpyxl", notifier.last_message)

    @unittest.skipIf(HAS_OPENPYXL, "本机已安装 openpyxl")
    def test_import_reports_missing_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "c.xlsx")
            Path(path).write_bytes(b"not really xlsx")
            notifier = NotifierSpy()
            ok, _ = ExcelImporter.import_from_excel(path, notifier=notifier)
            self.assertFalse(ok)
            self.assertIn("openpyxl", notifier.last_message)


if __name__ == "__main__":
    unittest.main()
