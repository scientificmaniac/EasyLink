import json
import os
import logging
from typing import List, Dict, Any, Optional
from contact import Contact

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, file_path: str = "contacts.json"):
        """初始化数据存储"""
        if not isinstance(file_path, str):
            raise TypeError("file_path must be a string")
        
        self.file_path: str = file_path
        self.contacts: List[Contact] = []
        self.load_contacts()

    def load_contacts(self) -> None:
        """加载联系人数据"""
        self.contacts.clear()
        
        if not os.path.exists(self.file_path):
            logger.info(f"File {self.file_path} does not exist, initializing empty contacts list")
            return
        
        if not os.path.isfile(self.file_path):
            logger.error(f"{self.file_path} is a directory, not a file")
            raise IsADirectoryError(f"{self.file_path} is a directory, not a file")
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                logger.error(f"Invalid data format in {self.file_path}: expected a list of contacts")
                raise ValueError("Invalid data format: expected a list of contacts")
            
            invalid_contacts_count = 0
            for contact_data in data:
                try:
                    contact = Contact.from_dict(contact_data)
                    self.contacts.append(contact)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Skipping invalid contact data: {e}")
                    invalid_contacts_count += 1
                    continue
            
            if invalid_contacts_count > 0:
                logger.warning(f"Loaded {len(self.contacts)} contacts, skipped {invalid_contacts_count} invalid entries")
            else:
                logger.info(f"Successfully loaded {len(self.contacts)} contacts from {self.file_path}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in {self.file_path}: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        except PermissionError as e:
            logger.error(f"Permission denied when reading {self.file_path}: {e}")
            raise PermissionError(f"Permission denied when reading {self.file_path}: {e}")
        except OSError as e:
            logger.error(f"OS error when reading {self.file_path}: {e}")
            raise OSError(f"Failed to read file {self.file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error when loading contacts: {e}", exc_info=True)
            raise Exception(f"Failed to load contacts: {e}")

    def save_contacts(self) -> None:
        """保存联系人数据"""
        try:
            # 确保目录存在
            dir_path = os.path.dirname(self.file_path)
            if dir_path and not os.path.exists(dir_path):
                logger.info(f"Creating directory {dir_path} for contacts storage")
                os.makedirs(dir_path, exist_ok=True)
            
            # 准备数据
            data: List[Dict[str, Any]] = [contact.to_dict() for contact in self.contacts]
            
            # 先写入临时文件，再重命名，确保原子操作
            temp_file_path = f"{self.file_path}.tmp"
            with open(temp_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # 替换原文件
            os.replace(temp_file_path, self.file_path)
            logger.info(f"Successfully saved {len(self.contacts)} contacts to {self.file_path}")
            
        except PermissionError as e:
            logger.error(f"Permission denied when writing {self.file_path}: {e}")
            raise PermissionError(f"Permission denied when writing {self.file_path}: {e}")
        except OSError as e:
            logger.error(f"OS error when writing {self.file_path}: {e}")
            raise OSError(f"Failed to write file {self.file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error when saving contacts: {e}", exc_info=True)
            raise Exception(f"Failed to save contacts: {e}")
    
    def add_contact(self, contact: Contact) -> None:
        """添加联系人"""
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")
        self.contacts.append(contact)
        self.save_contacts()
    
    def update_contact(self, index: int, contact: Contact) -> None:
        """更新联系人"""
        if not isinstance(contact, Contact):
            raise TypeError("contact must be an instance of Contact")
        if not 0 <= index < len(self.contacts):
            raise IndexError("Invalid contact index")
        self.contacts[index] = contact
        self.save_contacts()
    
    def delete_contact(self, index: int) -> None:
        """删除联系人"""
        if not 0 <= index < len(self.contacts):
            raise IndexError("Invalid contact index")
        del self.contacts[index]
        self.save_contacts()
    
    def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """根据电话号码查找联系人"""
        if not isinstance(phone, str):
            raise TypeError("phone must be a string")
        for contact in self.contacts:
            if contact.phone == phone:
                return contact
        return None
    
    def clear_contacts(self) -> None:
        """清空所有联系人"""
        self.contacts.clear()
        self.save_contacts()
    
    def get_contacts_count(self) -> int:
        """获取联系人数量"""
        return len(self.contacts)
