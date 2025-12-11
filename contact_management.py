import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from openpyxl import Workbook

# 国家区号映射
COUNTRY_CODES = {
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
KEYPAD_MAPPING = {
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
LETTER_TO_KEY = {}
for key, letters in KEYPAD_MAPPING.items():
    for letter in letters:
        LETTER_TO_KEY[letter] = key

class Contact:
    def __init__(self, name, phone, email="", remark="", is_frequent=False):
        self.name = name
        self.phone = phone
        self.email = email
        self.remark = remark
        self.is_frequent = is_frequent
        self.country = self.get_country_from_phone()

    def get_country_from_phone(self):
        """根据电话号码获取国家/地区"""
        for code, country in COUNTRY_CODES.items():
            if self.phone.startswith(code):
                return country
        # 检查是否是国内号码（无前缀）
        if self.phone.isdigit() and len(self.phone) == 11:
            return '中国'
        return '未知'

    def to_dict(self):
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "remark": self.remark,
            "is_frequent": self.is_frequent
        }

    @classmethod
    def from_dict(cls, data):
        contact = cls(
            data["name"],
            data["phone"],
            data.get("email", ""),
            data.get("remark", ""),
            data.get("is_frequent", False)
        )
        contact.country = contact.get_country_from_phone()
        return contact

class DataStorage:
    def __init__(self, file_path="contacts.json"):
        self.file_path = file_path
        self.contacts = []
        self.load_contacts()

    def load_contacts(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.contacts = [Contact.from_dict(contact) for contact in data]
            except Exception as e:
                messagebox.showerror("错误", f"加载联系人失败: {str(e)}")
        else:
            self.contacts = []

    def save_contacts(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                data = [contact.to_dict() for contact in self.contacts]
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("错误", f"保存联系人失败: {str(e)}")

class ContactManager:
    def __init__(self, storage):
        self.storage = storage
        # 预计算并缓存搜索所需的小写名称，提高搜索效率
        self._precompute_search_cache()

    def _precompute_search_cache(self):
        """预计算搜索缓存，提高搜索效率"""
        self._search_cache = []
        for contact in self.storage.contacts:
            name_lower = contact.name.lower()
            self._search_cache.append({
                'contact': contact,
                'name_lower': name_lower,
                'phone': contact.phone,
                'keypad_code': self.convert_to_keypad_code(name_lower)
            })
    
    def convert_to_keypad_code(self, text):
        """将文本转换为九键键盘数字序列（公开方法）"""
        keypad_code = []
        for char in text:
            if char.isalpha():
                keypad_code.append(LETTER_TO_KEY.get(char, ''))
            # 非字母字符跳过
        return ''.join(keypad_code)

    def add_contact(self, contact):
        for c in self.storage.contacts:
            if c.phone == contact.phone:
                messagebox.showerror("错误", "该电话号码已存在")
                return False
        self.storage.contacts.append(contact)
        self._precompute_search_cache()  # 更新缓存
        self.storage.save_contacts()
        return True

    def update_contact(self, index, contact):
        self.storage.contacts[index] = contact
        self._precompute_search_cache()  # 更新缓存
        self.storage.save_contacts()

    def delete_contact(self, index):
        del self.storage.contacts[index]
        self._precompute_search_cache()  # 更新缓存
        self.storage.save_contacts()

    def search_by_name(self, name):
        """优化的姓名搜索，使用预计算的小写名称"""
        name_lower = name.lower()
        return [item['contact'] for item in self._search_cache if name_lower in item['name_lower']]

    def search_by_phone(self, phone):
        """优化的电话搜索"""
        return [item['contact'] for item in self._search_cache if phone in item['phone']]
    
    def search_by_keypad(self, keypad_code):
        """九键搜索：根据数字序列搜索联系人"""
        return [item['contact'] for item in self._search_cache if keypad_code in item['keypad_code']]

    def get_all_contacts(self):
        return self.storage.contacts

    def get_frequent_contacts(self):
        return [item['contact'] for item in self._search_cache if item['contact'].is_frequent]

class Validator:
    @staticmethod
    def is_valid_email(email):
        """验证邮箱格式"""
        import re
        if not email:
            return True  # 邮箱可为空
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def is_valid_phone(phone):
        """验证手机号格式"""
        import re
        if not phone:
            return False  # 手机号不能为空
        
        # 支持多种格式：+8613800138000, 13800138000, 010-12345678
        pattern = r'^\+?[0-9\s-]{7,15}$'
        return re.match(pattern, phone) is not None

class ExcelExporter:
    @staticmethod
    def export_to_excel(contacts, file_path="contacts.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "联系人列表"

        headers = ["姓名", "电话", "邮箱", "国家/地区", "备注", "常用联系人"]
        ws.append(headers)

        for contact in contacts:
            ws.append([
                contact.name,
                contact.phone,
                contact.email,
                contact.country,
                contact.remark,
                "是" if contact.is_frequent else "否"
            ])

        try:
            wb.save(file_path)
            messagebox.showinfo("成功", f"联系人已导出到 {file_path}")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            return False

class TXTExporter:
    @staticmethod
    def export_to_txt(contacts, file_path="contacts.txt"):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("个人通讯录\n")
                f.write("=" * 50 + "\n\n")
                
                for i, contact in enumerate(contacts, 1):
                    f.write(f"联系人 {i}:\n")
                    f.write(f"姓名: {contact.name}\n")
                    f.write(f"电话: {contact.phone}\n")
                    f.write(f"邮箱: {contact.email}\n")
                    f.write(f"国家/地区: {contact.country}\n")
                    f.write(f"备注: {contact.remark}\n")
                    f.write(f"常用联系人: {'是' if contact.is_frequent else '否'}\n")
                    f.write("-" * 50 + "\n\n")
            
            messagebox.showinfo("成功", f"联系人已导出到 {file_path}")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            return False

class MDExporter:
    @staticmethod
    def export_to_md(contacts, file_path="contacts.md"):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("# 个人通讯录\n\n")
                f.write("| 姓名 | 电话 | 邮箱 | 国家/地区 | 备注 | 常用联系人 |\n")
                f.write("|------|------|------|------------|------|------------|\n")
                
                for contact in contacts:
                    f.write(f"| {contact.name} | {contact.phone} | {contact.email} | {contact.country} | {contact.remark} | {'是' if contact.is_frequent else '否'} |\n")
            
            messagebox.showinfo("成功", f"联系人已导出到 {file_path}")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            return False

class ContactGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("个人通讯录管理系统")
        
        # 设置窗口初始大小为屏幕的70%，实现自适应
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = int(screen_width * 0.7)
        window_height = int(screen_height * 0.7)
        self.root.geometry(f"{window_width}x{window_height}")
        
        # 设置最小大小
        self.root.minsize(700, 500)
        self.root.resizable(True, True)

        # 设置样式
        self.style = ttk.Style()
        self.setup_style()

        self.storage = DataStorage()
        self.manager = ContactManager(self.storage)

        self.current_tab = "全部联系人"
        self.current_contacts = self.manager.get_all_contacts()

        self.setup_ui()
        self.refresh_contact_list()

    def setup_style(self):
        # 设置主题
        self.style.theme_use("clam")
        
        # 主窗口背景
        self.root.configure(bg="#f5f5f5")
        
        # 标签样式
        self.style.configure("TLabel", background="#f5f5f5", foreground="#333333", font=("Microsoft YaHei", 10))
        
        # 按钮样式
        self.style.configure("TButton", 
                           background="#4a90e2", 
                           foreground="white", 
                           font=("Microsoft YaHei", 10),
                           padding=6)
        self.style.map("TButton", 
                      background=[("active", "#357abd"), ("disabled", "#d9d9d9")],
                      foreground=[("disabled", "#999999")])
        
        # 输入框样式
        self.style.configure("TEntry", 
                           fieldbackground="white", 
                           foreground="#333333",
                           padding=5,
                           font=("Microsoft YaHei", 10))
        
        # 列表框样式
        self.style.configure("Listbox", 
                           background="white", 
                           foreground="#333333",
                           font=("Microsoft YaHei", 10))
        
        # 标签页样式
        self.style.configure("TNotebook", background="#f5f5f5")
        self.style.configure("TNotebook.Tab", 
                           background="#e0e0e0", 
                           foreground="#333333",
                           padding=[15, 5],
                           font=("Microsoft YaHei", 10))
        self.style.map("TNotebook.Tab", 
                      background=[("selected", "white")],
                      foreground=[("selected", "#4a90e2")])
        
        # 详情框架样式
        self.style.configure("TLabelframe", 
                           background="#f5f5f5",
                           foreground="#333333",
                           font=("Microsoft YaHei", 11, "bold"))
        self.style.configure("TLabelframe.Label", 
                           background="#f5f5f5",
                           foreground="#333333",
                           font=("Microsoft YaHei", 11, "bold"))

    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="个人通讯录管理系统", 
                               font=("Microsoft YaHei", 16, "bold"), 
                               foreground="#4a90e2")
        title_label.pack(pady=(0, 15))

        # 搜索和功能按钮区
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # 搜索框架
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(search_frame, text="搜索:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        # 添加回车事件绑定
        search_entry.bind("<Return>", self.unified_search)
        
        search_buttons_frame = ttk.Frame(search_frame)
        search_buttons_frame.pack(side=tk.LEFT)
        ttk.Button(search_buttons_frame, text="搜索", command=self.unified_search, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_buttons_frame, text="重置", command=self.reset_search, width=8).pack(side=tk.LEFT, padx=2)

        # 操作按钮框架
        action_buttons_frame = ttk.Frame(top_frame)
        action_buttons_frame.pack(side=tk.RIGHT)
        ttk.Button(action_buttons_frame, text="添加", command=self.add_contact, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons_frame, text="修改", command=self.edit_contact, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons_frame, text="删除", command=self.delete_contact, width=10).pack(side=tk.LEFT, padx=5)

        # 中间内容区
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 左侧联系人列表区
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 创建标签页
        tab_control = ttk.Notebook(left_frame)
        self.all_contacts_tab = ttk.Frame(tab_control)
        self.frequent_contacts_tab = ttk.Frame(tab_control)
        self.keypad_search_tab = ttk.Frame(tab_control)  # 新增九键搜索标签页

        tab_control.add(self.all_contacts_tab, text="全部联系人")
        tab_control.add(self.frequent_contacts_tab, text="常用联系人")
        tab_control.add(self.keypad_search_tab, text="九键搜索")  # 添加九键搜索标签
        tab_control.pack(fill=tk.BOTH, expand=True)

        tab_control.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 联系人列表框 - 全部联系人
        list_frame1 = ttk.Frame(self.all_contacts_tab)
        list_frame1.pack(fill=tk.BOTH, expand=True)

        self.contact_list = tk.Listbox(list_frame1, height=20, bd=1, relief="solid", highlightthickness=1, highlightbackground="#e0e0e0")
        self.contact_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(list_frame1, orient=tk.VERTICAL, command=self.contact_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.contact_list.config(yscrollcommand=scrollbar.set)

        # 绑定列表框事件
        self.contact_list.bind("<<ListboxSelect>>", self.on_contact_select)
        self.contact_list.bind("<Double-1>", self.edit_contact)

        # 常用联系人列表框（复用同一个列表框，通过标签页切换）
        list_frame2 = ttk.Frame(self.frequent_contacts_tab)
        list_frame2.pack(fill=tk.BOTH, expand=True)
        
        # 为常用联系人标签页添加相同的列表框
        self.frequent_list = tk.Listbox(list_frame2, height=20, bd=1, relief="solid", highlightthickness=1, highlightbackground="#e0e0e0")
        self.frequent_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar2 = ttk.Scrollbar(list_frame2, orient=tk.VERTICAL, command=self.frequent_list.yview)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.frequent_list.config(yscrollcommand=scrollbar2.set)
        
        # 绑定事件
        self.frequent_list.bind("<<ListboxSelect>>", self.on_contact_select)
        self.frequent_list.bind("<Double-1>", self.edit_contact)
        
        # 右侧详情和导出区
        right_frame = ttk.Frame(content_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        
        # 详情框架
        detail_frame = ttk.LabelFrame(right_frame, text="联系人详情", padding="10 10 10 10")
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # 姓名
        name_frame = ttk.Frame(detail_frame)
        name_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(name_frame, text="姓名:", width=8, anchor="w").pack(side=tk.LEFT, padx=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, state="disabled", foreground="#666666")
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 电话
        phone_frame = ttk.Frame(detail_frame)
        phone_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(phone_frame, text="电话:", width=8, anchor="w").pack(side=tk.LEFT, padx=5)
        self.phone_var = tk.StringVar()
        phone_entry = ttk.Entry(phone_frame, textvariable=self.phone_var, state="disabled", foreground="#666666")
        phone_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 国家/地区
        country_frame = ttk.Frame(detail_frame)
        country_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(country_frame, text="国家:", width=8, anchor="w").pack(side=tk.LEFT, padx=5)
        self.country_var = tk.StringVar(value="")
        country_entry = ttk.Entry(country_frame, textvariable=self.country_var, state="disabled", foreground="#666666")
        country_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 邮箱
        email_frame = ttk.Frame(detail_frame)
        email_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(email_frame, text="邮箱:", width=8, anchor="w").pack(side=tk.LEFT, padx=5)
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(email_frame, textvariable=self.email_var, state="disabled", foreground="#666666")
        email_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 备注
        remark_frame = ttk.Frame(detail_frame)
        remark_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(remark_frame, text="备注:", width=8, anchor="w").pack(side=tk.LEFT, padx=5)
        self.remark_var = tk.StringVar()
        remark_entry = ttk.Entry(remark_frame, textvariable=self.remark_var, state="disabled", foreground="#666666")
        remark_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 常用联系人标记
        frequent_frame = ttk.Frame(detail_frame)
        frequent_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(frequent_frame, text="标记为常用", command=self.toggle_frequent).pack(fill=tk.X, padx=5)

        # 导出框架
        export_frame = ttk.LabelFrame(right_frame, text="数据导出", padding="10 10 10 10")
        export_frame.pack(fill=tk.X)

        export_buttons_frame = ttk.Frame(export_frame)
        export_buttons_frame.pack(fill=tk.X, pady=5)
        ttk.Button(export_buttons_frame, text="导出Excel", command=self.export_excel, width=15).pack(fill=tk.X, pady=3)
        ttk.Button(export_buttons_frame, text="导出TXT", command=self.export_txt, width=15).pack(fill=tk.X, pady=3)
        ttk.Button(export_buttons_frame, text="导出Markdown", command=self.export_md, width=15).pack(fill=tk.X, pady=3)
        
        # 九键搜索页面
        self.setup_keypad_search_page()
    
    def setup_keypad_search_page(self):
        """设置九键搜索页面"""
        # 主框架
        keypad_frame = ttk.Frame(self.keypad_search_tab, padding="20 20 20 20")
        keypad_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(keypad_frame, text="九键拨号搜索", 
                               font=("Microsoft YaHei", 14, "bold"), 
                               foreground="#4a90e2")
        title_label.pack(pady=(0, 20))
        
        # 输入显示框
        input_frame = ttk.Frame(keypad_frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 输入框容器
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.X, padx=50, pady=10)
        
        self.keypad_input_var = tk.StringVar()
        input_entry = ttk.Entry(input_container, textvariable=self.keypad_input_var, 
                               font=("Microsoft YaHei", 16), justify="center",
                               foreground="#333333", state="readonly")
        # 通过padding增加高度
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipadx=10, ipady=15)
        
        # 添加清除按钮在输入框右侧
        clear_btn = ttk.Button(input_container, text="×", 
                              command=self.keypad_clear, 
                              style="KeypadClear.TButton")
        clear_btn.pack(side=tk.RIGHT, fill=tk.Y, padx=5, ipadx=15)
        
        # 搜索结果提示
        self.keypad_result_var = tk.StringVar(value="请使用下方拨号键盘输入数字")
        result_label = ttk.Label(keypad_frame, textvariable=self.keypad_result_var, 
                                font=("Microsoft YaHei", 10), 
                                foreground="#666666")
        result_label.pack(pady=(0, 20))
        
        # 拨号键盘 - 使用固定高度，确保在不同分辨率下都能正常显示
        keypad_container = ttk.Frame(keypad_frame)
        keypad_container.pack(fill=tk.X, padx=50, pady=10)
        
        # 键盘按钮布局
        keypad_buttons = [
            ('1', ''), ('2', 'ABC'), ('3', 'DEF'),
            ('4', 'GHI'), ('5', 'JKL'), ('6', 'MNO'),
            ('7', 'PQRS'), ('8', 'TUV'), ('9', 'WXYZ'),
            ('*', ''), ('0', '+'), ('#', '')
        ]
        
        # 创建键盘网格 - 设置固定高度
        keypad_grid = ttk.Frame(keypad_container)
        keypad_grid.pack(fill=tk.X, expand=False)
        
        # 创建按钮
        for i, (num, letters) in enumerate(keypad_buttons):
            row = i // 3
            col = i % 3
            
            # 配置网格权重 - 确保每行每列大小一致
            keypad_grid.grid_rowconfigure(row, weight=1, minsize=60)  # 设置最小高度
            keypad_grid.grid_columnconfigure(col, weight=1, minsize=80)  # 设置最小宽度
            
            # 使用ttk.Button的compound属性来显示字母，而不是单独的标签
            # 组合文本：第一行是数字（大字体），第二行是字母（小字体）
            if letters:
                # 对于有字母的按钮，使用多行文本
                button_text = f"{num}\n{letters}"
                btn = ttk.Button(keypad_grid, 
                               text=button_text, 
                               command=lambda n=num: self.keypad_button_click(n),
                               style="Keypad.TButton",
                               compound="top")
            else:
                # 对于没有字母的按钮，只显示数字
                btn = ttk.Button(keypad_grid, 
                               text=num, 
                               command=lambda n=num: self.keypad_button_click(n),
                               style="Keypad.TButton")
            
            # 使用grid布局直接放置按钮，不需要额外容器
            btn.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        
        # 操作按钮
        action_frame = ttk.Frame(keypad_frame)
        action_frame.pack(fill=tk.X, pady=20, padx=50)
        
        ttk.Button(action_frame, text="清除", command=self.keypad_clear, width=10).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(action_frame, text="删除", command=self.keypad_backspace, width=10).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(action_frame, text="搜索", command=self.keypad_search, width=10).pack(side=tk.LEFT, padx=5, expand=True)
        
        # 搜索结果列表
        result_frame = ttk.LabelFrame(keypad_frame, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=20, padx=50)
        
        self.keypad_result_list = tk.Listbox(result_frame, height=10, bd=1, 
                                            relief="solid", highlightthickness=1, 
                                            highlightbackground="#e0e0e0")
        self.keypad_result_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, 
                                 command=self.keypad_result_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.keypad_result_list.config(yscrollcommand=scrollbar.set)
        
        # 绑定列表框事件
        self.keypad_result_list.bind("<<ListboxSelect>>", self.on_keypad_result_select)
        self.keypad_result_list.bind("<Double-1>", self.on_keypad_result_double_click)
        
        # 配置keypad按钮样式 - 确保多行文本正确显示，适应不同分辨率
        self.style.configure("Keypad.TButton", 
                           font=("Microsoft YaHei", 14, "bold"),
                           padding=15,  # 调整内边距，为字母提示留出空间
                           # 移除固定宽度，让按钮根据网格自适应
                           justify="center",
                           anchor="center",
                           wrapLength=0,  # 允许自动换行
                           height=2,  # 设置两行高度
                           width=8)  # 保持适当宽度
        self.style.map("Keypad.TButton", 
                      background=[("active", "#357abd"), ("disabled", "#d9d9d9")])
        
        # 配置清除按钮样式
        self.style.configure("KeypadClear.TButton", 
                           font=("Microsoft YaHei", 18, "bold"),
                           foreground="#ff6b6b",
                           background="#f5f5f5",
                           borderwidth=1,
                           relief="solid")
        self.style.map("KeypadClear.TButton", 
                      background=[("active", "#ffebee"), ("disabled", "#d9d9d9")])

    def on_tab_changed(self, event):
        tab_control = event.widget
        current_tab = tab_control.tab(tab_control.select(), "text")
        self.current_tab = current_tab
        self.refresh_contact_list()

    def refresh_contact_list(self):
        # 确定当前使用的列表框
        if self.current_tab == "全部联系人":
            current_listbox = self.contact_list
            self.current_contacts = self.manager.get_all_contacts()
        elif self.current_tab == "常用联系人":
            current_listbox = self.frequent_list
            self.current_contacts = self.manager.get_frequent_contacts()
        else:
            # 九键搜索标签页，不更新列表
            return

        # 清空并更新列表
        current_listbox.delete(0, tk.END)
        for contact in self.current_contacts:
            status = "[常用]" if contact.is_frequent else ""
            current_listbox.insert(tk.END, f"{status}{contact.name} - {contact.phone} - {contact.email}")

    def on_contact_select(self, event):
        # 获取触发事件的列表框
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            contact = self.current_contacts[index]
            self.name_var.set(contact.name)
            self.phone_var.set(contact.phone)
            self.email_var.set(contact.email)
            self.remark_var.set(contact.remark)
            self.country_var.set(contact.country)

    def add_contact(self):
        AddContactDialog(self.root, self.manager, self.refresh_contact_list)

    def edit_contact(self, event=None):
        # 确定当前使用的列表框
        if self.current_tab == "全部联系人":
            current_listbox = self.contact_list
        elif self.current_tab == "常用联系人":
            current_listbox = self.frequent_list
        else:
            # 九键搜索标签页，使用九键结果列表
            current_listbox = self.keypad_result_list
        
        selection = current_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个联系人")
            return

        index = selection[0]
        
        if self.current_tab == "九键搜索":
            # 九键搜索结果需要特殊处理
            display_text = current_listbox.get(index)
            parts = display_text.split(" - ")
            if len(parts) >= 2:
                name_part = parts[0].replace("[常用]", "").strip()
                phone = parts[1]
                
                # 查找对应的联系人对象
                for i, contact in enumerate(self.storage.contacts):
                    if contact.name == name_part and contact.phone == phone:
                        EditContactDialog(self.root, self.manager, i, contact, self.refresh_contact_list)
                        break
        else:
            # 正常列表处理
            contact = self.current_contacts[index]
            original_index = self.storage.contacts.index(contact)
            EditContactDialog(self.root, self.manager, original_index, contact, self.refresh_contact_list)

    def delete_contact(self):
        # 确定当前使用的列表框
        if self.current_tab == "全部联系人":
            current_listbox = self.contact_list
        elif self.current_tab == "常用联系人":
            current_listbox = self.frequent_list
        else:
            # 九键搜索标签页，不支持直接删除
            messagebox.showinfo("提示", "请在全部联系人或常用联系人标签页中进行删除操作")
            return
        
        selection = current_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个联系人")
            return

        index = selection[0]
        contact = self.current_contacts[index]
        original_index = self.storage.contacts.index(contact)

        if messagebox.askyesno("确认", f"确定要删除联系人 {contact.name} 吗?"):
            self.manager.delete_contact(original_index)
            self.refresh_contact_list()
            self.clear_detail()

    def toggle_frequent(self):
        # 确定当前使用的列表框
        if self.current_tab == "全部联系人":
            current_listbox = self.contact_list
        elif self.current_tab == "常用联系人":
            current_listbox = self.frequent_list
        else:
            # 九键搜索标签页，不支持直接标记
            messagebox.showinfo("提示", "请在全部联系人或常用联系人标签页中进行标记操作")
            return
        
        selection = current_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个联系人")
            return

        index = selection[0]
        contact = self.current_contacts[index]
        original_index = self.storage.contacts.index(contact)

        contact.is_frequent = not contact.is_frequent
        self.manager.update_contact(original_index, contact)
        self.refresh_contact_list()
        self.on_contact_select(None)

    def search_by_name(self):
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return

        results = self.manager.search_by_name(search_term)
        self.show_search_results(results)

    def search_by_phone(self):
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return

        results = self.manager.search_by_phone(search_term)
        self.show_search_results(results)
    
    def search_by_keypad(self):
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("警告", "请输入九键数字序列")
            return
        
        # 验证输入是否为纯数字
        if not search_term.isdigit():
            messagebox.showwarning("警告", "九键搜索只能输入数字")
            return
        
        results = self.manager.search_by_keypad(search_term)
        self.show_search_results(results)
    
    def unified_search(self, event=None):
        """统一搜索功能：同时搜索姓名、电话、邮箱"""
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return
        
        # 获取所有联系人
        all_contacts = self.manager.get_all_contacts()
        results = []
        
        # 统一搜索逻辑
        search_term_lower = search_term.lower()
        for contact in all_contacts:
            # 搜索姓名
            if search_term_lower in contact.name.lower():
                results.append(contact)
                continue
            # 搜索电话
            if search_term in contact.phone:
                results.append(contact)
                continue
            # 搜索邮箱
            if contact.email and search_term_lower in contact.email.lower():
                results.append(contact)
                continue
            # 搜索九键编码
            if search_term.isdigit():
                # 检查九键编码是否匹配
                keypad_code = self.manager.convert_to_keypad_code(contact.name.lower())
                if search_term in keypad_code:
                    results.append(contact)
                    continue
        
        # 去除重复结果
        unique_results = []
        seen = set()
        for contact in results:
            if contact.phone not in seen:
                seen.add(contact.phone)
                unique_results.append(contact)
        
        # 显示结果
        self.show_search_results(unique_results)
    
    def keypad_button_click(self, num):
        """九键按钮点击事件"""
        if num in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
            current_text = self.keypad_input_var.get()
            self.keypad_input_var.set(current_text + num)
            # 自动搜索
            self.keypad_auto_search()
    
    def keypad_clear(self):
        """清除九键输入"""
        self.keypad_input_var.set("")
        self.keypad_result_var.set("请使用下方拨号键盘输入数字")
        self.keypad_result_list.delete(0, tk.END)
    
    def keypad_backspace(self):
        """删除九键输入的最后一个字符"""
        current_text = self.keypad_input_var.get()
        if current_text:
            self.keypad_input_var.set(current_text[:-1])
            # 自动搜索
            self.keypad_auto_search()
    
    def keypad_search(self):
        """执行九键搜索"""
        search_term = self.keypad_input_var.get().strip()
        if not search_term:
            self.keypad_result_var.set("请输入数字后再搜索")
            return
        
        results = self.manager.search_by_keypad(search_term)
        self.keypad_display_results(results, search_term)
    
    def keypad_auto_search(self):
        """自动搜索（输入时实时搜索）"""
        search_term = self.keypad_input_var.get().strip()
        if not search_term:
            self.keypad_result_var.set("请使用下方拨号键盘输入数字")
            self.keypad_result_list.delete(0, tk.END)
            return
        
        results = self.manager.search_by_keypad(search_term)
        self.keypad_display_results(results, search_term)
    
    def keypad_display_results(self, results, search_term):
        """显示九键搜索结果"""
        self.keypad_result_list.delete(0, tk.END)
        
        if not results:
            self.keypad_result_var.set(f"未找到匹配 '{search_term}' 的联系人")
            return
        
        self.keypad_result_var.set(f"找到 {len(results)} 个匹配的联系人")
        for contact in results:
            status = "[常用]" if contact.is_frequent else ""
            self.keypad_result_list.insert(tk.END, f"{status}{contact.name} - {contact.phone}")
    
    def on_keypad_result_select(self, event):
        """处理九键搜索结果选择"""
        selection = self.keypad_result_list.curselection()
        if selection:
            index = selection[0]
            # 获取当前显示的结果
            display_text = self.keypad_result_list.get(index)
            # 从显示文本中提取联系人信息
            parts = display_text.split(" - ")
            if len(parts) >= 2:
                name_part = parts[0].replace("[常用]", "").strip()
                phone = parts[1]
                
                # 查找对应的联系人对象
                for contact in self.storage.contacts:
                    if contact.name == name_part and contact.phone == phone:
                        # 显示在详情面板
                        self.name_var.set(contact.name)
                        self.phone_var.set(contact.phone)
                        self.email_var.set(contact.email)
                        self.remark_var.set(contact.remark)
                        self.country_var.set(contact.country)
                        break
    
    def on_keypad_result_double_click(self, event):
        """处理九键搜索结果双击事件（编辑联系人）"""
        selection = self.keypad_result_list.curselection()
        if not selection:
            return
        
        index = selection[0]
        display_text = self.keypad_result_list.get(index)
        parts = display_text.split(" - ")
        if len(parts) >= 2:
            name_part = parts[0].replace("[常用]", "").strip()
            phone = parts[1]
            
            # 查找对应的联系人对象
            for i, contact in enumerate(self.storage.contacts):
                if contact.name == name_part and contact.phone == phone:
                    EditContactDialog(self.root, self.manager, i, contact, self.refresh_contact_list)
                    break

    def show_search_results(self, results):
        self.contact_list.delete(0, tk.END)
        self.current_contacts = results
        for contact in results:
            status = "[常用]" if contact.is_frequent else ""
            self.contact_list.insert(tk.END, f"{status}{contact.name} - {contact.phone} - {contact.email}")

    def reset_search(self):
        self.search_var.set("")
        self.refresh_contact_list()

    def export_excel(self):
        if not self.storage.contacts:
            messagebox.showwarning("警告", "没有联系人可以导出")
            return

        ExcelExporter.export_to_excel(self.storage.contacts)

    def export_txt(self):
        if not self.storage.contacts:
            messagebox.showwarning("警告", "没有联系人可以导出")
            return

        TXTExporter.export_to_txt(self.storage.contacts)

    def export_md(self):
        if not self.storage.contacts:
            messagebox.showwarning("警告", "没有联系人可以导出")
            return

        MDExporter.export_to_md(self.storage.contacts)

    def clear_detail(self):
        self.name_var.set("")
        self.phone_var.set("")
        self.email_var.set("")
        self.remark_var.set("")
        self.country_var.set("")

class AddContactDialog:
    def __init__(self, parent, manager, refresh_callback):
        self.parent = parent
        self.manager = manager
        self.refresh_callback = refresh_callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("添加联系人")
        
        # 设置窗口大小和位置
        dialog_width = 450
        dialog_height = 350
        
        # 获取父窗口位置
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # 设置窗口属性
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self):
        # 姓名
        name_frame = ttk.Frame(self.dialog)
        name_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(name_frame, text="姓名:", width=10).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 电话
        phone_frame = ttk.Frame(self.dialog)
        phone_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(phone_frame, text="电话:", width=10).pack(side=tk.LEFT)
        self.phone_var = tk.StringVar()
        ttk.Entry(phone_frame, textvariable=self.phone_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 邮箱
        email_frame = ttk.Frame(self.dialog)
        email_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(email_frame, text="邮箱:", width=10).pack(side=tk.LEFT)
        self.email_var = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.email_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 备注
        remark_frame = ttk.Frame(self.dialog)
        remark_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(remark_frame, text="备注:", width=10).pack(side=tk.LEFT)
        self.remark_var = tk.StringVar()
        ttk.Entry(remark_frame, textvariable=self.remark_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 按钮
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=20, padx=20)
        ttk.Button(button_frame, text="添加", command=self.add_contact).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5, expand=True)

    def add_contact(self):
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        remark = self.remark_var.get().strip()

        if not name:
            messagebox.showerror("错误", "姓名不能为空")
            return
        
        if not phone:
            messagebox.showerror("错误", "电话不能为空")
            return
        
        # 验证手机号格式
        if not Validator.is_valid_phone(phone):
            messagebox.showerror("错误", "请输入有效的电话号码")
            return
        
        # 验证邮箱格式
        if not Validator.is_valid_email(email):
            messagebox.showerror("错误", "请输入有效的邮箱地址")
            return

        contact = Contact(name, phone, email, remark)
        if self.manager.add_contact(contact):
            self.refresh_callback()
            self.dialog.destroy()

class EditContactDialog:
    def __init__(self, parent, manager, index, contact, refresh_callback):
        self.parent = parent
        self.manager = manager
        self.index = index
        self.contact = contact
        self.refresh_callback = refresh_callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("修改联系人")
        
        # 设置窗口大小和位置
        dialog_width = 450
        dialog_height = 380  # 编辑窗口略高，因为多了一个常用联系人选项
        
        # 获取父窗口位置
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # 设置窗口属性
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self):
        # 姓名
        name_frame = ttk.Frame(self.dialog)
        name_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(name_frame, text="姓名:", width=10).pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self.contact.name)
        ttk.Entry(name_frame, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 电话
        phone_frame = ttk.Frame(self.dialog)
        phone_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(phone_frame, text="电话:", width=10).pack(side=tk.LEFT)
        self.phone_var = tk.StringVar(value=self.contact.phone)
        ttk.Entry(phone_frame, textvariable=self.phone_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 邮箱
        email_frame = ttk.Frame(self.dialog)
        email_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(email_frame, text="邮箱:", width=10).pack(side=tk.LEFT)
        self.email_var = tk.StringVar(value=self.contact.email)
        ttk.Entry(email_frame, textvariable=self.email_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 备注
        remark_frame = ttk.Frame(self.dialog)
        remark_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(remark_frame, text="备注:", width=10).pack(side=tk.LEFT)
        self.remark_var = tk.StringVar(value=self.contact.remark)
        ttk.Entry(remark_frame, textvariable=self.remark_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 常用联系人选项
        frequent_frame = ttk.Frame(self.dialog)
        frequent_frame.pack(fill=tk.X, pady=10, padx=20)
        self.frequent_var = tk.BooleanVar(value=self.contact.is_frequent)
        ttk.Checkbutton(frequent_frame, text="设为常用联系人", variable=self.frequent_var).pack(side=tk.LEFT)

        # 按钮
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=20, padx=20)
        ttk.Button(button_frame, text="保存", command=self.save_contact).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5, expand=True)

    def save_contact(self):
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        remark = self.remark_var.get().strip()
        is_frequent = self.frequent_var.get()

        if not name:
            messagebox.showerror("错误", "姓名不能为空")
            return
        
        if not phone:
            messagebox.showerror("错误", "电话不能为空")
            return
        
        # 验证手机号格式
        if not Validator.is_valid_phone(phone):
            messagebox.showerror("错误", "请输入有效的电话号码")
            return
        
        # 验证邮箱格式
        if not Validator.is_valid_email(email):
            messagebox.showerror("错误", "请输入有效的邮箱地址")
            return

        # 检查电话号码是否已存在（排除当前联系人）
        for c in self.manager.storage.contacts:
            if c.phone == phone and c != self.contact:
                messagebox.showerror("错误", "该电话号码已存在")
                return

        contact = Contact(name, phone, email, remark, is_frequent)
        self.manager.update_contact(self.index, contact)
        self.refresh_callback()
        self.dialog.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ContactGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.storage.save_contacts(), root.destroy()))
    root.mainloop()
