#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人数据导出模块

该模块提供联系人数据的导出功能，支持导出为 Excel、TXT 和 Markdown 三种格式。

主要功能：
1. 导出联系人为 Excel 文件
2. 导出联系人为 TXT 文件
3. 导出联系人为 Markdown 文件
4. 统一的导出接口和错误处理

设计说明：
1. openpyxl 采用**惰性导入**：未安装时程序仍可正常启动，只是 Excel 导出不可用，
   并给出明确的安装提示；同时本模块因此可以在无 openpyxl 的环境下被导入和测试。
2. 本模块不依赖 tkinter，用户提示通过 notifier 回调交给 GUI 层（见 notifier.py）。
"""

import logging
from abc import ABC
from typing import Callable, List, Optional

from contact import Contact
from notifier import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING, Notifier, notify

logger = logging.getLogger(__name__)

# 缺少 openpyxl 时统一给出的提示，避免用户面对一句裸的 ImportError
_OPENPYXL_HINT = "缺少 openpyxl 依赖，无法处理 Excel 文件。请执行: pip install -r requirements.txt"


def _require_openpyxl():
    """惰性导入 openpyxl

    Returns:
        module: openpyxl 模块

    Raises:
        ImportError: 未安装 openpyxl
    """
    try:
        import openpyxl
    except ImportError as e:
        raise ImportError(_OPENPYXL_HINT) from e
    return openpyxl


class BaseExporter(ABC):
    """导出器基类，用于复用导出逻辑

    提供通用的导出流程：参数校验、异常捕获、结果提示，
    具体写文件的动作由子类以 export_impl 的形式传入。
    """

    @classmethod
    def export(
        cls,
        contacts: List[Contact],
        file_path: str,
        export_name: str,
        export_impl: Callable[[List[Contact], str], None],
        notifier: Optional[Notifier] = None,
    ) -> bool:
        """通用导出方法

        Args:
            contacts: 要导出的联系人列表
            file_path: 导出文件路径
            export_name: 导出格式名称，用于日志与提示文案
            export_impl: 具体的导出实现函数，签名为 (contacts, file_path)
            notifier: 可选的通知回调，用于向用户展示提示

        Returns:
            bool: 导出是否成功
        """
        if not isinstance(contacts, list):
            notify(notifier, LEVEL_ERROR, "联系人列表必须是列表类型")
            return False

        if not isinstance(file_path, str) or not file_path:
            notify(notifier, LEVEL_ERROR, "文件路径必须是非空字符串")
            return False

        if not contacts:
            notify(notifier, LEVEL_WARNING, "没有联系人可以导出")
            return False

        try:
            export_impl(contacts, file_path)
        except PermissionError as e:
            logger.error("导出 %s 到 %s 时权限不足: %s", export_name, file_path, e)
            notify(notifier, LEVEL_ERROR, f"没有写入权限: {file_path}")
            return False
        except ImportError as e:
            logger.error("导出 %s 失败: %s", export_name, e)
            notify(notifier, LEVEL_ERROR, str(e))
            return False
        except Exception as e:
            logger.error("导出 %s 到 %s 失败: %s", export_name, file_path, e, exc_info=True)
            notify(notifier, LEVEL_ERROR, f"导出失败: {e}")
            return False

        logger.info("成功导出 %d 条联系人到 %s (%s)", len(contacts), file_path, export_name)
        notify(notifier, LEVEL_INFO, f"联系人已导出到 {file_path}")
        return True


class ExcelExporter(BaseExporter):
    """Excel 导出器，将联系人数据导出为 .xlsx 文件"""

    @staticmethod
    def export_to_excel(
        contacts: List[Contact],
        file_path: str = "contacts.xlsx",
        notifier: Optional[Notifier] = None,
    ) -> bool:
        """导出联系人为 Excel 文件

        Args:
            contacts: 要导出的联系人列表
            file_path: 导出文件路径（可选，默认为 contacts.xlsx）
            notifier: 可选的通知回调

        Returns:
            bool: 导出是否成功
        """

        def _export_impl(contacts: List[Contact], file_path: str) -> None:
            openpyxl = _require_openpyxl()

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "联系人列表"

            ws.append(["姓名", "电话", "邮箱", "国家/地区", "备注", "常用联系人"])

            for contact in contacts:
                if not isinstance(contact, Contact):
                    logger.warning("跳过非 Contact 对象: %r", contact)
                    continue
                ws.append([
                    contact.name,
                    contact.phone,
                    contact.email,
                    contact.country,
                    contact.remark,
                    "是" if contact.is_frequent else "否",
                ])

            wb.save(file_path)

        return ExcelExporter.export(contacts, file_path, "Excel", _export_impl, notifier)


class TXTExporter(BaseExporter):
    """TXT 导出器，将联系人数据导出为纯文本文件"""

    @staticmethod
    def export_to_txt(
        contacts: List[Contact],
        file_path: str = "contacts.txt",
        notifier: Optional[Notifier] = None,
    ) -> bool:
        """导出联系人为 TXT 文件

        Args:
            contacts: 要导出的联系人列表
            file_path: 导出文件路径（可选，默认为 contacts.txt）
            notifier: 可选的通知回调

        Returns:
            bool: 导出是否成功
        """

        def _export_impl(contacts: List[Contact], file_path: str) -> None:
            # 先过滤出有效对象，保证下面的编号连续、不跳号
            valid = [c for c in contacts if isinstance(c, Contact)]
            for skipped in (c for c in contacts if not isinstance(c, Contact)):
                logger.warning("跳过非 Contact 对象: %r", skipped)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("EasyLink 通讯录\n")
                f.write("=" * 50 + "\n\n")

                for i, contact in enumerate(valid, 1):
                    f.write(f"联系人 {i}:\n")
                    f.write(f"姓名: {contact.name}\n")
                    f.write(f"电话: {contact.phone}\n")
                    f.write(f"邮箱: {contact.email}\n")
                    f.write(f"国家/地区: {contact.country}\n")
                    f.write(f"备注: {contact.remark}\n")
                    f.write(f"常用联系人: {'是' if contact.is_frequent else '否'}\n")
                    f.write("-" * 50 + "\n\n")

        return TXTExporter.export(contacts, file_path, "TXT", _export_impl, notifier)


class MDExporter(BaseExporter):
    """Markdown 导出器，将联系人数据导出为 Markdown 表格"""

    @staticmethod
    def export_to_md(
        contacts: List[Contact],
        file_path: str = "contacts.md",
        notifier: Optional[Notifier] = None,
    ) -> bool:
        """导出联系人为 Markdown 文件

        Args:
            contacts: 要导出的联系人列表
            file_path: 导出文件路径（可选，默认为 contacts.md）
            notifier: 可选的通知回调

        Returns:
            bool: 导出是否成功
        """

        def _export_impl(contacts: List[Contact], file_path: str) -> None:
            valid = [c for c in contacts if isinstance(c, Contact)]
            for skipped in (c for c in contacts if not isinstance(c, Contact)):
                logger.warning("跳过非 Contact 对象: %r", skipped)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("# EasyLink 通讯录\n\n")
                f.write("| 姓名 | 电话 | 邮箱 | 国家/地区 | 备注 | 常用联系人 |\n")
                f.write("|------|------|------|------------|------|------------|\n")

                for contact in valid:
                    f.write(
                        "| {} | {} | {} | {} | {} | {} |\n".format(
                            _escape_md(contact.name),
                            _escape_md(contact.phone),
                            _escape_md(contact.email),
                            _escape_md(contact.country),
                            _escape_md(contact.remark),
                            "是" if contact.is_frequent else "否",
                        )
                    )

        return MDExporter.export(contacts, file_path, "Markdown", _export_impl, notifier)


def _escape_md(text: str) -> str:
    """转义 Markdown 表格中的竖线，避免备注内容破坏表格结构"""
    return (text or "").replace("\\", "\\\\").replace("|", "\\|")
