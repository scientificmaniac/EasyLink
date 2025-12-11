import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from contact import Contact
from validator import Validator
from exporter import ExcelExporter, TXTExporter, MDExporter
from importer import DataImporter
from gui.dialogs import AddContactDialog, EditContactDialog
from gui.keypad import KeypadSearchPage

class ContactGUI:
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
                           font=("Microsoft YaHei", 12),  # 增大字体
                           selectbackground="#e6f2ff",
                           selectforeground="#000000")
        
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

    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="EasyLink", 
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

        # 中间内容区 - 确保不会挤压底部的帮助按钮
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))  # 增加底部边距，确保帮助按钮有足够空间

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

        # 联系人列表 - 全部联系人（使用Treeview）
        list_frame1 = ttk.Frame(self.all_contacts_tab)
        list_frame1.pack(fill=tk.BOTH, expand=True)

        # 创建Treeview组件
        self.contact_list = ttk.Treeview(list_frame1, 
                                       columns=('status', 'name', 'phone', 'email'),
                                       show='headings',
                                       height=20,
                                       style='Treeview')
        
        # 定义列
        self.contact_list.heading('status', text='状态', anchor='center')
        self.contact_list.heading('name', text='姓名', anchor='center')
        self.contact_list.heading('phone', text='电话', anchor='center')
        self.contact_list.heading('email', text='邮箱', anchor='center')
        
        # 设置列宽
        self.contact_list.column('status', width=60, anchor='center')
        self.contact_list.column('name', width=150, anchor='center')
        self.contact_list.column('phone', width=180, anchor='center')
        self.contact_list.column('email', width=220, anchor='center')
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame1, orient=tk.VERTICAL, command=self.contact_list.yview)
        self.contact_list.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.contact_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 绑定事件
        self.contact_list.bind("<<TreeviewSelect>>", self.on_treeview_select)
        self.contact_list.bind("<Double-1>", self.edit_contact)

        # 常用联系人列表（使用Treeview）
        list_frame2 = ttk.Frame(self.frequent_contacts_tab)
        list_frame2.pack(fill=tk.BOTH, expand=True)
        
        # 为常用联系人标签页添加相同的Treeview
        self.frequent_list = ttk.Treeview(list_frame2, 
                                        columns=('status', 'name', 'phone', 'email'),
                                        show='headings',
                                        height=20,
                                        style='Treeview')
        
        # 定义列
        self.frequent_list.heading('status', text='状态', anchor='center')
        self.frequent_list.heading('name', text='姓名', anchor='center')
        self.frequent_list.heading('phone', text='电话', anchor='center')
        self.frequent_list.heading('email', text='邮箱', anchor='center')
        
        # 设置列宽
        self.frequent_list.column('status', width=60, anchor='center')
        self.frequent_list.column('name', width=150, anchor='center')
        self.frequent_list.column('phone', width=180, anchor='center')
        self.frequent_list.column('email', width=220, anchor='center')
        
        # 添加滚动条
        scrollbar2 = ttk.Scrollbar(list_frame2, orient=tk.VERTICAL, command=self.frequent_list.yview)
        self.frequent_list.configure(yscrollcommand=scrollbar2.set)
        
        # 布局
        self.frequent_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 绑定事件
        self.frequent_list.bind("<<TreeviewSelect>>", self.on_treeview_select)
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
        self.keypad_page = KeypadSearchPage(self.keypad_search_tab, self.manager, self.refresh_contact_list, self.on_keypad_contact_select)
        self.keypad_page.setup()
        
        # 添加菜单
        self.setup_menu()
        
        # 添加帮助按钮到主界面右下角 - 确保不会被压缩
        # 使用更可靠的布局方式
        help_frame = ttk.Frame(main_frame)
        # 确保help_frame不会被压缩
        help_frame.pack(side=tk.BOTTOM, anchor=tk.SE, pady=10, padx=10)
        
        # 为按钮创建一个容器，确保按钮大小固定
        btn_container = ttk.Frame(help_frame)
        btn_container.pack(side=tk.RIGHT, fill=tk.NONE, expand=False)
        
        # 创建按钮，不使用height参数（ttk.Button不支持）
        help_btn = ttk.Button(btn_container, text="?", 
                            command=self.about_dialog, 
                            width=3, 
                            style="TButton")
        help_btn.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.NONE, expand=False)

    def on_tab_changed(self, event):
        tab_control = event.widget
        current_tab = tab_control.tab(tab_control.select(), "text")
        self.current_tab = current_tab
        self.refresh_contact_list()

    def refresh_contact_list(self):
        # 确定当前使用的Treeview
        if self.current_tab == "全部联系人":
            current_tree = self.contact_list
            self.current_contacts = self.manager.get_all_contacts()
        elif self.current_tab == "常用联系人":
            current_tree = self.frequent_list
            self.current_contacts = self.manager.get_frequent_contacts()
        else:
            # 九键搜索标签页，不更新列表
            return

        # 清空并更新Treeview
        for item in current_tree.get_children():
            current_tree.delete(item)
        
        for contact in self.current_contacts:
            status = "常用" if contact.is_frequent else ""
            # 使用格式化后的电话号码
            formatted_phone = contact.format_phone()
            # 插入Treeview行
            current_tree.insert('', tk.END, values=(status, contact.name, formatted_phone, contact.email))

    def on_treeview_select(self, event):
        # 获取触发事件的Treeview
        if event is None:
            # 当event为None时，获取当前标签页对应的Treeview
            if self.current_tab == "全部联系人":
                widget = self.contact_list
            elif self.current_tab == "常用联系人":
                widget = self.frequent_list
            else:
                return
        else:
            widget = event.widget
        
        selection = widget.selection()
        if selection:
            item_id = selection[0]
            # 获取选中行的值
            values = widget.item(item_id, 'values')
            if values:
                # 查找对应的联系人对象
                formatted_phone = values[2]
                # 从格式化的电话号码中提取原始电话号码（去掉前缀和空格）
                original_phone = formatted_phone.replace('+86 ', '').replace('+', '')
                for contact in self.current_contacts:
                    if contact.phone.replace('+86', '').replace('+', '') == original_phone:
                        # 显示联系人详情
                        self.name_var.set(contact.name)
                        self.phone_var.set(contact.phone)
                        self.email_var.set(contact.email)
                        self.remark_var.set(contact.remark)
                        self.country_var.set(contact.country)
                        # 更新当前选中的联系人
                        self.selected_contact = contact
                        break
    
    def on_contact_select(self, event):
        # 兼容旧的Listbox选择事件，实际使用on_treeview_select
        pass
    
    def on_keypad_contact_select(self, contact):
        """处理九键搜索结果选择，更新联系人详情"""
        if contact:
            self.name_var.set(contact.name)
            self.phone_var.set(contact.phone)
            self.email_var.set(contact.email)
            self.remark_var.set(contact.remark)
            self.country_var.set(contact.country)
            # 更新当前选中的联系人
            self.selected_contact = contact

    def add_contact(self):
        AddContactDialog(self.root, self.manager, self.refresh_contact_list)

    def edit_contact(self, event=None):
        # 确定当前使用的控件
        if self.current_tab == "全部联系人" or self.current_tab == "常用联系人":
            # Treeview控件
            current_tree = self.contact_list if self.current_tab == "全部联系人" else self.frequent_list
            selection = current_tree.selection()
            
            if not selection:
                messagebox.showwarning("警告", "请先选择一个联系人")
                return
            
            item_id = selection[0]
            values = current_tree.item(item_id, 'values')
            if values:
                formatted_phone = values[2]
                # 从格式化的电话号码中提取原始电话号码
                # 移除国家代码和空格
                original_phone = formatted_phone.replace('+86 ', '').replace('+', '').replace(' ', '')
                
                # 查找对应的联系人对象
                for i, contact in enumerate(self.storage.contacts):
                    # 比较时也移除国家代码和空格
                    contact_phone_clean = contact.phone.replace('+86', '').replace('+', '').replace(' ', '')
                    if contact_phone_clean == original_phone:
                        EditContactDialog(self.root, self.manager, i, contact, self.refresh_contact_list)
                        break
        else:
            # 九键搜索标签页，使用九键结果Treeview
            current_tree = self.keypad_page.keypad_result_list
            selection = current_tree.selection()
            
            if not selection:
                messagebox.showwarning("警告", "请先选择一个联系人")
                return
            
            # 使用iid作为原始电话号码
            original_phone = selection[0]
            
            # 查找对应的联系人对象
            for i, contact in enumerate(self.storage.contacts):
                if contact.phone == original_phone:
                    EditContactDialog(self.root, self.manager, i, contact, self.refresh_contact_list)
                    break

    def delete_contact(self):
        # 确定当前使用的Treeview
        if self.current_tab == "全部联系人" or self.current_tab == "常用联系人":
            current_tree = self.contact_list if self.current_tab == "全部联系人" else self.frequent_list
            selection = current_tree.selection()
            
            if not selection:
                messagebox.showwarning("警告", "请先选择一个联系人")
                return
            
            item_id = selection[0]
            values = current_tree.item(item_id, 'values')
            if values:
                formatted_phone = values[2]
                # 从格式化的电话号码中提取原始电话号码
                original_phone = formatted_phone.replace('+86 ', '').replace('+', '').replace(' ', '')
                
                # 查找对应的联系人对象
                for contact in self.current_contacts:
                    contact_phone_clean = contact.phone.replace('+86', '').replace('+', '').replace(' ', '')
                    if contact_phone_clean == original_phone:
                        if messagebox.askyesno("确认", f"确定要删除联系人 {contact.name} 吗?"):
                            original_index = self.storage.contacts.index(contact)
                            success, msg = self.manager.delete_contact(original_index)
                            if success:
                                self.refresh_contact_list()
                                self.clear_detail()
                            else:
                                messagebox.showerror("错误", msg)
                        break
        else:
            # 九键搜索标签页，不支持直接删除
            messagebox.showinfo("提示", "请在全部联系人或常用联系人标签页中进行删除操作")
            return

    def toggle_frequent(self):
        # 确定当前使用的Treeview
        if self.current_tab == "全部联系人" or self.current_tab == "常用联系人":
            current_tree = self.contact_list if self.current_tab == "全部联系人" else self.frequent_list
            selection = current_tree.selection()
            
            if not selection:
                messagebox.showwarning("警告", "请先选择一个联系人")
                return
            
            item_id = selection[0]
            values = current_tree.item(item_id, 'values')
            if values:
                formatted_phone = values[2]
                # 从格式化的电话号码中提取原始电话号码
                original_phone = formatted_phone.replace('+86 ', '').replace('+', '').replace(' ', '')
                
                # 查找对应的联系人对象
                for contact in self.current_contacts:
                    contact_phone_clean = contact.phone.replace('+86', '').replace('+', '').replace(' ', '')
                    if contact_phone_clean == original_phone:
                        original_index = self.storage.contacts.index(contact)
                        contact.is_frequent = not contact.is_frequent
                        success, msg = self.manager.update_contact(original_index, contact)
                        if success:
                            self.refresh_contact_list()
                            # 重新选择联系人以更新详情
                            self.on_treeview_select(None)
                        else:
                            messagebox.showerror("错误", msg)
                        break
        else:
            # 九键搜索标签页，不支持直接标记
            messagebox.showinfo("提示", "请在全部联系人或常用联系人标签页中进行标记操作")
            return

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

    def show_search_results(self, results):
        # 根据当前标签页选择对应的Treeview
        if self.current_tab == "全部联系人":
            current_tree = self.contact_list
        elif self.current_tab == "常用联系人":
            current_tree = self.frequent_list
        else:
            # 九键搜索标签页，不更新列表
            return
        
        # 清空Treeview
        for item in current_tree.get_children():
            current_tree.delete(item)
        
        self.current_contacts = results
        for contact in results:
            status = "常用" if contact.is_frequent else ""
            # 使用格式化后的电话号码
            formatted_phone = contact.format_phone()
            # 插入Treeview行
            current_tree.insert('', tk.END, values=(status, contact.name, formatted_phone, contact.email))

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
    
    def import_data(self):
        """数据导入功能"""
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择要导入的文件",
            filetypes=[
                ("所有支持的文件", "*.xlsx *.txt *.md *.json"),
                ("Excel文件", "*.xlsx"),
                ("文本文件", "*.txt"),
                ("Markdown文件", "*.md"),
                ("JSON文件", "*.json")
            ]
        )
        
        if file_path:
            # 调用导入功能
            success = DataImporter.import_contacts(file_path, self.manager)
            if success:
                # 刷新联系人列表
                self.refresh_contact_list()
                self.clear_detail()
    
    def setup_menu(self):
        """设置菜单 - 暂时不使用菜单，改为在主界面添加按钮"""
        pass
    
    def about_dialog(self):
        """显示关于对话框"""
        AboutDialog(self.root)

class AboutDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("关于EasyLink")
        
        # 设置窗口大小和位置
        dialog_width = 400
        dialog_height = 300
        
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
        except Exception:
            # 如果获取父窗口位置失败，使用默认居中位置
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+50+50")
        
        # 设置窗口属性
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self):
        """设置关于对话框UI"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="EasyLink", 
                               font=("Microsoft YaHei", 18, "bold"), 
                               foreground="#4a90e2")
        title_label.pack(pady=(0, 15))
        
        # 版本信息
        version_label = ttk.Label(main_frame, text="版本 1.0.0", 
                                font=("Microsoft YaHei", 12), 
                                foreground="#666666")
        version_label.pack(pady=(0, 10))
        
        # 功能描述 - 添加滚动条
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本组件
        desc_text = "EasyLink 是一款功能强大的个人通讯录管理系统，\n" \
                   "为您提供便捷的联系人管理解决方案。\n\n" \
                   "主要功能：\n" \
                   "✓ 联系人的添加、修改、删除\n" \
                   "✓ 常用联系人标记\n" \
                   "✓ 多种方式搜索联系人（姓名、电话、邮箱）\n" \
                   "✓ 九键拨号搜索\n" \
                   "✓ 数据导入导出（Excel、TXT、Markdown、JSON）\n" \
                   "✓ 美观易用的用户界面\n" \
                   "✓ 数据自动保存\n" \
                   "✓ 联系人详情快速查看\n" \
                   "✓ 支持国际电话号码格式\n" \
                   "✓ 自动根据电话号码识别国家/地区\n"
        
        # 创建Text组件并绑定滚动条
        desc_text_widget = tk.Text(desc_frame, 
                                 font=("Microsoft YaHei", 10), 
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
        
        # 插入文本
        desc_text_widget.insert(tk.END, desc_text)
        
        # 设置为只读
        desc_text_widget.config(state=tk.DISABLED)
        
        # 绑定滚动条
        scrollbar.config(command=desc_text_widget.yview)
        
        # 版权信息
        copyright_label = ttk.Label(main_frame, text="© 2025 EasyLink. All rights reserved.", 
                                 font=("Microsoft YaHei", 9), 
                                 foreground="#999999")
        copyright_label.pack(pady=(10, 0))
        
        # 关闭按钮
        close_frame = ttk.Frame(main_frame)
        close_frame.pack(fill=tk.X, pady=(20, 0))
        
        close_btn = ttk.Button(close_frame, text="关闭", command=self.dialog.destroy, 
                             style="TButton")
        close_btn.pack(side=tk.RIGHT, padx=5)
        
        # 居中对齐关闭按钮
        close_frame.pack_propagate(False)
        close_frame.config(height=40)
