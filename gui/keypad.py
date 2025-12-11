import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class KeypadSearchPage:
    def __init__(self, parent, manager, refresh_callback, update_detail_callback=None):
        self.parent = parent
        self.manager = manager
        self.refresh_callback = refresh_callback
        self.update_detail_callback = update_detail_callback  # 用于更新主窗口详情
        self.keypad_window = None  # 独立拨号键盘窗口
        self.keypad_input_var = tk.StringVar()  # 九键输入变量
        self.setup_ui()
    
    def setup(self):
        pass
    
    def setup_ui(self):
        """设置九键搜索页面"""
        # 主框架
        keypad_frame = ttk.Frame(self.parent, padding="20 20 20 20")
        keypad_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(keypad_frame, text="九键拨号搜索", 
                               font=("Microsoft YaHei", 14, "bold"), 
                               foreground="#4a90e2")
        title_label.pack(pady=(0, 20))
        
        # 搜索结果提示
        self.keypad_result_var = tk.StringVar(value="请点击下方按钮打开拨号键盘")
        result_label = ttk.Label(keypad_frame, textvariable=self.keypad_result_var, 
                                font=("Microsoft YaHei", 10), 
                                foreground="#666666")
        result_label.pack(pady=(0, 20))
        
        # 添加打开拨号键盘按钮
        keypad_btn_frame = ttk.Frame(keypad_frame)
        keypad_btn_frame.pack(fill=tk.X, pady=20, padx=50)
        open_btn = ttk.Button(keypad_btn_frame, text="打开拨号键盘", command=self.open_keypad_window, 
                           style="TButton")
        open_btn.pack(fill=tk.X, expand=True, ipadx=10, ipady=5)
        
        # 搜索按钮
        search_frame = ttk.Frame(keypad_frame)
        search_frame.pack(fill=tk.X, pady=10, padx=50)
        ttk.Button(search_frame, text="搜索", command=self.keypad_search, width=20).pack(fill=tk.X, expand=True)
        
        # 搜索结果列表 - 增大结果框
        result_frame = ttk.LabelFrame(keypad_frame, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=20, padx=30)  # 减小左右边距，增大显示区域
        
        # 创建Treeview容器，支持水平滚动
        tree_container = ttk.Frame(result_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # 使用Treeview替换Listbox
        self.keypad_result_list = ttk.Treeview(tree_container, 
                                            columns=('status', 'name', 'phone', 'email'),
                                            show='headings',
                                            height=10,
                                            style='Treeview')
        
        # 定义列
        self.keypad_result_list.heading('status', text='状态', anchor='center')
        self.keypad_result_list.heading('name', text='姓名', anchor='center')
        self.keypad_result_list.heading('phone', text='电话', anchor='center')
        self.keypad_result_list.heading('email', text='邮箱', anchor='center')
        
        # 设置列宽，根据实际需要调整
        self.keypad_result_list.column('status', width=60, anchor='center', minwidth=60)
        self.keypad_result_list.column('name', width=120, anchor='center', minwidth=100)
        self.keypad_result_list.column('phone', width=150, anchor='center', minwidth=120)
        self.keypad_result_list.column('email', width=180, anchor='center', minwidth=150)
        
        # 添加垂直滚动条
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, 
                                 command=self.keypad_result_list.yview)
        self.keypad_result_list.configure(yscrollcommand=v_scrollbar.set)
        
        # 添加水平滚动条
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, 
                                 command=self.keypad_result_list.xview)
        self.keypad_result_list.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.keypad_result_list.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 配置容器的网格权重
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # 绑定Treeview事件
        self.keypad_result_list.bind("<<TreeviewSelect>>", self.on_keypad_result_select)
        self.keypad_result_list.bind("<Double-1>", self.on_keypad_result_double_click)
    
    def open_keypad_window(self):
        """打开独立的拨号键盘窗口，包含输入框和九个键"""
        if self.keypad_window and self.keypad_window.winfo_exists():
            # 窗口已存在，前置显示
            self.keypad_window.lift()
            return
        
        # 创建新窗口 - 调整窗口比例
        self.keypad_window = tk.Toplevel(self.parent)
        self.keypad_window.title("九键拨号键盘")
        self.keypad_window.geometry("320x480")  # 调整窗口大小
        self.keypad_window.resizable(False, False)
        self.keypad_window.attributes('-topmost', True)  # 窗口置顶
        
        # 输入显示框
        input_frame = ttk.Frame(self.keypad_window, padding="10")
        input_frame.pack(fill=tk.X, pady=(15, 10))
        
        # 输入框容器
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.X, padx=20, pady=10)
        
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
        
        # 拨号键盘 - 固定大小，调整按键大小
        keypad_grid = ttk.Frame(self.keypad_window, padding="15")
        keypad_grid.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 键盘按钮布局 - 替换*和#为删除和清除按钮
        keypad_buttons = [
            ('1', ''), ('2', 'ABC'), ('3', 'DEF'),
            ('4', 'GHI'), ('5', 'JKL'), ('6', 'MNO'),
            ('7', 'PQRS'), ('8', 'TUV'), ('9', 'WXYZ'),
            ('删除', 'DEL'), ('0', '+'), ('清除', 'CLR')
        ]
        
        # 创建按钮 - 调整按键大小
        for i, (num, letters) in enumerate(keypad_buttons):
            row = i // 3
            col = i % 3
            
            # 配置网格权重 - 确保每行每列大小一致，调整按键大小
            keypad_grid.grid_rowconfigure(row, weight=1, minsize=60)  # 调整按键高度
            keypad_grid.grid_columnconfigure(col, weight=1, minsize=80)  # 调整按键宽度
            
            # 根据按钮类型设置不同的命令和样式
            if num == '删除':
                # 删除按钮
                btn = ttk.Button(keypad_grid, 
                               text=f"{num}\n{letters}", 
                               command=self.keypad_backspace,
                               style="Keypad.TButton",
                               compound="top",
                               padding=10)
            elif num == '清除':
                # 清除按钮
                btn = ttk.Button(keypad_grid, 
                               text=f"{num}\n{letters}", 
                               command=self.keypad_clear,
                               style="Keypad.TButton",
                               compound="top",
                               padding=10)
            elif letters:
                # 对于有字母的按钮，使用多行文本
                button_text = f"{num}\n{letters}"
                btn = ttk.Button(keypad_grid, 
                               text=button_text, 
                               command=lambda n=num: self.keypad_button_click(n),
                               style="Keypad.TButton",
                               compound="top",
                               padding=10)  # 调整按键内边距
            else:
                # 对于没有字母的按钮，只显示数字
                btn = ttk.Button(keypad_grid, 
                               text=num, 
                               command=lambda n=num: self.keypad_button_click(n),
                               style="Keypad.TButton",
                               padding=10)  # 调整按键内边距
            
            # 使用grid布局直接放置按钮
            btn.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
    
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
        # 清空Treeview中的所有项
        for item in self.keypad_result_list.get_children():
            self.keypad_result_list.delete(item)
    
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
            # 清空Treeview
            for item in self.keypad_result_list.get_children():
                self.keypad_result_list.delete(item)
            return
        
        results = self.manager.search_by_keypad(search_term)
        self.keypad_display_results(results, search_term)
    
    def keypad_display_results(self, results, search_term):
        """显示九键搜索结果"""
        # 清空Treeview
        for item in self.keypad_result_list.get_children():
            self.keypad_result_list.delete(item)
        
        if not results:
            self.keypad_result_var.set(f"未找到匹配 '{search_term}' 的联系人")
            return
        
        self.keypad_result_var.set(f"找到 {len(results)} 个匹配的联系人")
        for contact in results:
            status = "常用" if contact.is_frequent else ""
            # 使用格式化后的电话号码显示，但保留原始电话号码用于查找
            formatted_phone = contact.format_phone()
            # 插入Treeview行，同时存储原始电话号码作为iid
            self.keypad_result_list.insert('', tk.END, iid=contact.phone, values=(status, contact.name, formatted_phone, contact.email))
    
    def on_keypad_result_select(self, event):
        """处理九键搜索结果选择，通知主窗口更新详情"""
        selection = self.keypad_result_list.selection()
        if selection:
            # 使用iid作为原始电话号码
            original_phone = selection[0]
            
            # 查找对应的联系人对象
            for contact in self.manager.storage.contacts:
                if contact.phone == original_phone:
                    # 通知主窗口更新详情
                    if self.update_detail_callback:
                        self.update_detail_callback(contact)
                    break
    
    def on_keypad_result_double_click(self, event):
        """处理九键搜索结果双击事件（编辑联系人）"""
        selection = self.keypad_result_list.selection()
        if not selection:
            return
        
        # 使用iid作为原始电话号码
        original_phone = selection[0]
        
        # 查找对应的联系人对象
        for i, contact in enumerate(self.manager.storage.contacts):
            if contact.phone == original_phone:
                from gui.dialogs import EditContactDialog
                EditContactDialog(self.parent.winfo_toplevel(), self.manager, i, contact, self.refresh_callback)
                break
