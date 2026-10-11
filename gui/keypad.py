#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
九键搜索页面

提供拨号键盘输入、实时搜索与结果展示。

说明：
    结果列表的行顺序与 self._results 严格一一对应，选中时按行号取回联系人即可，
    不需要（也不应该）用电话号码作为行 iid —— 一旦数据中存在重复号码，
    重复的 iid 会让 Treeview 直接抛 TclError。
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from contact import Contact
from gui.dialogs import EditContactDialog

logger = logging.getLogger(__name__)

# 界面字体：与主窗口保持一致
_FONT_FAMILY = "BCU DongHui"


class KeypadSearchPage:
    """九键拨号搜索页面"""

    def __init__(self, parent, manager, refresh_callback, update_detail_callback=None):
        self.parent = parent
        self.manager = manager
        self.refresh_callback = refresh_callback
        self.update_detail_callback = update_detail_callback  # 用于更新主窗口详情
        self.keypad_window = None  # 独立拨号键盘窗口
        self.keypad_input_var = tk.StringVar()  # 九键输入变量
        self._results: List[Contact] = []  # 与结果列表行顺序一一对应
        self.setup_ui()

    def setup_ui(self):
        """设置九键搜索页面"""
        keypad_frame = ttk.Frame(self.parent, padding="20 20 20 20")
        keypad_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(keypad_frame, text="九键拨号搜索",
                  font=(_FONT_FAMILY, 14, "bold"),
                  foreground="#4a90e2").pack(pady=(0, 20))

        self.keypad_result_var = tk.StringVar(value="请点击下方按钮打开拨号键盘")
        ttk.Label(keypad_frame, textvariable=self.keypad_result_var,
                  font=(_FONT_FAMILY, 10),
                  foreground="#666666").pack(pady=(0, 20))

        keypad_btn_frame = ttk.Frame(keypad_frame)
        keypad_btn_frame.pack(fill=tk.X, pady=20, padx=50)
        ttk.Button(keypad_btn_frame, text="打开拨号键盘", command=self.open_keypad_window,
                   style="TButton").pack(fill=tk.X, expand=True, ipadx=10, ipady=5)

        search_frame = ttk.Frame(keypad_frame)
        search_frame.pack(fill=tk.X, pady=10, padx=50)
        ttk.Button(search_frame, text="搜索", command=self.keypad_search,
                   width=20).pack(fill=tk.X, expand=True)

        result_frame = ttk.LabelFrame(keypad_frame, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=20, padx=30)

        tree_container = ttk.Frame(result_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.keypad_result_list = ttk.Treeview(tree_container,
                                               columns=('status', 'name', 'phone', 'email'),
                                               show='headings',
                                               height=10,
                                               style='Treeview')

        self.keypad_result_list.heading('status', text='状态', anchor='center')
        self.keypad_result_list.heading('name', text='姓名', anchor='center')
        self.keypad_result_list.heading('phone', text='电话', anchor='center')
        self.keypad_result_list.heading('email', text='邮箱', anchor='center')

        self.keypad_result_list.column('status', width=60, anchor='center', minwidth=60)
        self.keypad_result_list.column('name', width=120, anchor='center', minwidth=100)
        self.keypad_result_list.column('phone', width=150, anchor='center', minwidth=120)
        self.keypad_result_list.column('email', width=180, anchor='center', minwidth=150)

        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL,
                                    command=self.keypad_result_list.yview)
        self.keypad_result_list.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL,
                                    command=self.keypad_result_list.xview)
        self.keypad_result_list.configure(xscrollcommand=h_scrollbar.set)

        self.keypad_result_list.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.keypad_result_list.bind("<<TreeviewSelect>>", self.on_keypad_result_select)
        self.keypad_result_list.bind("<Double-1>", self.on_keypad_result_double_click)

    def open_keypad_window(self):
        """打开独立的拨号键盘窗口，包含输入框和九个键"""
        if self.keypad_window and self.keypad_window.winfo_exists():
            self.keypad_window.lift()
            return

        self.keypad_window = tk.Toplevel(self.parent)
        self.keypad_window.title("九键拨号键盘")
        self.keypad_window.geometry("320x480")
        self.keypad_window.resizable(False, False)
        self.keypad_window.attributes('-topmost', True)

        input_frame = ttk.Frame(self.keypad_window, padding="10")
        input_frame.pack(fill=tk.X, pady=(15, 10))

        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.X, padx=20, pady=10)

        ttk.Entry(input_container, textvariable=self.keypad_input_var,
                  font=(_FONT_FAMILY, 16), justify="center",
                  foreground="#333333", state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipadx=10, ipady=15)

        ttk.Button(input_container, text="×",
                   command=self.keypad_clear,
                   style="KeypadClear.TButton").pack(side=tk.RIGHT, fill=tk.Y, padx=5, ipadx=15)

        keypad_grid = ttk.Frame(self.keypad_window, padding="15")
        keypad_grid.pack(fill=tk.BOTH, expand=True, pady=5)

        # 用「删除 / 清除」替换传统键盘上的 * 和 #
        keypad_buttons = [
            ('1', ''), ('2', 'ABC'), ('3', 'DEF'),
            ('4', 'GHI'), ('5', 'JKL'), ('6', 'MNO'),
            ('7', 'PQRS'), ('8', 'TUV'), ('9', 'WXYZ'),
            ('删除', 'DEL'), ('0', '+'), ('清除', 'CLR'),
        ]

        for i, (num, letters) in enumerate(keypad_buttons):
            row, col = divmod(i, 3)

            keypad_grid.grid_rowconfigure(row, weight=1, minsize=60)
            keypad_grid.grid_columnconfigure(col, weight=1, minsize=80)

            if num == '删除':
                command = self.keypad_backspace
            elif num == '清除':
                command = self.keypad_clear
            else:
                command = lambda n=num: self.keypad_button_click(n)  # noqa: E731

            if letters:
                text = f"{num}\n{letters}"
            else:
                text = num

            ttk.Button(keypad_grid, text=text, command=command,
                       style="Keypad.TButton", padding=10).grid(
                row=row, column=col, sticky="nsew", padx=5, pady=5)

    # ------------------------------------------------------------------
    # 输入与搜索
    # ------------------------------------------------------------------
    def keypad_button_click(self, num):
        """九键按钮点击事件"""
        if num in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
            self.keypad_input_var.set(self.keypad_input_var.get() + num)
            self.keypad_auto_search()

    def clear_keypad_results(self):
        """清空九键搜索结果"""
        for item in self.keypad_result_list.get_children():
            self.keypad_result_list.delete(item)
        self._results = []

    def keypad_clear(self):
        """清除九键输入"""
        self.keypad_input_var.set("")
        self.keypad_result_var.set("请使用下方拨号键盘输入数字")
        self.clear_keypad_results()

    def keypad_backspace(self):
        """删除九键输入的最后一个字符"""
        current_text = self.keypad_input_var.get()
        if current_text:
            self.keypad_input_var.set(current_text[:-1])
            self.keypad_auto_search()

    def perform_keypad_search(self, search_term):
        """执行九键搜索并显示结果"""
        try:
            results = self.manager.search_by_keypad(search_term)
        except ValueError as e:
            self.keypad_result_var.set(str(e))
            self.clear_keypad_results()
            return
        self.keypad_display_results(results, search_term)

    def keypad_search(self):
        """按钮触发的九键搜索"""
        search_term = self.keypad_input_var.get().strip()
        if not search_term:
            self.keypad_result_var.set("请输入数字后再搜索")
            return
        self.perform_keypad_search(search_term)

    def keypad_auto_search(self):
        """输入变化时的实时搜索"""
        search_term = self.keypad_input_var.get().strip()
        if not search_term:
            self.keypad_result_var.set("请使用下方拨号键盘输入数字")
            self.clear_keypad_results()
            return
        self.perform_keypad_search(search_term)

    def keypad_display_results(self, results, search_term):
        """展示九键搜索结果"""
        self.clear_keypad_results()

        if not results:
            self.keypad_result_var.set(f"未找到匹配 '{search_term}' 的联系人")
            return

        self.keypad_result_var.set(f"找到 {len(results)} 个匹配的联系人")
        self._results = list(results)

        for contact in self._results:
            status = "常用" if contact.is_frequent else ""
            self.keypad_result_list.insert(
                '', tk.END,
                values=(status, contact.name, contact.format_phone(), contact.email),
            )

    # ------------------------------------------------------------------
    # 结果选择
    # ------------------------------------------------------------------
    def _selected_contact(self) -> Optional[Contact]:
        """按行号取回当前选中的联系人，未选中时返回 None"""
        selection = self.keypad_result_list.selection()
        if not selection:
            return None

        row = self.keypad_result_list.index(selection[0])
        if not 0 <= row < len(self._results):
            return None
        return self._results[row]

    def on_keypad_result_select(self, event):
        """选中结果时通知主窗口刷新详情面板"""
        contact = self._selected_contact()
        if contact is not None and self.update_detail_callback:
            self.update_detail_callback(contact)

    def on_keypad_result_double_click(self, event):
        """双击结果时打开编辑对话框"""
        contact = self._selected_contact()
        if contact is None:
            return

        try:
            index = self.manager.storage.contacts.index(contact)
        except ValueError:
            logger.warning("九键搜索结果已不在当前数据集中: %r", contact)
            messagebox.showwarning("警告", "该联系人已不在当前列表中，请重新搜索")
            return

        EditContactDialog(self.parent.winfo_toplevel(), self.manager, index,
                          contact, self.refresh_callback)
