from typing import Dict, Set, List, Optional, Any
from validator import Validator

# 国家区号映射
COUNTRY_CODES: Dict[str, str] = {
    '+86': '中国',
    '+1': '美国/加拿大',
    '+44': '英国',
    '+49': '德国',
    '+33': '法国',
    '+39': '意大利',
    '+81': '日本',
    '+82': '韩国',
    '+61': '澳大利亚',
    '+91': '印度',
    '+7': '俄罗斯',
    '+65': '新加坡',
    '+47': '挪威',
    '+46': '瑞典',
    '+45': '丹麦',
    '+31': '荷兰',
    '+43': '奥地利',
    '+34': '西班牙',
    '+41': '瑞士',
    '+64': '新西兰',
    '+27': '南非',
    '+55': '巴西',
    '+52': '墨西哥',
    '+886': '中国台湾',
    '+852': '中国香港',
    '+853': '中国澳门'
}

# 九键键盘映射表
# 数字键对应字母，用于九键搜索
KEYPAD_MAPPING: Dict[str, Set[str]] = {
    '2': {'a', 'b', 'c'},
    '3': {'d', 'e', 'f'},
    '4': {'g', 'h', 'i'},
    '5': {'j', 'k', 'l'},
    '6': {'m', 'n', 'o'},
    '7': {'p', 'q', 'r', 's'},
    '8': {'t', 'u', 'v'},
    '9': {'w', 'x', 'y', 'z'}
}

# 反向映射：字母到数字
LETTER_TO_KEY: Dict[str, str] = {}
for key, letters in KEYPAD_MAPPING.items():
    for letter in letters:
        LETTER_TO_KEY[letter] = key

class Contact:
    def __init__(self, name: str, phone: str, email: str = "", remark: str = "", is_frequent: bool = False):
        # 验证输入数据
        valid, msg = Validator.validate_contact_data(name, phone, email, remark)
        if not valid:
            raise ValueError(f"Invalid contact data: {msg}")
        
        self.name: str = name.strip()
        self.phone: str = phone.strip()
        self.email: str = email.strip()
        self.remark: str = remark.strip()
        self.is_frequent: bool = is_frequent
        self.country: str = self.get_country_from_phone()

    def get_country_from_phone(self) -> str:
        """根据电话号码获取国家/地区"""
        if not self.phone:
            return '未知'
        
        for code, country in COUNTRY_CODES.items():
            if self.phone.startswith(code):
                return country
        # 检查是否是国内号码（无前缀）
        if self.phone.isdigit() and len(self.phone) == 11:
            return '中国'
        return '未知'
    
    def format_phone(self) -> str:
        """格式化电话号码显示，在区号和电话号中间添加空格"""
        if not self.phone:
            return ""
        
        # 检查是否有国际区号
        for code in COUNTRY_CODES.keys():
            if self.phone.startswith(code):
                # 有国际区号，在区号后添加空格
                return f"{code} {self.phone[len(code):]}"
        # 检查是否是国内11位手机号（无前缀）
        if self.phone.isdigit() and len(self.phone) == 11:
            # 国内手机号，添加+86前缀和空格
            return f"+86 {self.phone}"
        # 其他情况，保持原样
        return self.phone

    def to_dict(self) -> Dict[str, Any]:
        """将联系人转换为字典"""
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "remark": self.remark,
            "is_frequent": self.is_frequent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """从字典创建联系人对象"""
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary")
        
        required_fields = ["name", "phone"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
            if not isinstance(data[field], str):
                raise TypeError(f"Field '{field}' must be a string")
        
        # 处理可选字段
        email = data.get("email", "")
        if email and not isinstance(email, str):
            raise TypeError("email must be a string")
        
        remark = data.get("remark", "")
        if remark and not isinstance(remark, str):
            raise TypeError("remark must be a string")
        
        is_frequent = data.get("is_frequent", False)
        if not isinstance(is_frequent, bool):
            raise TypeError("is_frequent must be a boolean")
        
        contact = cls(
            data["name"],
            data["phone"],
            email,
            remark,
            is_frequent
        )
        contact.country = contact.get_country_from_phone()
        return contact
    
    def update(self, name: Optional[str] = None, phone: Optional[str] = None, 
               email: Optional[str] = None, remark: Optional[str] = None, 
               is_frequent: Optional[bool] = None) -> None:
        """更新联系人信息"""
        # 准备更新后的数据
        new_name = name.strip() if name is not None else self.name
        new_phone = phone.strip() if phone is not None else self.phone
        new_email = email.strip() if email is not None else self.email
        new_remark = remark.strip() if remark is not None else self.remark
        new_is_frequent = is_frequent if is_frequent is not None else self.is_frequent
        
        # 验证更新后的数据
        valid, msg = Validator.validate_contact_data(new_name, new_phone, new_email, new_remark)
        if not valid:
            raise ValueError(f"Invalid contact data: {msg}")
        
        # 更新属性
        self.name = new_name
        self.phone = new_phone
        self.email = new_email
        self.remark = new_remark
        self.is_frequent = new_is_frequent
        self.country = self.get_country_from_phone()  # 重新计算国家/地区
