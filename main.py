import tkinter as tk
from storage import DataStorage
from contact_manager import ContactManager
from gui.main_window import ContactGUI

if __name__ == "__main__":
    root = tk.Tk()
    
    # 初始化数据存储
    storage = DataStorage()
    
    # 初始化联系人管理器
    manager = ContactManager(storage)
    
    # 创建并启动GUI应用
    app = ContactGUI(root, storage, manager)
    
    # 设置窗口关闭事件处理
    root.protocol("WM_DELETE_WINDOW", lambda: (storage.save_contacts(), root.destroy()))
    
    # 启动主循环
    root.mainloop()
