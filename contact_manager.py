from typing import List, Dict, Any, Optional, Tuple
import logging
from contact import LETTER_TO_KEY
from contact import Contact

# 配置日志
logger = logging.getLogger(__name__)

class ContactManager:
    def __init__(self, storage):
        """初始化联系人管理器"""
        if storage is None:
            raise ValueError("storage cannot be None")
        if not hasattr(storage, 'contacts') or not hasattr(storage, 'save_contacts'):
            raise TypeError("storage must have contacts attribute and save_contacts method")
        
        self.storage = storage
        # 预计算并缓存搜索所需的小写名称，提高搜索效率
        self._search_cache: List[Dict[str, Any]] = []
        self._precompute_search_cache()

    def _precompute_search_cache(self) -> None:
        """预计算搜索缓存，提高搜索效率"""
        self._search_cache.clear()
        
        for contact in self.storage.contacts:
            name_lower = contact.name.lower()
            self._search_cache.append({
                'contact': contact,
                'name_lower': name_lower,
                'phone': contact.phone,
                'keypad_code': self.convert_to_keypad_code(name_lower)
            })
        
        logger.info(f"Search cache updated with {len(self._search_cache)} contacts")
    
    def convert_to_keypad_code(self, text: str) -> str:
        """将文本转换为九键键盘数字序列（公开方法）"""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        
        keypad_code = []
        for char in text:
            if char.isalpha():
                keypad_code.append(LETTER_TO_KEY.get(char, ''))
            # 非字母字符跳过
        return ''.join(keypad_code)

    def add_contact(self, contact: Contact) -> tuple[bool, str]:
        """添加联系人"""
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")
        
        # 检查电话号码是否已存在
        existing_contact = self.storage.get_contact_by_phone(contact.phone)
        if existing_contact:
            logger.warning(f"Attempt to add duplicate contact with phone: {contact.phone}")
            return False, "该电话号码已存在"
        
        try:
            self.storage.contacts.append(contact)
            self._precompute_search_cache()  # 更新缓存
            self.storage.save_contacts()
            logger.info(f"Contact added successfully: {contact.name} ({contact.phone})")
            return True, "添加成功"
        except Exception as e:
            logger.error(f"Failed to add contact: {e}", exc_info=True)
            return False, f"添加失败: {str(e)}"

    def update_contact(self, index: int, contact: Contact) -> tuple[bool, str]:
        """更新联系人"""
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")
        
        if not 0 <= index < len(self.storage.contacts):
            raise IndexError("Invalid contact index")
        
        # 检查电话号码是否被其他联系人使用
        existing_contact = self.storage.get_contact_by_phone(contact.phone)
        if existing_contact and self.storage.contacts.index(existing_contact) != index:
            logger.warning(f"Attempt to update contact with duplicate phone: {contact.phone}")
            return False, "该电话号码已被其他联系人使用"
        
        try:
            old_contact = self.storage.contacts[index]
            self.storage.contacts[index] = contact
            self._precompute_search_cache()  # 更新缓存
            self.storage.save_contacts()
            logger.info(f"Contact updated successfully: {old_contact.name} -> {contact.name} ({contact.phone})")
            return True, "更新成功"
        except Exception as e:
            logger.error(f"Failed to update contact at index {index}: {e}", exc_info=True)
            return False, f"更新失败: {str(e)}"

    def delete_contact(self, index: int) -> tuple[bool, str]:
        """删除联系人"""
        if not 0 <= index < len(self.storage.contacts):
            raise IndexError("Invalid contact index")
        
        try:
            deleted_contact = self.storage.contacts.pop(index)
            self._precompute_search_cache()  # 更新缓存
            self.storage.save_contacts()
            logger.info(f"Contact deleted successfully: {deleted_contact.name} ({deleted_contact.phone})")
            return True, "删除成功"
        except Exception as e:
            logger.error(f"Failed to delete contact at index {index}: {e}", exc_info=True)
            return False, f"删除失败: {str(e)}"

    def search_by_name(self, name: str) -> List[Contact]:
        """优化的姓名搜索，使用预计算的小写名称"""
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        
        if not name:
            return []
        
        name_lower = name.lower()
        results = [item['contact'] for item in self._search_cache if name_lower in item['name_lower']]
        logger.info(f"Name search '{name}' returned {len(results)} results")
        return results

    def search_by_phone(self, phone: str) -> List[Contact]:
        """优化的电话搜索"""
        if not isinstance(phone, str):
            raise TypeError("phone must be a string")
        
        if not phone:
            return []
        
        results = [item['contact'] for item in self._search_cache if phone in item['phone']]
        logger.info(f"Phone search '{phone}' returned {len(results)} results")
        return results
    
    def search_by_keypad(self, keypad_code: str) -> List[Contact]:
        """九键搜索：根据数字序列搜索联系人"""
        if not isinstance(keypad_code, str):
            raise TypeError("keypad_code must be a string")
        
        if not keypad_code:
            return []
        
        # 验证输入是否为纯数字
        if not keypad_code.isdigit():
            raise ValueError("keypad_code must contain only digits")
        
        results = [item['contact'] for item in self._search_cache if keypad_code in item['keypad_code']]
        logger.info(f"Keypad search '{keypad_code}' returned {len(results)} results")
        return results
    
    def search_by_email(self, email: str) -> List[Contact]:
        """根据邮箱搜索联系人"""
        if not isinstance(email, str):
            raise TypeError("email must be a string")
        
        if not email:
            return []
        
        email_lower = email.lower()
        results = [item['contact'] for item in self._search_cache if email_lower in item['contact'].email.lower()]
        logger.info(f"Email search '{email}' returned {len(results)} results")
        return results

    def get_all_contacts(self) -> List[Contact]:
        """获取所有联系人"""
        return self.storage.contacts.copy()

    def get_frequent_contacts(self) -> List[Contact]:
        """获取常用联系人"""
        return [item['contact'] for item in self._search_cache if item['contact'].is_frequent]
    
    def get_contact_by_index(self, index: int) -> Optional[Contact]:
        """根据索引获取联系人"""
        if not 0 <= index < len(self.storage.contacts):
            return None
        return self.storage.contacts[index]
    
    def get_contacts_count(self) -> int:
        """获取联系人总数"""
        return len(self.storage.contacts)
