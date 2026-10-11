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
_BG = "#f5f5f5"       # 界面统一底色，与窗口背景一致
_BRAND = "#4a90e2"    # 品牌色


class ContactGUI:
    """主窗口：联系人列表、详情面板与导入导出入口"""

    def __init__(self, root, storage, manager):
        self.root = root
        self.storage = storage
        self.manager = manager
        self.root.title("EasyLink")

        # 设置窗口初始大小为屏幕的70%，实现自适应
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = int(screen_width * 0.7)
        window_height = int(screen_height * 0.7)
        self.root.geometry(f"{window_width}x{window_height}")

        # 设置最小大小
        self.root.minsize(860, 560)
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

        # ---------------- 统一底色 ----------------
        # ttk 默认的 Frame 背景偏深，与窗口底色 #f5f5f5 拼在一起会出现色块
        self.style.configure("TFrame", background=_BG)
        self.style.configure("TLabelframe", background=_BG)
        self.style.configure("TLabelframe.Label", background=_BG)

        # 品牌标题
        self.style.configure("Brand.TLabel",
                             background=_BG,
                             foreground=_BRAND,
                             font=(_FONT_FAMILY, 15, "bold"))

        # 危险操作（删除）
        self.style.configure("Danger.TButton",
                             background="#e05252",
                             foreground="white",
                             font=(_FONT_FAMILY, 10),
                             padding=6)
        self.style.map("Danger.TButton",
                       background=[("active", "#c62828"), ("disabled", "#d9d9d9")],
                       foreground=[("disabled", "#999999")])

        # 详情面板的字段名与字段值
        self.style.configure("Field.TLabel",
                             background=_BG,
                             foreground="#8a8a8a",
                             font=(_FONT_FAMILY, 10))
        self.style.configure("Value.TLabel",
                             background=_BG,
                             foreground="#222222",
                             font=(_FONT_FAMILY, 10))

        # 次要提示文字
        self.style.configure("Hint.TLabel",
                             background=_BG,
                             foreground="#9e9e9e",
                             font=(_FONT_FAMILY, 9))

        # 底部状态栏
        self.style.configure("Status.TFrame", background="#e8eaed")
        self.style.configure("Status.TLabel",
                             background="#e8eaed",
                             foreground="#546e7a",
                             font=(_FONT_FAMILY, 9))

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="12 10 12 0")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---------------- 顶部工具栏：品牌 + 搜索 ----------------
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(toolbar, text="EasyLink", style="Brand.TLabel").pack(side=tk.LEFT, padx=(0, 15))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        search_entry.bind("<Return>", self.unified_search)

        ttk.Button(toolbar, text="搜索", command=self.unified_search, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="重置", command=self.reset_search, width=8).pack(side=tk.LEFT, padx=2)

        # ---------------- 底部状态栏 ----------------
        # 先于内容区 pack，确保窗口变小时状态栏仍能贴在底部而不被挤掉
        status_bar = ttk.Frame(main_frame, style="Status.TFrame", padding="10 6 10 6")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_bar, textvariable=self.status_var,
                  style="Status.TLabel").pack(side=tk.LEFT)

        ttk.Button(status_bar, text="关于", command=self.about_dialog,
                   width=6).pack(side=tk.RIGHT)

        # ---------------- 内容区 ----------------
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 用 grid 划分左右两列：左列随窗口伸缩，右列固定 320px。
        # 若改用 pack，窄窗口下先 pack 的一侧会把另一侧挤到只剩几十像素。
        content_frame.rowconfigure(0, weight=1)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=0, minsize=320)

        # 左侧：列表操作条 + 标签页
        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        list_toolbar = ttk.Frame(left_frame)
        list_toolbar.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(list_toolbar, text="添加联系人", command=self.add_contact,
                   width=11).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(list_toolbar, text="修改", command=self.edit_contact,
                   width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(list_toolbar, text="删除", command=self.delete_contact,
                   width=8, style="Danger.TButton").pack(side=tk.LEFT, padx=4)

        ttk.Label(list_toolbar, text="双击列表行可快速编辑",
                  style="Hint.TLabel").pack(side=tk.RIGHT, padx=4)

        tab_control = ttk.Notebook(left_frame)
        self.all_contacts_tab = ttk.Frame(tab_control)
        self.frequent_contacts_tab = ttk.Frame(tab_control)
        self.keypad_search_tab = ttk.Frame(tab_control)

        tab_control.add(self.all_contacts_tab, text="全部联系人")
        tab_control.add(self.frequent_contacts_tab, text="常用联系人")
        tab_control.add(self.keypad_search_tab, text="九键搜索")
        tab_control.pack(fill=tk.BOTH, expand=True)
        tab_control.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.contact_list = self._create_treeview(self.all_contacts_tab)
        self.frequent_list = self._create_treeview(self.frequent_contacts_tab)

        # 右侧：详情 + 导入导出。固定宽度，不随窗口拉伸而变宽
        right_frame = ttk.Frame(content_frame, width=320)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_propagate(False)

        detail_frame = ttk.LabelFrame(right_frame, text=" 联系人详情 ", padding="12 8 12 12")
        detail_frame.pack(fill=tk.X, pady=(0, 10))

        self.name_var = self._add_detail_row(detail_frame, "姓名")
        self.phone_var = self._add_detail_row(detail_frame, "电话")
        self.country_var = self._add_detail_row(detail_frame, "国家/地区")
        self.email_var = self._add_detail_row(detail_frame, "邮箱")
        self.remark_var = self._add_detail_row(detail_frame, "备注")

        ttk.Button(detail_frame, text="切换常用标记",
                   command=self.toggle_frequent).pack(fill=tk.X, pady=(12, 0))

        io_frame = ttk.LabelFrame(right_frame, text=" 数据导入 / 导出 ", padding="12 8 12 12")
        io_frame.pack(fill=tk.X)

        ttk.Button(io_frame, text="导入数据",
                   command=self.import_data).pack(fill=tk.X, pady=(0, 6))

        export_grid = ttk.Frame(io_frame)
        export_grid.pack(fill=tk.X)
        export_grid.columnconfigure(0, weight=1)
        export_grid.columnconfigure(1, weight=1)

        ttk.Button(export_grid, text="导出 Excel", command=self.export_excel).grid(
            row=0, column=0, sticky="ew", padx=(0, 3), pady=3)
        ttk.Button(export_grid, text="导出 TXT", command=self.export_txt).grid(
            row=0, column=1, sticky="ew", padx=(3, 0), pady=3)
        ttk.Button(export_grid, text="导出 Markdown", command=self.export_md).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=3)

        # 九键搜索页面
        self.keypad_page = KeypadSearchPage(
            self.keypad_search_tab, self.manager, self.refresh_contact_list, self.on_keypad_contact_select
        )

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

    def _add_detail_row(self, parent, label):
        """在详情面板中追加一行字段，返回用于显示值的 StringVar

        用 Label 而非 disabled Entry：这些字段本就不可编辑，
        输入框外观会让人误以为可以点进去修改。
        """
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=3)

        ttk.Label(row, text=label, width=10, anchor="w",
                  style="Field.TLabel").pack(side=tk.LEFT, padx=(0, 5))

        var = tk.StringVar(value="")
        ttk.Label(row, textvariable=var, anchor="w", style="Value.TLabel",
                  wraplength=200, justify="left").pack(side=tk.LEFT, fill=tk.X, expand=True)
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
    # 状态栏
    # ------------------------------------------------------------------
    def _update_status(self, shown: Optional[int] = None) -> None:
        """刷新底部状态栏

        Args:
            shown: 当前列表实际展示的条数；为 None 表示展示的就是完整数据
        """
        total = self.manager.get_contacts_count()
        frequent = len(self.manager.get_frequent_contacts())

        if shown is None:
            self.status_var.set(f"共 {total} 位联系人 · 常用 {frequent} 位")
        else:
            self.status_var.set(f"找到 {shown} 位 · 共 {total} 位联系人")

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
        self._update_status()

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
        self._update_status(shown=len(results))

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
        self.dialog.title("关于 EasyLink")
        self.dialog.configure(bg=_BG)

        dialog_width = 400
        dialog_height = 430

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
        main_frame = ttk.Frame(self.dialog, padding="28 24 28 20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="EasyLink",
                  style="Brand.TLabel").pack(anchor="center")

        ttk.Label(main_frame, text="版本 2.2.0",
                  style="Hint.TLabel").pack(anchor="center", pady=(2, 16))

        ttk.Label(main_frame, text="轻量、离线的桌面通讯录管理工具",
                  font=(_FONT_FAMILY, 10),
                  foreground="#555555").pack(anchor="center", pady=(0, 16))

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 14))

        feature_frame = ttk.Frame(main_frame)
        feature_frame.pack(fill=tk.X)

        for item in (
            "联系人的添加、修改、删除与常用标记",
            "统一搜索：姓名 / 拼音 / 电话 / 邮箱 / 九键编码",
            "九键拨号搜索，支持中文姓名的拼音匹配",
            "数据导入导出：Excel / TXT / Markdown / JSON",
            "SQLite 本地存储，修改即时落盘",
            "自动识别国际区号与国家/地区",
        ):
            row = ttk.Frame(feature_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text="•", foreground=_BRAND,
                      font=(_FONT_FAMILY, 10)).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Label(row, text=item, style="Value.TLabel").pack(side=tk.LEFT)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=14)

        ttk.Label(main_frame, text="基于 MIT License 开源",
                  style="Hint.TLabel").pack(anchor="center")

        ttk.Button(main_frame, text="关闭", command=self.dialog.destroy,
                   width=10).pack(anchor="center", pady=(16, 0))
