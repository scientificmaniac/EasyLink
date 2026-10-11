#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块

负责搭建 Tkinter 界面，并把用户操作转发给 ContactManager。
数据层（importer / exporter）不直接弹对话框，而是通过 notifier 回调把提示
交回本层展示（见 _notify）。
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

from contact import Contact
from exporter import ExcelExporter, TXTExporter, MDExporter
from importer import DataImporter
from gui.dialogs import AddContactDialog, EditContactDialog
from gui.keypad import KeypadSearchPage
from notifier import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING

logger = logging.getLogger(__name__)

# 界面字体：优先使用当前系统中存在的中文字体
_FONT_FAMILY = "BCU DongHui"


class ContactGUI:
    """主窗口：联系人列表、详情面板与导入导出入口"""

    def __init__(self, root, storage, manager):
        self.root = root
        self.storage = storage
        self.manager = manager
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

        self.current_tab = "全部联系人"
        self.current_contacts = self.manager.get_all_contacts()
        self.selected_contact = None  # 用于跟踪当前选中的联系人

        self.setup_ui()
        self.refresh_contact_list()

    # ------------------------------------------------------------------
    # 样式与界面
    # ------------------------------------------------------------------
    def setup_style(self):
        # 设置主题
        self.style.theme_use("clam")

        # 主窗口背景
        self.root.configure(bg="#f5f5f5")

        # 标签样式
        self.style.configure("TLabel", background="#f5f5f5", foreground="#333333",
                             font=(_FONT_FAMILY, 10))

        # 按钮样式
        self.style.configure("TButton",
                             background="#4a90e2",
                             foreground="white",
                             font=(_FONT_FAMILY, 10),
                             padding=6)
        self.style.map("TButton",
                       background=[("active", "#357abd"), ("disabled", "#d9d9d9")],
                       foreground=[("disabled", "#999999")])

        # 输入框样式
        self.style.configure("TEntry",
                             fieldbackground="white",
                             foreground="#333333",
                             padding=5,
                             font=(_FONT_FAMILY, 10))

        # 列表框样式
        self.style.configure("Listbox",
                             background="white",
                             foreground="#333333",
                             font=(_FONT_FAMILY, 12),
                             selectbackground="#e6f2ff",
                             selectforeground="#000000")

        # 标签页样式
        self.style.configure("TNotebook", background="#f5f5f5")
        self.style.configure("TNotebook.Tab",
                             background="#e0e0e0",
                             foreground="#333333",
                             padding=[15, 5],
                             font=(_FONT_FAMILY, 10))
        self.style.map("TNotebook.Tab",
                       background=[("selected", "white")],
                       foreground=[("selected", "#4a90e2")])

        # 详情框架样式
        self.style.configure("TLabelframe",
                             background="#f5f5f5",
                             foreground="#333333",
                             font=(_FONT_FAMILY, 11, "bold"))
        self.style.configure("TLabelframe.Label",
                             background="#f5f5f5",
                             foreground="#333333",
                             font=(_FONT_FAMILY, 11, "bold"))

        # 配置keypad按钮样式 - 确保多行文本正确显示，适应不同分辨率
        self.style.configure("Keypad.TButton",
                             font=(_FONT_FAMILY, 14, "bold"),
                             padding=15,
                             justify="center",
                             anchor="center",
                             wrapLength=0,
                             height=2,
                             width=8)
        self.style.map("Keypad.TButton",
                       background=[("active", "#357abd"), ("disabled", "#d9d9d9")])

        # 配置清除按钮样式
        self.style.configure("KeypadClear.TButton",
                             font=(_FONT_FAMILY, 18, "bold"),
                             foreground="#ff6b6b",
                             background="#f5f5f5",
                             borderwidth=1,
                             relief="solid")
        self.style.map("KeypadClear.TButton",
                       background=[("active", "#ffebee"), ("disabled", "#d9d9d9")])

    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="个人通讯录管理系统",
                                font=(_FONT_FAMILY, 16, "bold"),
                                foreground="#4a90e2")
        title_label.pack(pady=(0, 15))

        # 搜索和功能按钮区
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # 搜索框架
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(search_frame, text="搜索:", font=(_FONT_FAMILY, 10)).pack(side=tk.LEFT, padx=(0, 5))
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

        # 中间内容区 - 确保不会挤压底部的帮助按钮
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # 左侧联系人列表区
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 创建标签页
        tab_control = ttk.Notebook(left_frame)
        self.all_contacts_tab = ttk.Frame(tab_control)
        self.frequent_contacts_tab = ttk.Frame(tab_control)
        self.keypad_search_tab = ttk.Frame(tab_control)

        tab_control.add(self.all_contacts_tab, text="全部联系人")
        tab_control.add(self.frequent_contacts_tab, text="常用联系人")
        tab_control.add(self.keypad_search_tab, text="九键搜索")
        tab_control.pack(fill=tk.BOTH, expand=True)

        tab_control.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 创建联系人列表Treeview
        self.contact_list = self._create_treeview(self.all_contacts_tab)
        self.frequent_list = self._create_treeview(self.frequent_contacts_tab)

        # 右侧详情和导出区
        right_frame = ttk.Frame(content_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

        detail_frame = ttk.LabelFrame(right_frame, text="联系人详情", padding="10 10 10 10")
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # 只读详情字段
        self.name_var = self._add_detail_row(detail_frame, "姓名:", 8)
        self.phone_var = self._add_detail_row(detail_frame, "电话:", 8)
        self.country_var = self._add_detail_row(detail_frame, "国家:", 8)
        self.email_var = self._add_detail_row(detail_frame, "邮箱:", 8)
        self.remark_var = self._add_detail_row(detail_frame, "备注:", 8)

        # 常用联系人标记
        frequent_frame = ttk.Frame(detail_frame)
        frequent_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(frequent_frame, text="标记为常用", command=self.toggle_frequent).pack(fill=tk.X, padx=5)

        # 导出框架
        export_frame = ttk.LabelFrame(right_frame, text="数据导出", padding="10 10 10 10")
        export_frame.pack(fill=tk.X, pady=(0, 15))

        export_buttons_frame = ttk.Frame(export_frame)
        export_buttons_frame.pack(fill=tk.X, pady=5)
        ttk.Button(export_buttons_frame, text="导出Excel", command=self.export_excel, width=15).pack(fill=tk.X, pady=3)
        ttk.Button(export_buttons_frame, text="导出TXT", command=self.export_txt, width=15).pack(fill=tk.X, pady=3)
        ttk.Button(export_buttons_frame, text="导出Markdown", command=self.export_md, width=15).pack(fill=tk.X, pady=3)

        # 导入框架
        import_frame = ttk.LabelFrame(right_frame, text="数据导入", padding="10 10 10 10")
        import_frame.pack(fill=tk.X)

        import_buttons_frame = ttk.Frame(import_frame)
        import_buttons_frame.pack(fill=tk.X, pady=5)
        ttk.Button(import_buttons_frame, text="导入数据", command=self.import_data, width=15).pack(fill=tk.X, pady=3)

        # 九键搜索页面
        self.keypad_page = KeypadSearchPage(
            self.keypad_search_tab, self.manager, self.refresh_contact_list, self.on_keypad_contact_select
        )

        # 帮助按钮置于右下角
        help_frame = ttk.Frame(main_frame)
        help_frame.pack(side=tk.BOTTOM, anchor=tk.SE, pady=10, padx=10)

        btn_container = ttk.Frame(help_frame)
        btn_container.pack(side=tk.RIGHT, fill=tk.NONE, expand=False)

        ttk.Button(btn_container, text="?", command=self.about_dialog,
                   width=3, style="TButton").pack(side=tk.RIGHT, padx=5, pady=5,
                                                  fill=tk.NONE, expand=False)

    def _create_treeview(self, parent):
        """创建并配置联系人列表 Treeview"""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)

        treeview = ttk.Treeview(list_frame,
                                columns=('status', 'name', 'phone', 'email'),
                                show='headings',
                                height=20,
                                style='Treeview')

        treeview.heading('status', text='状态', anchor='center')
        treeview.heading('name', text='姓名', anchor='center')
        treeview.heading('phone', text='电话', anchor='center')
        treeview.heading('email', text='邮箱', anchor='center')

        treeview.column('status', width=60, anchor='center')
        treeview.column('name', width=150, anchor='center')
        treeview.column('phone', width=180, anchor='center')
        treeview.column('email', width=220, anchor='center')

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=treeview.yview)
        treeview.configure(yscrollcommand=scrollbar.set)

        treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        treeview.bind("<<TreeviewSelect>>", self.on_treeview_select)
        treeview.bind("<Double-1>", self.edit_contact)

        return treeview

    def _add_detail_row(self, parent, label, label_width):
        """在详情面板中追加一行只读字段，返回其绑定的 StringVar"""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row, text=label, width=label_width, anchor="w").pack(side=tk.LEFT, padx=5)
        var = tk.StringVar()
        ttk.Entry(row, textvariable=var, state="disabled",
                  foreground="#666666").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        return var

    # ------------------------------------------------------------------
    # 通知
    # ------------------------------------------------------------------
    def _notify(self, level: str, message: str) -> None:
        """数据层的通知回调：把 (级别, 消息) 转成对应对话框

        importer / exporter 不认识 tkinter，它们只负责把结果交出来，
        由本层决定用什么方式呈现给用户。
        """
        if level == LEVEL_ERROR:
            messagebox.showerror("错误", message)
        elif level == LEVEL_WARNING:
            messagebox.showwarning("警告", message)
        else:
            messagebox.showinfo("提示", message)

    # ------------------------------------------------------------------
    # 列表刷新与选中
    # ------------------------------------------------------------------
    def on_tab_changed(self, event):
        tab_control = event.widget
        self.current_tab = tab_control.tab(tab_control.select(), "text")
        # 切换标签页后原列表的选中项已不属于当前视图，清空详情避免张冠李戴
        self.clear_detail()
        self.refresh_contact_list()

    def update_treeview(self, tree, contacts: List[Contact]) -> None:
        """刷新 Treeview 内容

        行顺序与 self.current_contacts 严格一一对应，选中时即可按行号取回联系人，
        不需要从「格式化后的电话文本」反推原始号码。
        """
        for item in tree.get_children():
            tree.delete(item)

        for contact in contacts:
            status = "常用" if contact.is_frequent else ""
            tree.insert('', tk.END,
                        values=(status, contact.name, contact.format_phone(), contact.email))

    def refresh_contact_list(self):
        """按当前标签页重新加载列表（会退出搜索态，恢复完整数据）"""
        if self.current_tab == "全部联系人":
            current_tree = self.contact_list
            contacts = self.manager.get_all_contacts()
        elif self.current_tab == "常用联系人":
            current_tree = self.frequent_list
            contacts = self.manager.get_frequent_contacts()
        else:
            # 九键搜索标签页由 KeypadSearchPage 自行维护列表
            return

        self.current_contacts = contacts
        self.update_treeview(current_tree, contacts)

    def get_selected_contact_from_treeview(self, treeview) -> Optional[Contact]:
        """从 Treeview 获取当前选中的联系人对象，未选中时返回 None"""
        selection = treeview.selection()
        if not selection:
            return None

        row = treeview.index(selection[0])
        if not 0 <= row < len(self.current_contacts):
            return None
        return self.current_contacts[row]

    def get_contact_by_tree_selection(self, tree, selection):
        """根据选中项返回 (在 storage.contacts 中的索引, 联系人对象)

        先按行号从 current_contacts 取对象，再回到 storage.contacts 定位索引。
        current_contacts 中的元素与 storage.contacts 是同一批对象，因此
        list.index 走的是身份比较，不会因为两条记录内容相同而认错人。
        """
        if not selection:
            return None, None

        contact = self.get_selected_contact_from_treeview(tree)
        if contact is None:
            return None, None

        try:
            return self.storage.contacts.index(contact), contact
        except ValueError:
            logger.warning("选中的联系人已不在当前数据集中: %r", contact)
            return None, None

    def display_contact_detail(self, contact: Optional[Contact]) -> None:
        """在详情面板显示联系人信息"""
        if contact:
            self.name_var.set(contact.name)
            self.phone_var.set(contact.phone)
            self.email_var.set(contact.email)
            self.remark_var.set(contact.remark)
            self.country_var.set(contact.country)
            self.selected_contact = contact
        else:
            self.clear_detail()

    def clear_detail(self):
        """清空详情面板与选中记录"""
        self.name_var.set("")
        self.phone_var.set("")
        self.email_var.set("")
        self.remark_var.set("")
        self.country_var.set("")
        self.selected_contact = None

    def on_treeview_select(self, event):
        if event is None:
            # 由代码触发的刷新：取当前标签页对应的 Treeview
            if self.current_tab == "全部联系人":
                widget = self.contact_list
            elif self.current_tab == "常用联系人":
                widget = self.frequent_list
            else:
                return
        else:
            widget = event.widget

        self.display_contact_detail(self.get_selected_contact_from_treeview(widget))

    def on_keypad_contact_select(self, contact: Contact) -> None:
        """九键搜索结果被选中时，同步刷新详情面板"""
        self.display_contact_detail(contact)

    def get_current_tree_and_selection(self):
        """获取当前标签页对应的 Treeview 及其选中项"""
        if self.current_tab == "九键搜索":
            current_tree = self.keypad_page.keypad_result_list
        elif self.current_tab == "常用联系人":
            current_tree = self.frequent_list
        else:
            current_tree = self.contact_list

        selection = current_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个联系人")
            return None, None

        return current_tree, selection

    # ------------------------------------------------------------------
    # 增删改
    # ------------------------------------------------------------------
    def add_contact(self):
        AddContactDialog(self.root, self.manager, self.refresh_contact_list)

    def edit_contact(self, event=None):
        current_tree, selection = self.get_current_tree_and_selection()
        if not current_tree or not selection:
            return

        index, contact = self.get_contact_by_tree_selection(current_tree, selection)
        if index is not None and contact:
            EditContactDialog(self.root, self.manager, index, contact, self.refresh_contact_list)

    def delete_contact(self):
        if self.current_tab == "九键搜索":
            messagebox.showinfo("提示", "请在全部联系人或常用联系人标签页中进行删除操作")
            return

        current_tree, selection = self.get_current_tree_and_selection()
        if not current_tree or not selection:
            return

        index, contact = self.get_contact_by_tree_selection(current_tree, selection)
        if index is None or not contact:
            return

        if not messagebox.askyesno("确认", f"确定要删除联系人 {contact.name} 吗?"):
            return

        success, msg = self.manager.delete_contact(index)
        if success:
            self.refresh_contact_list()
            self.clear_detail()
        else:
            messagebox.showerror("错误", msg)

    def toggle_frequent(self):
        if self.current_tab == "九键搜索":
            messagebox.showinfo("提示", "请在全部联系人或常用联系人标签页中进行标记操作")
            return

        current_tree, selection = self.get_current_tree_and_selection()
        if not current_tree or not selection:
            return

        index, contact = self.get_contact_by_tree_selection(current_tree, selection)
        if index is None or not contact:
            return

        # 交给 manager 在副本上修改：保存失败时不会留下已被翻转的内存状态
        success, msg = self.manager.set_frequent(index, not contact.is_frequent)
        if not success:
            messagebox.showerror("错误", msg)
            return

        self.refresh_contact_list()
        self.on_treeview_select(None)

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------
    def unified_search(self, event=None):
        """统一搜索：一次匹配姓名、拼音、电话、邮箱与九键数字编码"""
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return

        self.show_search_results(self.manager.search_all(search_term))

    def show_search_results(self, results):
        """在左侧列表展示搜索结果（不修改底层数据）"""
        if self.current_tab == "全部联系人":
            current_tree = self.contact_list
        elif self.current_tab == "常用联系人":
            current_tree = self.frequent_list
        else:
            # 九键搜索标签页由 KeypadSearchPage 自行维护列表
            return

        self.current_contacts = results
        self.update_treeview(current_tree, results)

    def reset_search(self):
        self.search_var.set("")
        self.refresh_contact_list()

    # ------------------------------------------------------------------
    # 导入导出
    # ------------------------------------------------------------------
    def export_data(self, export_func, export_name):
        """通用数据导出方法"""
        try:
            export_func(self.storage.contacts, notifier=self._notify)
        except Exception as e:
            logger.error("导出%s失败: %s", export_name, e, exc_info=True)
            messagebox.showerror("错误", f"导出{export_name}失败: {e}")

    def export_excel(self):
        self.export_data(ExcelExporter.export_to_excel, "Excel")

    def export_txt(self):
        self.export_data(TXTExporter.export_to_txt, "TXT")

    def export_md(self):
        self.export_data(MDExporter.export_to_md, "Markdown")

    def import_data(self):
        """选择文件并把其中的联系人导入当前通讯录"""
        file_path = filedialog.askopenfilename(
            title="选择要导入的文件",
            filetypes=[
                ("所有支持的文件", "*.xlsx *.txt *.md *.json"),
                ("Excel文件", "*.xlsx"),
                ("文本文件", "*.txt"),
                ("Markdown文件", "*.md"),
                ("JSON文件", "*.json"),
            ],
        )
        if not file_path:
            return

        try:
            success = DataImporter.import_contacts(file_path, self.manager, notifier=self._notify)
        except Exception as e:
            # 批量写入失败（如磁盘异常）不应让界面卡死或半更新
            logger.error("导入数据失败: %s", e, exc_info=True)
            messagebox.showerror("错误", f"导入失败: {e}")
            return

        if success:
            self.refresh_contact_list()
            self.clear_detail()

    def about_dialog(self):
        AboutDialog(self.root)


