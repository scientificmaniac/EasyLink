#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人数据导入模块

该模块提供联系人数据的导入功能，支持从 Excel、TXT、Markdown 和 JSON 文件中导入。

主要功能：
1. 从 Excel 文件导入联系人
2. 从 TXT 文件导入联系人
3. 从 Markdown 文件导入联系人
4. 从 JSON 文件导入联系人
5. 统一的导入接口和错误处理
6. 重复联系人检测

设计说明：
1. openpyxl 采用**惰性导入**，未安装时程序仍可启动，仅 Excel 导入不可用。
2. 本模块不依赖 tkinter，用户提示通过 notifier 回调交给 GUI 层（见 notifier.py）。
3. Markdown / TXT 的解析与 exporter 的写出格式严格对称，
   保证「导出后再导入」不丢内容、不错列。
"""

import json
import logging
import os
from abc import ABC
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

from contact import Contact, coerce_is_frequent
from notifier import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING, Notifier, notify
from validator import Validator

if TYPE_CHECKING:  # 仅用于类型标注，避免运行时多余依赖
    from contact_manager import ContactManager

logger = logging.getLogger(__name__)

# 缺少 openpyxl 时统一给出的提示
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


def _cell_to_str(value: Any) -> str:
    """把 Excel 单元格值转成字符串

    Excel 中的电话号码若以数字格式存储，会被读成 float（如 13800138000.0），
    直接 str() 会得到带 `.0` 的非法号码，因此整数型浮点需还原为整数文本。

    Args:
        value: 单元格原始值

    Returns:
        str: 规范化后的文本
    """
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _split_md_row(line: str) -> List[str]:
    """按未转义的竖线切分 Markdown 表格行，并还原转义字符

    导出时备注中的 `|` 会被写成 `\\|`。这里必须把它视为普通字符而非列分隔符，
    否则「含竖线的联系人」导出后再导入会整体错列。

    Args:
        line: 一行 Markdown 表格文本

    Returns:
        List[str]: 各列文本；首尾由行首行尾的竖线产生的空串也会保留
    """
    parts: List[str] = []
    buf: List[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "\\" and i + 1 < n and line[i + 1] in "\\|":
            buf.append(line[i + 1])
            i += 2
        elif ch == "|":
            parts.append("".join(buf).strip())
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    parts.append("".join(buf).strip())
    return parts


def _is_md_separator(line: str) -> bool:
    """判断是否为 Markdown 表格的分隔行（如 |---|---|）

    不依赖固定列宽，因此用户手工调整表格后仍能正确解析。

    Args:
        line: 一行 Markdown 文本

    Returns:
        bool: 是否为分隔行
    """
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    return all(ch in "|-: \t" for ch in stripped)


class BaseImporter(ABC):
    """导入器基类，用于复用导入流程

    提供通用的导入流程：文件存在性检查、扩展名验证、异常捕获，
    具体解析动作由子类以 parse_func 的形式传入。
    """

    @classmethod
    def import_from_file(
        cls,
        file_path: str,
        expected_ext: str,
        import_name: str,
        parse_func: Callable[[str], List[Contact]],
        notifier: Optional[Notifier] = None,
    ) -> Tuple[bool, List[Contact]]:
        """通用导入方法

        Args:
            file_path: 导入文件路径
            expected_ext: 预期的文件扩展名（如 '.xlsx'）
            import_name: 导入格式名称，用于日志与提示文案
            parse_func: 具体的解析函数，签名为 (file_path) -> List[Contact]
            notifier: 可选的通知回调

        Returns:
            Tuple[bool, List[Contact]]: (导入是否成功, 导入的联系人列表)
        """
        if not isinstance(file_path, str) or not file_path:
            notify(notifier, LEVEL_ERROR, "文件路径必须是非空字符串")
            return False, []

        if not os.path.exists(file_path):
            notify(notifier, LEVEL_ERROR, f"文件不存在: {file_path}")
            return False, []

        if not os.path.isfile(file_path):
            notify(notifier, LEVEL_ERROR, f"不是有效的文件: {file_path}")
            return False, []

        if not file_path.lower().endswith(expected_ext):
            notify(notifier, LEVEL_ERROR, f"不是有效的{import_name}文件，应为 {expected_ext} 格式")
            return False, []

        try:
            contacts = parse_func(file_path)
        except PermissionError as e:
            logger.error("读取 %s 文件权限不足: %s", import_name, e)
            notify(notifier, LEVEL_ERROR, f"没有读取权限: {e}")
            return False, []
        except ImportError as e:
            logger.error("%s 导入失败: %s", import_name, e)
            notify(notifier, LEVEL_ERROR, str(e))
            return False, []
        except Exception as e:
            logger.error("%s 导入失败: %s", import_name, e, exc_info=True)
            notify(notifier, LEVEL_ERROR, f"{import_name}导入失败: {e}")
            return False, []

        logger.info("%s 导入解析完成: 得到 %d 条有效联系人", import_name, len(contacts))
        return True, contacts

    @staticmethod
    def _create_contact(
        name: str,
        phone: str,
        email: str = "",
        remark: str = "",
        is_frequent: bool = False,
    ) -> Contact:
        """创建并校验联系人对象

        Args:
            name: 姓名
            phone: 电话
            email: 邮箱（可选）
            remark: 备注（可选）
            is_frequent: 是否为常用联系人（可选）

        Returns:
            Contact: 联系人对象

        Raises:
            ValueError: 如果联系人数据无效
        """
        valid, msg = Validator.validate_contact_data(name, phone, email, remark)
        if not valid:
            logger.warning("跳过无效联系人记录: %s", msg)
            raise ValueError(msg)
        return Contact(name, phone, email, remark, is_frequent)


class ExcelImporter(BaseImporter):
    """Excel 导入器，从 .xlsx 文件导入联系人"""

    @staticmethod
    def import_from_excel(
        file_path: str, notifier: Optional[Notifier] = None
    ) -> Tuple[bool, List[Contact]]:
        """从 Excel 文件导入联系人

        Args:
            file_path: Excel 文件路径
            notifier: 可选的通知回调

        Returns:
            Tuple[bool, List[Contact]]: (导入是否成功, 导入的联系人列表)
        """

        def _parse_excel(file_path: str) -> List[Contact]:
            openpyxl = _require_openpyxl()

            contacts: List[Contact] = []
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            try:
                ws = wb.active
                # 跳过表头，从第二行开始读取数据
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row is None or len(row) < 2:
                        continue

                    name = _cell_to_str(row[0])
                    phone = _cell_to_str(row[1])
                    if not name or not phone:
                        continue

                    email = _cell_to_str(row[2]) if len(row) > 2 else ""
                    # 国家/地区由系统根据电话自动推断，不采用导入值
                    remark = _cell_to_str(row[4]) if len(row) > 4 else ""
                    is_frequent = row[5] == "是" if len(row) > 5 else False

                    try:
                        contacts.append(
                            BaseImporter._create_contact(name, phone, email, remark, is_frequent)
                        )
                    except ValueError:
                        continue
            finally:
                wb.close()

            return contacts

        return BaseImporter.import_from_file(
            file_path, ".xlsx", "Excel", _parse_excel, notifier
        )


class TXTImporter(BaseImporter):
    """TXT 导入器，读取由 TXTExporter 生成的文本格式"""

    # 字段前缀，与 TXTExporter 的写出格式保持一致
    _FIELD_PREFIXES = {
        "姓名: ": "name",
        "电话: ": "phone",
        "邮箱: ": "email",
        "备注: ": "remark",
        "常用联系人: ": "is_frequent",
    }

    @staticmethod
    def import_from_txt(
        file_path: str, notifier: Optional[Notifier] = None
    ) -> Tuple[bool, List[Contact]]:
        """从 TXT 文件导入联系人

        Args:
            file_path: TXT 文件路径
            notifier: 可选的通知回调

        Returns:
            Tuple[bool, List[Contact]]: (导入是否成功, 导入的联系人列表)
        """

        def _collect(current: dict, contacts: List[Contact]) -> None:
            """把一条已解析的记录加入结果列表（字段不全则丢弃）"""
            if not current:
                return
            name, phone = current.get("name", ""), current.get("phone", "")
            if not name or not phone:
                logger.warning("跳过字段不完整的 TXT 记录: %r", current)
                return
            try:
                contacts.append(
                    BaseImporter._create_contact(
                        name,
                        phone,
                        current.get("email", ""),
                        current.get("remark", ""),
                        bool(current.get("is_frequent", False)),
                    )
                )
            except ValueError as e:
                logger.warning("跳过无效的 TXT 记录: %s", e)

        def _parse_txt(file_path: str) -> List[Contact]:
            contacts: List[Contact] = []

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            current: dict = {}
            for raw_line in lines:
                line = raw_line.strip()

                if line.startswith("联系人 ") and line.endswith(":"):
                    # 遇到新联系人：先保存上一条，再**无条件**重置缓冲，
                    # 否则上一条的残留字段（如邮箱）会污染下一条记录。
                    _collect(current, contacts)
                    current = {}
                    continue

                for prefix, field in TXTImporter._FIELD_PREFIXES.items():
                    if line.startswith(prefix):
                        value = line[len(prefix):]
                        current[field] = value == "是" if field == "is_frequent" else value
                        break

            _collect(current, contacts)
            return contacts

        return BaseImporter.import_from_file(file_path, ".txt", "TXT", _parse_txt, notifier)


class MDImporter(BaseImporter):
    """Markdown 导入器，读取由 MDExporter 生成的表格"""

    @staticmethod
    def import_from_md(
        file_path: str, notifier: Optional[Notifier] = None
    ) -> Tuple[bool, List[Contact]]:
        """从 Markdown 文件导入联系人

        Args:
            file_path: Markdown 文件路径
            notifier: 可选的通知回调

        Returns:
            Tuple[bool, List[Contact]]: (导入是否成功, 导入的联系人列表)
        """

        def _parse_md(file_path: str) -> List[Contact]:
            contacts: List[Contact] = []

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for raw_line in lines:
                line = raw_line.strip()
                if not line.startswith("|") or _is_md_separator(line):
                    continue

                # 行首行尾各有一个竖线，切分后首尾为空串，去掉它们即为各列
                parts = _split_md_row(line)[1:-1]
                if len(parts) < 2 or parts[0] == "姓名":
                    continue

                name, phone = parts[0], parts[1]
                email = parts[2] if len(parts) > 2 else ""
                # 第 4 列为国家/地区，由系统根据电话自动推断，此处忽略
                remark = parts[4] if len(parts) > 4 else ""
                is_frequent = parts[5] == "是" if len(parts) > 5 else False

                try:
                    contacts.append(
                        BaseImporter._create_contact(name, phone, email, remark, is_frequent)
                    )
                except ValueError as e:
                    logger.warning("跳过无效的 Markdown 记录: %s", e)

            return contacts

        return BaseImporter.import_from_file(file_path, ".md", "Markdown", _parse_md, notifier)


class JSONImporter(BaseImporter):
    """JSON 导入器，读取联系人字典列表"""

    @staticmethod
    def import_from_json(
        file_path: str, notifier: Optional[Notifier] = None
    ) -> Tuple[bool, List[Contact]]:
        """从 JSON 文件导入联系人

        Args:
            file_path: JSON 文件路径
            notifier: 可选的通知回调

        Returns:
            Tuple[bool, List[Contact]]: (导入是否成功, 导入的联系人列表)
        """

        def _parse_json(file_path: str) -> List[Contact]:
            contacts: List[Contact] = []

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("JSON 数据格式不正确，应为联系人列表")

            for contact_data in data:
                if not isinstance(contact_data, dict):
                    logger.warning("跳过非字典的 JSON 条目: %r", contact_data)
                    continue

                name = _cell_to_str(contact_data.get("name"))
                phone = _cell_to_str(contact_data.get("phone"))
                if not name or not phone:
                    logger.warning("跳过缺少姓名或电话的 JSON 条目: %r", contact_data)
                    continue

                email = _cell_to_str(contact_data.get("email"))
                remark = _cell_to_str(contact_data.get("remark"))

                try:
                    # 用与 Contact.from_dict 相同的规则解析布尔值：
                    # 直接 bool("false") 会得到 True，而拒绝 0/1 又会丢掉整条记录
                    is_frequent = coerce_is_frequent(contact_data.get("is_frequent", False))
                    contacts.append(
                        BaseImporter._create_contact(name, phone, email, remark, is_frequent)
                    )
                except (TypeError, ValueError) as e:
                    logger.warning("跳过无效的 JSON 记录: %s", e)

            return contacts

        return BaseImporter.import_from_file(file_path, ".json", "JSON", _parse_json, notifier)


class DataImporter:
    """统一数据导入入口，根据文件扩展名自动选择导入方式"""

    # 扩展名 -> 导入器
    _IMPORTERS = {
        ".xlsx": ExcelImporter.import_from_excel,
        ".txt": TXTImporter.import_from_txt,
        ".md": MDImporter.import_from_md,
        ".json": JSONImporter.import_from_json,
    }

    @staticmethod
    def import_contacts(
        file_path: str,
        contact_manager: "ContactManager",
        notifier: Optional[Notifier] = None,
    ) -> bool:
        """统一导入入口：按扩展名选择解析方式，并把结果批量写入管理器

        Args:
            file_path: 导入文件路径
            contact_manager: 联系人管理器对象，需提供 add_contacts 方法
            notifier: 可选的通知回调

        Returns:
            bool: 是否至少导入了一条联系人
        """
        if not isinstance(file_path, str) or not file_path:
            notify(notifier, LEVEL_ERROR, "文件路径必须是非空字符串")
            return False

        ext = os.path.splitext(file_path)[1].lower()
        importer = DataImporter._IMPORTERS.get(ext)
        if importer is None:
            notify(notifier, LEVEL_ERROR, f"不支持的文件格式: {ext or '(无扩展名)'}")
            return False

        success, contacts = importer(file_path, notifier)
        if not success:
            return False

        if not contacts:
            notify(notifier, LEVEL_WARNING, "文件中没有可导入的有效联系人")
            return False

        # 一次性批量写入：逐个 add_contact 会反复重建搜索缓存，导入大批量数据时是 O(N²)
        imported, skipped = contact_manager.add_contacts(contacts)

        notify(
            notifier,
            LEVEL_INFO,
            f"成功导入 {imported} 个联系人\n"
            f"跳过 {skipped} 个重复或无效联系人\n"
            f"共处理 {len(contacts)} 个联系人",
        )
        logger.info("导入完成: 成功 %d 条，跳过 %d 条，总计 %d 条", imported, skipped, len(contacts))
        return imported > 0
