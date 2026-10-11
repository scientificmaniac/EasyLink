import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Any
from contact import Contact
from validator import Validator
import logging

# 配置日志
logger = logging.getLogger(__name__)

class BaseContactDialog:
    """联系人对话框基类，用于复用添加和编辑对话框的共同代码"""
    def __init__(self, parent: tk.Tk, manager: Any, refresh_callback: Callable[[], None], title: str, width: int, height: int):
        """初始化对话框"""
        self.parent = parent
        self.manager = manager
        self.refresh_callback = refresh_callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        
        # 设置窗口大小和位置
        try:
            # 获取父窗口位置
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            # 计算居中位置
            x = parent_x + (parent_width - width) // 2
            y = parent_y + (parent_height - height) // 2
            
            self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        except Exception as e:
            # 如果获取父窗口位置失败，使用默认居中位置
            self.dialog.geometry(f"{width}x{height}+50+50")
            logger.warning(f"Failed to get parent window position: {e}")
        
        # 设置窗口属性
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 初始化变量
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.remark_var = tk.StringVar()
        self.frequent_var = tk.BooleanVar(value=False)

    def setup_common_ui(self) -> None:
        """设置通用UI组件"""
        # 姓名
        name_frame = ttk.Frame(self.dialog)
        name_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(name_frame, text="姓名:", width=10).pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 电话
        phone_frame = ttk.Frame(self.dialog)
        phone_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(phone_frame, text="电话:", width=10).pack(side=tk.LEFT)
        ttk.Entry(phone_frame, textvariable=self.phone_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 邮箱
        email_frame = ttk.Frame(self.dialog)
        email_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(email_frame, text="邮箱:", width=10).pack(side=tk.LEFT)
        ttk.Entry(email_frame, textvariable=self.email_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 备注
        remark_frame = ttk.Frame(self.dialog)
        remark_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(remark_frame, text="备注:", width=10).pack(side=tk.LEFT)
        ttk.Entry(remark_frame, textvariable=self.remark_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get_contact_data(self) -> tuple:
        """获取联系人数据"""
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        remark = self.remark_var.get().strip()
        is_frequent = self.frequent_var.get()
        return name, phone, email, remark, is_frequent

class AddContactDialog(BaseContactDialog):
    def __init__(self, parent: tk.Tk, manager: Any, refresh_callback: Callable[[], None]):
        """初始化添加联系人对话框"""
        super().__init__(parent, manager, refresh_callback, "添加联系人", 450, 350)
        self.setup_ui()

    def setup_ui(self) -> None:
        """设置添加对话框UI"""
        self.setup_common_ui()
        
        # 按钮
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=20, padx=20)
        ttk.Button(button_frame, text="添加", command=self.add_contact).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5, expand=True)

    def add_contact(self) -> None:
        """添加联系人"""
        name, phone, email, remark, is_frequent = self.get_contact_data()

        # 验证联系人数据
        valid, msg = Validator.validate_contact_data(name, phone, email, remark)
        if not valid:
            messagebox.showerror("错误", msg)
            return

        try:
            contact = Contact(name, phone, email, remark)
            success, msg = self.manager.add_contact(contact)
            if success:
                logger.info(f"Contact added successfully: {name} ({phone})")
                self.refresh_callback()
                self.dialog.destroy()
            else:
                messagebox.showerror("错误", msg)
                logger.warning(f"Failed to add contact: {msg}")
        except Exception as e:
            messagebox.showerror("错误", f"添加联系人失败: {str(e)}")
            logger.error(f"Unexpected error when adding contact: {e}", exc_info=True)

class EditContactDialog(BaseContactDialog):
    def __init__(self, parent: tk.Tk, manager: Any, index: int, contact: Contact, refresh_callback: Callable[[], None]):
        """初始化修改联系人对话框"""
        super().__init__(parent, manager, refresh_callback, "修改联系人", 450, 380)
        self.index = index
        
        # 初始化变量值
        self.name_var.set(contact.name)
        self.phone_var.set(contact.phone)
        self.email_var.set(contact.email)
        self.remark_var.set(contact.remark)
        self.frequent_var.set(contact.is_frequent)
        
        self.setup_ui()

    def setup_ui(self) -> None:
        """设置编辑对话框UI"""
        self.setup_common_ui()
        
        # 常用联系人选项
        frequent_frame = ttk.Frame(self.dialog)
        frequent_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Checkbutton(frequent_frame, text="设为常用联系人", variable=self.frequent_var).pack(side=tk.LEFT)

        # 按钮
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, pady=20, padx=20)
        ttk.Button(button_frame, text="保存", command=self.save_contact).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5, expand=True)

    def save_contact(self) -> None:
        """保存联系人修改"""
        name, phone, email, remark, is_frequent = self.get_contact_data()

        # 验证联系人数据
        valid, msg = Validator.validate_contact_data(name, phone, email, remark)
        if not valid:
            messagebox.showerror("错误", msg)
            return

        # 电话号码是否与他人重复交由 ContactManager 统一判定，此处不再重复实现

        try:
            contact = Contact(name, phone, email, remark, is_frequent)
            success, msg = self.manager.update_contact(self.index, contact)
            if success:
                logger.info(f"Contact updated successfully: {name} ({phone})")
                self.refresh_callback()
                self.dialog.destroy()
            else:
                messagebox.showerror("错误", msg)
                logger.warning(f"Failed to update contact: {msg}")
        except Exception as e:
            messagebox.showerror("错误", f"保存联系人失败: {str(e)}")
            logger.error(f"Unexpected error when updating contact: {e}", exc_info=True)
