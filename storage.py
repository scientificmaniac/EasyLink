#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人数据存储模块

该模块负责联系人数据的持久化存储，包括数据的加载、保存、增删改查等功能。
支持两种存储方式：
1. JSON文件存储（DataStorage类）
2. SQLite数据库存储（SQLiteStorage类）

设计说明：
1. 增删改查的公共实现集中在 StorageBase 中，子类只负责「如何读写介质」
   （load_contacts / save_contacts）以及需要特殊优化的单条写入操作。
2. 本模块是一个库模块，**不配置全局日志**：日志级别与输出目标由程序入口
   （main.py）决定，避免覆盖宿主应用的日志配置。
3. 加载阶段无法解析的记录会被跳过，但它们仍存在于磁盘上。由于任何一次
   覆盖写都会使其永久消失，因此覆盖前会先自动备份原文件。
"""

import json
import logging
import os
import shutil
import sqlite3
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from contact import Contact


logger = logging.getLogger(__name__)

# 联系人表的列定义，保证各处 INSERT/UPDATE 的占位符与取值顺序完全一致
_CONTACT_COLUMNS = ("name", "phone", "email", "remark", "is_frequent", "country")
_INSERT_SQL = f"INSERT INTO contacts ({', '.join(_CONTACT_COLUMNS)}) VALUES (?, ?, ?, ?, ?, ?)"
_UPDATE_SQL = (
    "UPDATE contacts SET name=?, phone=?, email=?, remark=?, is_frequent=?, country=? "
    "WHERE phone=?"
)


class StorageBase(ABC):
    """存储基类，定义存储接口和公共的增删改查实现

    子类必须实现 load_contacts() 与 save_contacts()；其余方法在此处统一实现，
    子类不应重复拷贝。

    属性：
        contacts: 联系人列表
    """

    def __init__(self) -> None:
        """初始化存储基类"""
        self.contacts: List[Contact] = []
        # 加载阶段判定为无效、因而未进入 contacts 的原始记录。
        # 这些记录仍在磁盘上，覆盖写入前必须先备份，否则会造成不可逆的数据丢失。
        self._skipped_records: List[Any] = []

    # ------------------------------------------------------------------
    # 子类必须实现的接口
    # ------------------------------------------------------------------
    @abstractmethod
    def load_contacts(self) -> None:
        """从存储介质加载联系人数据到 self.contacts"""
        raise NotImplementedError

    @abstractmethod
    def save_contacts(self) -> None:
        """将 self.contacts 整体写入存储介质"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 公共增删改查
    # ------------------------------------------------------------------
    @staticmethod
    def _require_contact(contact: Contact) -> None:
        """校验传入对象确实是 Contact 实例

        Args:
            contact: 待校验的对象

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
        """
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")

    @staticmethod
    def _require_index(index: int, contacts: List[Contact]) -> None:
        """校验索引在合法范围内

        Args:
            index: 待校验的索引
            contacts: 当前联系人列表

        Raises:
            IndexError: 如果索引无效
        """
        if not isinstance(index, int) or not 0 <= index < len(contacts):
            raise IndexError("Invalid contact index")

    def add_contact(self, contact: Contact) -> None:
        """添加联系人

        Args:
            contact: 要添加的联系人对象

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
            ValueError: 如果电话号码已存在（仅由子类实现负责）
        """
        self._require_contact(contact)
        self.contacts.append(contact)
        self.save_contacts()

    def add_contacts(self, contacts: Iterable[Contact]) -> None:
        """批量添加联系人，只落盘一次

        导入场景下逐个 add_contact 会导致 N 次全量写入，这里合并为一次。

        Args:
            contacts: 待添加的联系人集合

        Raises:
            TypeError: 如果其中混入非 Contact 对象
        """
        batch = list(contacts)
        for contact in batch:
            self._require_contact(contact)
        if not batch:
            return
        self.contacts.extend(batch)
        self.save_contacts()

    def update_contact(self, index: int, contact: Contact) -> None:
        """更新指定索引处的联系人

        Args:
            index: 要更新的联系人索引
            contact: 新的联系人对象

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
            IndexError: 如果索引无效
        """
        self._require_contact(contact)
        self._require_index(index, self.contacts)
        self.contacts[index] = contact
        self.save_contacts()

    def delete_contact(self, index: int) -> None:
        """删除指定索引处的联系人

        Args:
            index: 要删除的联系人索引

        Raises:
            IndexError: 如果索引无效
        """
        self._require_index(index, self.contacts)
        del self.contacts[index]
        self.save_contacts()

    def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """根据电话号码查找联系人

        Args:
            phone: 要查找的电话号码

        Returns:
            Optional[Contact]: 找到的联系人，没有找到则返回 None

        Raises:
            TypeError: 如果 phone 不是字符串
        """
        if not isinstance(phone, str):
            raise TypeError("phone must be a string")
        for contact in self.contacts:
            if contact.phone == phone:
                return contact
        return None

    def clear_contacts(self) -> None:
        """清空全部联系人"""
        self.contacts.clear()
        self.save_contacts()

    def get_contacts_count(self) -> int:
        """获取联系人数量

        Returns:
            int: 联系人数量
        """
        return len(self.contacts)

    # ------------------------------------------------------------------
    # 数据保护
    # ------------------------------------------------------------------
    def _backup_before_overwrite(self, file_path: str) -> Optional[str]:
        """覆盖写之前，若加载阶段跳过了无效记录，则先备份原文件

        当磁盘上存在无法解析的记录时，它们不会进入 self.contacts。
        一旦执行覆盖写，这些记录将永久消失。此时先把原文件完整复制一份
        到 `<file_path>.<时间戳>.bak`，让用户有机会人工找回。

        Args:
            file_path: 即将被覆盖的存储文件路径

        Returns:
            Optional[str]: 备份文件路径；无需备份时返回 None

        Raises:
            OSError: 备份失败。此时宁可不保存，也不能静默丢数据。
        """
        if not self._skipped_records or not os.path.exists(file_path):
            return None

        backup_path = f"{file_path}.{time.strftime('%Y%m%d-%H%M%S')}.bak"
        try:
            shutil.copy2(file_path, backup_path)
        except OSError:
            logger.exception(
                "检测到 %d 条无法解析的记录，但备份 %s 失败，已中止保存以避免数据丢失",
                len(self._skipped_records), file_path,
            )
            raise
        logger.error(
            "检测到 %d 条无法解析的记录，已备份原文件到 %s；"
            "本次保存不会包含这些记录，请确认是否需要人工恢复",
            len(self._skipped_records), backup_path,
        )
        return backup_path