class AboutDialog:
    """关于对话框"""

    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("关于个人通讯录管理系统")

        dialog_width = 400
        dialog_height = 300

        try:
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception as e:
            logger.warning("获取父窗口位置失败，使用默认位置: %s", e)
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+50+50")

        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="个人通讯录管理系统",
                  font=(_FONT_FAMILY, 18, "bold"),
                  foreground="#4a90e2").pack(pady=(0, 15))

        ttk.Label(main_frame, text="版本 2.1.0",
                  font=(_FONT_FAMILY, 12),
                  foreground="#666666").pack(pady=(0, 10))

        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        desc_text = (
            "个人通讯录管理系统 是一款功能强大的个人通讯录管理系统，\n"
            "为您提供便捷的联系人管理解决方案。\n\n"
            "主要功能：\n"
            "✓ 联系人的添加、修改、删除\n"
            "✓ 常用联系人标记\n"
            "✓ 统一搜索（姓名、拼音、电话、邮箱）\n"
            "✓ 九键拨号搜索（支持中文拼音）\n"
            "✓ 数据导入导出（Excel、TXT、Markdown、JSON）\n"
            "✓ 美观易用的用户界面\n"
            "✓ 数据自动保存\n"
            "✓ 联系人详情快速查看\n"
            "✓ 支持国际电话号码格式\n"
            "✓ 自动根据电话号码识别国家/地区\n\n"
            "开发团队：\n"
            "由东辉，崔鑫涛，杨宇凡小组制作、开发、测试\n"
        )

        desc_text_widget = tk.Text(desc_frame,
                                   font=(_FONT_FAMILY, 10),
                                   foreground="#333333",
                                   wrap=tk.WORD,
                                   yscrollcommand=scrollbar.set,
                                   width=40,
                                   height=10,
                                   borderwidth=0,
                                   bg="#f5f5f5",
                                   padx=0,
                                   pady=0)
        desc_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_text_widget.insert(tk.END, desc_text)
        desc_text_widget.config(state=tk.DISABLED)

        scrollbar.config(command=desc_text_widget.yview)

        ttk.Label(main_frame, text="python期末考核",
                  font=(_FONT_FAMILY, 9),
                  foreground="#999999").pack(pady=(10, 0))

        close_frame = ttk.Frame(main_frame, height=40)
        close_frame.pack(fill=tk.X, pady=(20, 0))
        close_frame.pack_propagate(False)

        ttk.Button(close_frame, text="关闭", command=self.dialog.destroy,
                   style="TButton").pack(side=tk.RIGHT, padx=5)
