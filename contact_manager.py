#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人管理器模块

该模块提供联系人管理的核心业务逻辑，包括联系人的添加、修改、删除、搜索等功能，
以及搜索所需索引的预计算与维护。

主要功能：
1. 联系人的增删改查
2. 多种搜索方式（姓名、电话、邮箱、九键搜索）
3. 搜索索引预计算，提高搜索效率
4. 批量导入，避免重复重建索引
5. 常用联系人管理

设计说明：
    self._search_cache 是 storage.contacts 的派生索引。任何会改动联系人集合
    的操作都必须调用 _rebuild_search_cache()，否则搜索与「常用联系人」页会
    返回过期结果。
"""

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pinyin
from contact import LETTER_TO_KEY, Contact
from storage import StorageBase

logger = logging.getLogger(__name__)


class ContactManager:
    """联系人管理器类

    该类负责联系人的核心业务逻辑，包括添加、修改、删除、搜索等功能。

    属性：
        storage: 数据存储对象
        _search_cache: 搜索索引，用于提高搜索效率
    """

    def __init__(self, storage: StorageBase) -> None:
        """初始化联系人管理器

        Args:
            storage: 数据存储对象

        Raises:
            ValueError: 如果 storage 为 None
            TypeError: 如果 storage 不是 StorageBase 的实例
        """
        if storage is None:
            raise ValueError("storage cannot be None")
        if not isinstance(storage, StorageBase):
            raise TypeError("storage must be an instance of StorageBase")

        self.storage: StorageBase = storage
        self._search_cache: List[Dict[str, Any]] = []
        self._rebuild_search_cache()

    # ------------------------------------------------------------------
    # 搜索索引
    # ------------------------------------------------------------------
    def _rebuild_search_cache(self) -> None:
        """重建搜索索引

        为每个联系人预计算小写姓名、邮箱与九键编码，避免每次搜索都重复计算。
        """
        self._search_cache = [
            {
                "contact": contact,
                "name_lower": contact.name.lower(),
                "phone": contact.phone,
                "email_lower": contact.email.lower(),
                # 拼音字母序列，用于支持「直接输入拼音搜中文姓名」
                "letters": pinyin.to_letters(contact.name),
                # 可能包含多个候选：姓氏存在异读时会同时保留两种读音的编码
                "keypad_codes": self._build_keypad_codes(contact.name),
            }
            for contact in self.storage.contacts
        ]
        logger.debug("搜索索引已更新，共 %d 条", len(self._search_cache))

    def refresh_cache(self) -> None:
        """对外暴露的索引刷新入口

        当调用方绕过本管理器直接改动 storage.contacts 后，应调用此方法恢复一致性。
        """
        self._rebuild_search_cache()

    @staticmethod
    def convert_to_keypad_code(text: str) -> str:
        """将文本转换为九键键盘数字序列

        拉丁字母按 a-z -> 2-9 直接映射；汉字先经 pinyin 转成拼音，再按拼音字母映射。
        未安装 pypinyin 时汉字会被跳过，英文姓名不受影响。

        Args:
            text: 要转换的文本

        Returns:
            str: 九键键盘数字序列

        Raises:
            TypeError: 如果 text 不是字符串
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        return "".join(LETTER_TO_KEY.get(char, "") for char in pinyin.to_letters(text))

    @staticmethod
    def _syllable_code(syllable: str) -> str:
        """把拼音音节转换成九键数字

        Args:
            syllable: 不带声调的拼音音节，如 "shan"

        Returns:
            str: 九键数字序列
        """
        return "".join(LETTER_TO_KEY.get(char, "") for char in syllable)

    def _build_keypad_codes(self, name: str) -> Tuple[str, ...]:
        """生成某个姓名对应的全部九键编码候选

        姓氏异读（如「单」作姓氏读 shàn，常用读音却是 dān）会让两种读音的编码
        完全不同。这里同时保留两套编码，用户按任一种读音输入都能检索到。

        Args:
            name: 联系人姓名

        Returns:
            Tuple[str, ...]: 去重后的编码候选；无法编码时返回空元组
        """
        primary = self.convert_to_keypad_code(name)

        if not name:
            return (primary,) if primary else ()

        alternate_reading = pinyin.surname_reading(name[0])
        if not alternate_reading:
            return (primary,)

        alternate = self._syllable_code(alternate_reading) + self.convert_to_keypad_code(name[1:])
        if alternate == primary:
            return (primary,)
        return (primary, alternate)

    # ------------------------------------------------------------------
    # 增删改
    # ------------------------------------------------------------------
    def add_contact(self, contact: Contact) -> Tuple[bool, str]:
        """添加单个联系人

        Args:
            contact: 要添加的联系人对象

        Returns:
            Tuple[bool, str]: (操作结果, 结果消息)

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
        """
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")

        if self.storage.get_contact_by_phone(contact.phone) is not None:
            logger.warning("尝试添加重复电话号码: %s", contact.phone)
            return False, "该电话号码已存在"

        try:
            self.storage.add_contact(contact)
        except ValueError as e:
            logger.warning("添加联系人失败: %s", e)
            return False, str(e)
        except Exception as e:
            logger.error("添加联系人失败: %s", e, exc_info=True)
            return False, f"添加失败: {e}"

        self._rebuild_search_cache()
        logger.info("联系人添加成功: %s (%s)", contact.name, contact.phone)
        return True, "添加成功"

    def add_contacts(self, contacts: Iterable[Contact]) -> Tuple[int, int]:
        """批量添加联系人（导入场景专用）

        与逐个调用 add_contact 相比，本方法在内存中去重、只落盘一次、
        只重建一次搜索索引，把导入 N 条数据的开销从 O(N²) 降为 O(N)。

        Args:
            contacts: 待添加的联系人集合

        Returns:
            Tuple[int, int]: (成功导入数量, 被跳过的数量)

        Raises:
            TypeError: 如果 contacts 中混入非 Contact 对象
        """
        existing_phones = {c.phone for c in self.storage.contacts}
        accepted: List[Contact] = []
        skipped = 0

        for contact in contacts:
            if not isinstance(contact, Contact):
                raise TypeError("contacts must contain Contact instances only")
            if contact.phone in existing_phones:
                logger.warning("导入时跳过重复电话号码: %s", contact.phone)
                skipped += 1
                continue
            existing_phones.add(contact.phone)
            accepted.append(contact)

        if not accepted:
            logger.info("批量导入: 没有新增联系人，跳过 %d 条", skipped)
            return 0, skipped

        self.storage.add_contacts(accepted)
        self._rebuild_search_cache()
        logger.info("批量导入完成: 新增 %d 条，跳过 %d 条", len(accepted), skipped)
        return len(accepted), skipped

    def update_contact(self, index: int, contact: Contact) -> Tuple[bool, str]:
        """更新指定索引处的联系人

        Args:
            index: 要更新的联系人索引
            contact: 新的联系人对象

        Returns:
            Tuple[bool, str]: (操作结果, 结果消息)

        Raises:
            TypeError: 如果 contact 不是 Contact 实例
            IndexError: 如果索引无效
        """
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")
        if not 0 <= index < len(self.storage.contacts):
            raise IndexError("Invalid contact index")

        # 电话号码是否被「别的」联系人占用（按对象身份比较，意图明确）
        existing = self.storage.get_contact_by_phone(contact.phone)
        if existing is not None and existing is not self.storage.contacts[index]:
            logger.warning("尝试把电话号码改为已被占用的 %s", contact.phone)
            return False, "该电话号码已被其他联系人使用"

        old_contact = self.storage.contacts[index]
        try:
            self.storage.update_contact(index, contact)
        except ValueError as e:
            logger.warning("更新联系人失败: %s", e)
            return False, str(e)
        except Exception as e:
            logger.error("更新索引 %d 处的联系人失败: %s", index, e, exc_info=True)
            return False, f"更新失败: {e}"

        self._rebuild_search_cache()
        logger.info("联系人更新成功: %s -> %s (%s)", old_contact.name, contact.name, contact.phone)
        return True, "更新成功"

    def delete_contact(self, index: int) -> Tuple[bool, str]:
        """删除指定索引处的联系人

        Args:
            index: 要删除的联系人索引

        Returns:
            Tuple[bool, str]: (操作结果, 结果消息)

        Raises:
            IndexError: 如果索引无效
        """
        if not 0 <= index < len(self.storage.contacts):
            raise IndexError("Invalid contact index")

        deleted_contact = self.storage.contacts[index]
        try:
            self.storage.delete_contact(index)
        except Exception as e:
            logger.error("删除索引 %d 处的联系人失败: %s", index, e, exc_info=True)
            return False, f"删除失败: {e}"

        self._rebuild_search_cache()
        logger.info("联系人删除成功: %s (%s)", deleted_contact.name, deleted_contact.phone)
        return True, "删除成功"

    def set_frequent(self, index: int, is_frequent: bool) -> Tuple[bool, str]:
        """设置（而非就地翻转）指定联系人的常用标记

        就地修改 contact.is_frequent 后若保存失败，内存对象会停留在被改过的状态，
        界面与数据库随即不一致。因此这里在副本上修改，成功后再替换内存对象。

        Args:
            index: 联系人索引
            is_frequent: 目标常用标记

        Returns:
            Tuple[bool, str]: (操作结果, 结果消息)
        """
        if not 0 <= index < len(self.storage.contacts):
            raise IndexError("Invalid contact index")

        old_contact = self.storage.contacts[index]
        if old_contact.is_frequent == is_frequent:
            return True, "无需修改"

        updated = Contact(
            old_contact.name,
            old_contact.phone,
            old_contact.email,
            old_contact.remark,
            is_frequent,
        )
        return self.update_contact(index, updated)

    # ------------------------------------------------------------------
    # 查询与搜索
    # ------------------------------------------------------------------
    def search_by_name(self, name: str) -> List[Contact]:
        """按姓名模糊搜索（不区分大小写的子串匹配）

        Args:
            name: 要搜索的姓名片段

        Returns:
            List[Contact]: 搜索结果列表

        Raises:
            TypeError: 如果 name 不是字符串
        """
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        if not name:
            return []

        name_lower = name.lower()
        results = [item["contact"] for item in self._search_cache if name_lower in item["name_lower"]]
        logger.debug("姓名搜索 '%s' 命中 %d 条", name, len(results))
        return results

    def search_by_phone(self, phone: str) -> List[Contact]:
        """按电话号码模糊搜索（子串匹配）

        注意：这是子串匹配而非精确匹配，输入 "138" 会命中所有含 138 的号码。

        Args:
            phone: 要搜索的电话号码片段

        Returns:
            List[Contact]: 搜索结果列表

        Raises:
            TypeError: 如果 phone 不是字符串
        """
        if not isinstance(phone, str):
            raise TypeError("phone must be a string")
        if not phone:
            return []

        results = [item["contact"] for item in self._search_cache if phone in item["phone"]]
        logger.debug("电话搜索 '%s' 命中 %d 条", phone, len(results))
        return results

    def search_by_email(self, email: str) -> List[Contact]:
        """按邮箱模糊搜索（不区分大小写的子串匹配）

        Args:
            email: 要搜索的邮箱片段

        Returns:
            List[Contact]: 搜索结果列表

        Raises:
            TypeError: 如果 email 不是字符串
        """
        if not isinstance(email, str):
            raise TypeError("email must be a string")
        if not email:
            return []

        email_lower = email.lower()
        results = [item["contact"] for item in self._search_cache if email_lower in item["email_lower"]]
        logger.debug("邮箱搜索 '%s' 命中 %d 条", email, len(results))
        return results

    def search_by_keypad(self, keypad_code: str) -> List[Contact]:
        """九键搜索：按数字序列前缀匹配联系人姓名的九键编码

        采用前缀匹配而非任意位置的子串匹配：九键输入是逐位收窄的过程，
        若用子串匹配，输入单个 "9" 会命中编码中段含 9 的全部联系人。

        中文姓名按拼音编码参与匹配（如「张明」-> zhangming -> 942646464），
        这需要安装 pypinyin；未安装时只有拉丁字母姓名能命中。

        Args:
            keypad_code: 九键键盘数字序列

        Returns:
            List[Contact]: 搜索结果列表

        Raises:
            TypeError: 如果 keypad_code 不是字符串
            ValueError: 如果 keypad_code 不是纯数字
        """
        if not isinstance(keypad_code, str):
            raise TypeError("keypad_code must be a string")
        if not keypad_code:
            return []
        if not keypad_code.isdigit():
            raise ValueError("keypad_code must contain only digits")

        results = [
            item["contact"]
            for item in self._search_cache
            if any(code.startswith(keypad_code) for code in item["keypad_codes"])
        ]
        logger.debug("九键搜索 '%s' 命中 %d 条", keypad_code, len(results))
        return results

    def search_all(self, keyword: str) -> List[Contact]:
        """统一搜索：一次遍历同时匹配姓名、拼音、电话、邮箱和九键编码

        支持的输入形式：
        - 中文或英文姓名的子串，如「张」「emma」
        - 姓名对应的拼音子串，如「zhang」「zhangming」
        - 电话号码子串
        - 邮箱子串
        - 九键数字序列（前缀匹配），如「942646464」

        Args:
            keyword: 搜索关键词

        Returns:
            List[Contact]: 去重后的搜索结果列表

        Raises:
            TypeError: 如果 keyword 不是字符串
        """
        if not isinstance(keyword, str):
            raise TypeError("keyword must be a string")
        if not keyword:
            return []

        keyword_lower = keyword.lower()
        is_digits = keyword.isdigit()

        results: List[Contact] = []
        for item in self._search_cache:
            if (
                keyword_lower in item["name_lower"]
                or keyword in item["phone"]
                or (item["email_lower"] and keyword_lower in item["email_lower"])
                or (item["letters"] and keyword_lower in item["letters"])
                or (is_digits and any(code.startswith(keyword) for code in item["keypad_codes"]))
            ):
                results.append(item["contact"])
        return results

    def get_all_contacts(self) -> List[Contact]:
        """获取所有联系人

        Returns:
            List[Contact]: 联系人列表的浅拷贝
        """
        return self.storage.contacts.copy()

    def get_frequent_contacts(self) -> List[Contact]:
        """获取常用联系人

        Returns:
            List[Contact]: 常用联系人列表
        """
        return [item["contact"] for item in self._search_cache if item["contact"].is_frequent]

    def get_contact_by_index(self, index: int) -> Optional[Contact]:
        """根据索引获取联系人

        Args:
            index: 联系人索引

        Returns:
            Optional[Contact]: 联系人对象，索引无效时返回 None
        """
        if not 0 <= index < len(self.storage.contacts):
            return None
        return self.storage.contacts[index]

    def get_contacts_count(self) -> int:
        """获取联系人总数

        Returns:
            int: 联系人总数
        """
        return len(self.storage.contacts)