class DataStorage(StorageBase):
    """联系人数据存储类（JSON 文件存储）

    使用 JSON 文件作为存储介质，写入采用「临时文件 + 原子替换」保证数据安全。

    属性：
        file_path: 数据文件路径
        contacts: 联系人列表
    """

    def __init__(self, file_path: str = "contacts.json") -> None:
        """初始化数据存储

        Args:
            file_path: 数据文件路径（可选，默认为 contacts.json）

        Raises:
            TypeError: 如果 file_path 不是字符串
        """
        if not isinstance(file_path, str):
            raise TypeError("file_path must be a string")

        super().__init__()
        self.file_path: str = file_path
        self.load_contacts()

    def load_contacts(self) -> None:
        """从 JSON 文件加载联系人数据

        无法解析的记录会被跳过，并记录到 _skipped_records 中，
        以便后续覆盖写之前触发自动备份。

        Raises:
            IsADirectoryError: 如果 file_path 是目录
            ValueError: 如果 JSON 格式无效或顶层不是列表
            PermissionError: 如果没有读取权限
            OSError: 如果发生其他操作系统错误
        """
        self.contacts.clear()
        self._skipped_records.clear()

        if not os.path.exists(self.file_path):
            logger.info("数据文件 %s 不存在，按空通讯录初始化", self.file_path)
            return

        if not os.path.isfile(self.file_path):
            logger.error("%s 是目录而非文件", self.file_path)
            raise IsADirectoryError(f"{self.file_path} is a directory, not a file")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("%s 不是合法的 JSON: %s", self.file_path, e)
            raise ValueError(f"Invalid JSON format: {e}") from e
        except PermissionError as e:
            logger.error("读取 %s 时权限不足: %s", self.file_path, e)
            raise PermissionError(f"Permission denied when reading {self.file_path}: {e}") from e
        except OSError as e:
            logger.error("读取 %s 时发生系统错误: %s", self.file_path, e)
            raise OSError(f"Failed to read file {self.file_path}: {e}") from e

        if not isinstance(data, list):
            logger.error("%s 的顶层结构不是列表", self.file_path)
            raise ValueError("Invalid data format: expected a list of contacts")

        for contact_data in data:
            try:
                self.contacts.append(Contact.from_dict(contact_data))
            except (TypeError, ValueError) as e:
                logger.warning("跳过无效的联系人记录: %s (原始数据: %r)", e, contact_data)
                self._skipped_records.append(contact_data)

        if self._skipped_records:
            logger.warning(
                "从 %s 加载 %d 条联系人，跳过 %d 条无效记录",
                self.file_path, len(self.contacts), len(self._skipped_records),
            )
        else:
            logger.info("成功从 %s 加载 %d 条联系人", self.file_path, len(self.contacts))

    def save_contacts(self) -> None:
        """将联系人列表保存到 JSON 文件（原子写入）

        Raises:
            PermissionError: 如果没有写入权限
            OSError: 如果发生其他操作系统错误
        """
        self._backup_before_overwrite(self.file_path)

        dir_path = os.path.dirname(self.file_path)
        if dir_path and not os.path.exists(dir_path):
            logger.info("创建联系人数据目录 %s", dir_path)
            os.makedirs(dir_path, exist_ok=True)

        data: List[Dict[str, Any]] = [contact.to_dict() for contact in self.contacts]
        temp_file_path = f"{self.file_path}.tmp"

        try:
            with open(temp_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # 原子替换：避免写入中途崩溃导致文件被截断
            os.replace(temp_file_path, self.file_path)
        except PermissionError as e:
            logger.error("写入 %s 时权限不足: %s", self.file_path, e)
            raise PermissionError(f"Permission denied when writing {self.file_path}: {e}") from e
        except OSError as e:
            logger.error("写入 %s 时发生系统错误: %s", self.file_path, e)
            raise OSError(f"Failed to write file {self.file_path}: {e}") from e

        # 原文件已被「包含全部有效记录」的新内容覆盖，此前的跳过记录已无对应文件，
        # 清空标记以免此后每次保存都重复生成一份备份
        self._skipped_records.clear()
        logger.info("成功保存 %d 条联系人到 %s", len(self.contacts), self.file_path)


class SQLiteStorage(StorageBase):
    """联系人数据存储类（SQLite 数据库存储）

    单条增删改直接作用于数据库，避免整表重写；批量保存使用事务。

    属性：
        db_path: 数据库文件路径
        contacts: 联系人列表
    """

    def __init__(self, db_path: str = "contacts.db") -> None:
        """初始化 SQLite 存储

        Args:
            db_path: 数据库文件路径（可选，默认为 contacts.db）

        Raises:
            TypeError: 如果 db_path 不是字符串
        """
        if not isinstance(db_path, str):
            raise TypeError("db_path must be a string")

        super().__init__()
        self.db_path: str = db_path
        self._init_db()
        self.load_contacts()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """打开数据库连接并保证退出时关闭

        Yields:
            sqlite3.Connection: 数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _to_row(contact: Contact) -> Tuple[str, str, str, str, int, str]:
        """把 Contact 转换为与 _CONTACT_COLUMNS 顺序一致的取值元组"""
        return (
            contact.name,
            contact.phone,
            contact.email,
            contact.remark,
            int(contact.is_frequent),
            contact.country,
        )

    @staticmethod
    def _row_to_contact(row: Tuple[Any, ...]) -> Contact:
        """把数据库行转换为 Contact 对象

        Args:
            row: (name, phone, email, remark, is_frequent, country)

        Returns:
            Contact: 联系人对象
        """
        contact = Contact(
            name=row[0],
            phone=row[1],
            email=row[2] or "",
            remark=row[3] or "",
            is_frequent=bool(row[4]),
        )
        # 数据库中保存的地区信息优先，避免每次重建时重新推断
        if row[5]:
            contact.country = row[5]
        return contact

    def _init_db(self) -> None:
        """初始化数据库，创建 contacts 表（表不存在时）"""
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE,
                    email TEXT,
                    remark TEXT,
                    is_frequent INTEGER DEFAULT 0,
                    country TEXT DEFAULT '未知'
                )
                """
            )
            conn.commit()

    def load_contacts(self) -> None:
        """从 SQLite 数据库加载联系人数据

        无法解析的行会被跳过并记录到 _skipped_records 中。
        """
        self.contacts.clear()
        self._skipped_records.clear()

        with self._connection() as conn:
            try:
                rows = conn.execute(
                    f"SELECT {', '.join(_CONTACT_COLUMNS)} FROM contacts"
                ).fetchall()
            except sqlite3.Error as e:
                logger.error("从数据库读取联系人失败: %s", e, exc_info=True)
                raise OSError(f"Failed to load contacts: {e}") from e

        for row in rows:
            try:
                self.contacts.append(self._row_to_contact(row))
            except (TypeError, ValueError) as e:
                logger.warning("跳过数据库中的无效联系人记录: %s", e)
                self._skipped_records.append(row)

        if self._skipped_records:
            logger.warning(
                "从 %s 加载 %d 条联系人，跳过 %d 条无效记录",
                self.db_path, len(self.contacts), len(self._skipped_records),
            )
        else:
            logger.info("成功从 %s 加载 %d 条联系人", self.db_path, len(self.contacts))

    def save_contacts(self) -> None:
        """将内存中的联系人列表整体写回数据库（事务 + 批量插入）

        Raises:
            Exception: 数据库写入失败时抛出，事务已回滚
        """
        self._backup_before_overwrite(self.db_path)

        with self._connection() as conn:
            try:
                conn.execute("DELETE FROM contacts")
                if self.contacts:
                    conn.executemany(_INSERT_SQL, [self._to_row(c) for c in self.contacts])
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error("保存联系人到数据库失败: %s", e, exc_info=True)
                raise OSError(f"Failed to save contacts: {e}") from e

        # 同 JSON 存储：全表已被重写，无需再为同一批跳过记录重复备份
        self._skipped_records.clear()
        logger.info("成功保存 %d 条联系人到 %s", len(self.contacts), self.db_path)

    def add_contact(self, contact: Contact) -> None:
        """添加联系人（单条插入，成功后同步内存）

        Args:
            contact: 要添加的联系人对象

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
            ValueError: 如果电话号码已存在
        """
        self._require_contact(contact)

        with self._connection() as conn:
            try:
                conn.execute(_INSERT_SQL, self._to_row(contact))
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                logger.warning("电话号码 %s 已存在，拒绝添加", contact.phone)
                raise ValueError(f"Contact with phone {contact.phone} already exists") from e
            except Exception as e:
                conn.rollback()
                logger.error("添加联系人到数据库失败: %s", e, exc_info=True)
                raise OSError(f"Failed to add contact: {e}") from e

        self.contacts.append(contact)
        logger.info("成功添加联系人 %s (%s)", contact.name, contact.phone)

    def add_contacts(self, contacts: Iterable[Contact]) -> None:
        """批量添加联系人（单事务 executemany，成功后同步内存）

        Args:
            contacts: 待添加的联系人集合

        Raises:
            TypeError: 如果其中混入非 Contact 对象
            ValueError: 如果批次内存在重复电话号码（整批回滚，不会部分写入）
        """
        batch = list(contacts)
        for contact in batch:
            self._require_contact(contact)
        if not batch:
            return

        with self._connection() as conn:
            try:
                conn.executemany(_INSERT_SQL, [self._to_row(c) for c in batch])
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                logger.warning("批量添加时遇到重复电话号码，整批回滚: %s", e)
                raise ValueError(f"批量添加失败，存在重复的电话号码: {e}") from e
            except Exception as e:
                conn.rollback()
                logger.error("批量添加联系人到数据库失败: %s", e, exc_info=True)
                raise OSError(f"Failed to add contacts: {e}") from e

        self.contacts.extend(batch)
        logger.info("成功批量添加 %d 条联系人到 %s", len(batch), self.db_path)

    def update_contact(self, index: int, contact: Contact) -> None:
        """更新联系人（按原电话号码定位记录，成功后同步内存）

        Args:
            index: 要更新的联系人索引
            contact: 新的联系人对象

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
            IndexError: 如果索引无效
            KeyError: 如果数据库中找不到原记录（内存与数据库不一致）
            ValueError: 如果新电话号码已被其他联系人占用
        """
        self._require_contact(contact)
        self._require_index(index, self.contacts)

        old_contact = self.contacts[index]

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    _UPDATE_SQL, (*self._to_row(contact), old_contact.phone)
                )
                # 影响行数为 0 说明内存与数据库已经不一致。
                # 此时若继续更新内存并返回成功，界面会显示"已保存"而数据实际丢失。
                if cursor.rowcount == 0:
                    raise KeyError(
                        f"数据库中不存在电话号码为 {old_contact.phone} 的记录，更新已中止"
                    )
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                logger.warning("电话号码 %s 已被占用，拒绝更新", contact.phone)
                raise ValueError(f"Phone {contact.phone} already exists") from e
            except Exception as e:
                conn.rollback()
                logger.error("更新数据库中的联系人失败: %s", e, exc_info=True)
                raise

        self.contacts[index] = contact
        logger.info("成功更新联系人 %s -> %s (%s)", old_contact.name, contact.name, contact.phone)

    def delete_contact(self, index: int) -> None:
        """删除联系人（按电话号码定位记录，成功后同步内存）

        Args:
            index: 要删除的联系人索引

        Raises:
            IndexError: 如果索引无效
            KeyError: 如果数据库中找不到对应记录
        """
        self._require_index(index, self.contacts)
        contact_to_delete = self.contacts[index]

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    "DELETE FROM contacts WHERE phone=?", (contact_to_delete.phone,)
                )
                if cursor.rowcount == 0:
                    raise KeyError(
                        f"数据库中不存在电话号码为 {contact_to_delete.phone} 的记录，删除已中止"
                    )
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error("从数据库删除联系人失败: %s", e, exc_info=True)
                raise

        del self.contacts[index]
        logger.info("成功删除联系人 %s (%s)", contact_to_delete.name, contact_to_delete.phone)
