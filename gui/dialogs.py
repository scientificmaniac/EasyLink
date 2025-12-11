import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Any
from contact import Contact
from validator import Validator
import logging

# 配置日志
logger = logging.getLogger(__name__)

class AddContactDialog:
    def __init__(self, parent: tk.Tk, manager: Any, refresh_callback: Callable[[], None]):
        """初始化添加联系人对话框"""
        self.parent = parent
        self.manager = manager
        self.refresh_callback = refresh_callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("添加联系人")
        
        # 设置窗口大小和位置
        dialog_width = 450
        dialog_height = 350
        
        try:
            # 获取父窗口位置
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            # 计算居中位置
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception as e:
            # 如果获取父窗口位置失败，使用默认居中位置
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+50+50")
            logger.warning(f"Failed to get parent window position: {e}")
        
        # 设置窗口属性
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self) -> None:
        """设置对话框UI"""
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

    def add_contact(self) -> None:
        """添加联系人"""
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        remark = self.remark_var.get().strip()

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

class EditContactDialog:
    def __init__(self, parent: tk.Tk, manager: Any, index: int, contact: Contact, refresh_callback: Callable[[], None]):
        """初始化修改联系人对话框"""
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
        
        try:
            # 获取父窗口位置
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            # 计算居中位置
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception as e:
            # 如果获取父窗口位置失败，使用默认居中位置
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+50+50")
            logger.warning(f"Failed to get parent window position: {e}")
        
        # 设置窗口属性
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self) -> None:
        """设置对话框UI"""
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

    def save_contact(self) -> None:
        """保存联系人修改"""
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        remark = self.remark_var.get().strip()
        is_frequent = self.frequent_var.get()

        # 验证联系人数据
        valid, msg = Validator.validate_contact_data(name, phone, email, remark)
        if not valid:
            messagebox.showerror("错误", msg)
            return

        # 检查电话号码是否已存在（排除当前联系人）
        existing_contact = self.manager.storage.get_contact_by_phone(phone)
        if existing_contact and existing_contact != self.contact:
            messagebox.showerror("错误", "该电话号码已存在")
            return

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
