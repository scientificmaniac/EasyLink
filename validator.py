import re
from typing import Optional, Tuple, Union

class Validator:
    # 邮箱验证正则表达式
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # 电话验证正则表达式，支持多种格式：+8613800138000, 13800138000, 010-12345678
    PHONE_PATTERN = re.compile(r'^\+?[0-9\s-]{7,15}$')
    
    # 姓名验证正则表达式，支持中文、英文、空格和部分特殊字符
    NAME_PATTERN = re.compile(r'^[\u4e00-\u9fa5a-zA-Z\s\."\'-]{1,50}$')

    @staticmethod
    def is_valid_email(email: Optional[str]) -> bool:
        """验证邮箱格式"""
        if not email:
            return True  # 邮箱可为空
        
        if not isinstance(email, str):
            return False
        
        return Validator.EMAIL_PATTERN.match(email) is not None
    
    @staticmethod
    def validate_email(email: Optional[str]) -> Tuple[bool, str]:
        """验证邮箱格式并返回详细的错误信息"""
        if not email:
            return True, ""
        
        if not isinstance(email, str):
            return False, "邮箱必须是字符串类型"
        
        if not Validator.EMAIL_PATTERN.match(email):
            return False, "邮箱格式不正确，应为 example@domain.com"
        
        return True, ""

    @staticmethod
    def is_valid_phone(phone: Optional[str]) -> bool:
        """验证手机号格式"""
        if not phone:
            return False  # 手机号不能为空
        
        if not isinstance(phone, str):
            return False
        
        return Validator.PHONE_PATTERN.match(phone) is not None
    
    @staticmethod
    def validate_phone(phone: Optional[str]) -> Tuple[bool, str]:
        """验证手机号格式并返回详细的错误信息"""
        if not phone:
            return False, "手机号不能为空"
        
        if not isinstance(phone, str):
            return False, "手机号必须是字符串类型"
        
        phone_clean = phone.replace(" ", "").replace("-", "")
        if len(phone_clean) < 7 or len(phone_clean) > 15:
            return False, "手机号长度必须在7-15位之间"
        
        if not Validator.PHONE_PATTERN.match(phone):
            return False, "手机号格式不正确，支持格式：+8613800138000, 13800138000, 010-12345678"
        
        return True, ""
    
    @staticmethod
    def is_valid_name(name: Optional[str]) -> bool:
        """验证姓名格式"""
        if not name:
            return False  # 姓名不能为空
        
        if not isinstance(name, str):
            return False
        
        # 姓名长度至少为1个字符，最多50个字符
        return 1 <= len(name.strip()) <= 50
    
    @staticmethod
    def validate_name(name: Optional[str]) -> Tuple[bool, str]:
        """验证姓名格式并返回详细的错误信息"""
        if not name:
            return False, "姓名不能为空"
        
        if not isinstance(name, str):
            return False, "姓名必须是字符串类型"
        
        name_stripped = name.strip()
        if not name_stripped:
            return False, "姓名不能为空"
        
        if len(name_stripped) < 1:
            return False, "姓名长度不能为0"
        
        if len(name_stripped) > 50:
            return False, "姓名长度不能超过50个字符"
        
        if not Validator.NAME_PATTERN.match(name_stripped):
            return False, "姓名只能包含中文、英文、空格、点、横杠和单引号"
        
        return True, ""
    
    @staticmethod
    def validate_remark(remark: Optional[str]) -> Tuple[bool, str]:
        """验证备注信息"""
        if not remark:
            return True, ""
        
        if not isinstance(remark, str):
            return False, "备注必须是字符串类型"
        
        if len(remark) > 200:
            return False, "备注长度不能超过200个字符"
        
        return True, ""
    
    @staticmethod
    def validate_contact_data(name: str, phone: str, email: str = "", remark: str = "") -> Tuple[bool, str]:
        """验证完整的联系人数据"""
        # 验证姓名
        valid, msg = Validator.validate_name(name)
        if not valid:
            return False, msg
        
        # 验证电话
        valid, msg = Validator.validate_phone(phone)
        if not valid:
            return False, msg
        
        # 验证邮箱
        valid, msg = Validator.validate_email(email)
        if not valid:
            return False, msg
        
        # 验证备注
        valid, msg = Validator.validate_remark(remark)
        if not valid:
            return False, msg
        
        return True, ""
