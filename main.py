#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人管理系统主程序入口

该程序是一个基于 Tkinter 的个人通讯录管理系统，支持联系人的添加、修改、删除、搜索等功能，
以及数据的导入导出。

主要功能：
1. 联系人的增删改查
2. 常用联系人标记
3. 统一搜索（姓名、电话、邮箱、九键搜索）
4. 数据导入导出（Excel、TXT、Markdown、JSON）
5. SQLite 数据库存储，首次运行自动从 contacts.json 迁移

运行：
    python main.py
"""

import logging
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from contact_manager import ContactManager
from gui.main_window import ContactGUI
from storage import DataStorage, SQLiteStorage

# 数据文件固定放在脚本所在目录。
# 若使用相对路径，从其它工作目录（如快捷方式、任务计划）启动时会读写到别处，
# 用户会看到"通讯录空了"。
BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / "contacts.json"
DB_FILE = BASE_DIR / "contacts.db"
LOG_FILE = BASE_DIR / "easylink.log"

logger = logging.getLogger("easylink")


def setup_logging() -> None:
    """配置日志：同时输出到控制台与日志文件

    日志配置是程序入口的职责；库模块只获取 logger，不调用 basicConfig，
    以免覆盖宿主应用的日志设置。打包为无控制台的 exe 后，日志文件是唯一线索。
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    except OSError as e:
        logger.warning("无法创建日志文件 %s，日志仅输出到控制台: %s", LOG_FILE, e)
    else:
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def migrate_data_from_json_to_sqlite() -> None:
    """首次运行时把 contacts.json 的数据迁移到 SQLite 数据库

    触发条件为「JSON 有数据」且「数据库尚无数据」。
    逐条迁移并对失败条目计数：单条脏数据不应该导致整批联系人都迁移不过去。
    """
    if not JSON_FILE.exists():
        logger.info("未找到 %s，跳过数据迁移", JSON_FILE)
        return

    try:
        json_storage = DataStorage(str(JSON_FILE))
    except Exception as e:
        logger.error("读取 %s 失败，跳过数据迁移: %s", JSON_FILE, e, exc_info=True)
        return

    if not json_storage.contacts:
        logger.info("%s 中没有可迁移的联系人", JSON_FILE)
        return

    try:
        sqlite_storage = SQLiteStorage(str(DB_FILE))
    except Exception as e:
        logger.error("打开数据库 %s 失败: %s", DB_FILE, e, exc_info=True)
        return

    if sqlite_storage.contacts:
        logger.info("数据库已有 %d 条联系人，无需迁移", len(sqlite_storage.contacts))
        return

    logger.info("正在从 %s 迁移数据到 %s", JSON_FILE, DB_FILE)
    migrated, failed = 0, 0
    for contact in json_storage.contacts:
        try:
            sqlite_storage.add_contact(contact)
            migrated += 1
        except Exception as e:
            failed += 1
            logger.warning("迁移联系人 %s (%s) 失败: %s", contact.name, contact.phone, e)

    logger.info("数据迁移完成: 成功 %d 条，失败 %d 条", migrated, failed)


def _show_startup_error(message: str) -> None:
    """启动阶段失败时尽力告知用户（此时主窗口尚不可用）"""
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("启动失败", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def main() -> int:
    """程序入口

    Returns:
        int: 进程退出码，0 表示正常退出
    """
    setup_logging()

    # 统一工作目录到脚本所在目录：导入/导出的默认文件名都是相对路径，
    # 若从其它目录启动，导出产物会散落到意想不到的位置。
    try:
        os.chdir(BASE_DIR)
    except OSError as e:
        logger.warning("切换工作目录到 %s 失败: %s", BASE_DIR, e)

    logger.info("EasyLink 启动，工作目录: %s", BASE_DIR)

    migrate_data_from_json_to_sqlite()

    try:
        storage = SQLiteStorage(str(DB_FILE))
    except Exception as e:
        logger.critical("初始化数据库失败: %s", e, exc_info=True)
        _show_startup_error(f"无法打开联系人数据库:\n{DB_FILE}\n\n{e}")
        return 1

    manager = ContactManager(storage)

    root = tk.Tk()
    # 保持实例引用，避免主窗口对象被回收后回调失效
    app = ContactGUI(root, storage, manager)  # noqa: F841

    def on_close() -> None:
        """关闭窗口时的收尾

        SQLite 存储的每次增删改都已即时提交，这里不再做整表重写：
        整表重写会重排自增 id，并可能把内存中不一致的状态固化回数据库。
        """
        logger.info("程序退出，当前共 %d 条联系人", len(storage.contacts))
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
