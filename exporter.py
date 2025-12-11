from openpyxl import Workbook
from tkinter import messagebox
from typing import List, Optional
import logging
from contact import Contact

# 配置日志
logger = logging.getLogger(__name__)

class ExcelExporter:
    @staticmethod
    def export_to_excel(contacts: List[Contact], file_path: str = "contacts.xlsx") -> bool:
        """导出联系人为Excel文件"""
        if not isinstance(contacts, list):
            messagebox.showerror("错误", "联系人列表必须是列表类型")
            return False
        
        if not isinstance(file_path, str):
            messagebox.showerror("错误", "文件路径必须是字符串")
            return False
        
        if not contacts:
            messagebox.showwarning("警告", "没有联系人可以导出")
            return False
        
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "联系人列表"

            headers = ["姓名", "电话", "邮箱", "国家/地区", "备注", "常用联系人"]
            ws.append(headers)

            for contact in contacts:
                if not isinstance(contact, Contact):
                    logger.warning(f"Skipping invalid contact: {contact}")
                    continue
                    
                ws.append([
                    contact.name,
                    contact.phone,
                    contact.email,
                    contact.country,
                    contact.remark,
                    "是" if contact.is_frequent else "否"
                ])

            wb.save(file_path)
            messagebox.showinfo("成功", f"联系人已导出到 {file_path}")
            logger.info(f"Successfully exported {len(contacts)} contacts to Excel: {file_path}")
            return True
        except PermissionError as e:
            error_msg = f"没有写入权限: {file_path}"
            messagebox.showerror("错误", error_msg)
            logger.error(f"Permission denied when exporting to Excel: {e}")
            return False
        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(f"Failed to export to Excel: {e}", exc_info=True)
            return False

class TXTExporter:
    @staticmethod
    def export_to_txt(contacts: List[Contact], file_path: str = "contacts.txt") -> bool:
        """导出联系人为TXT文件"""
        if not isinstance(contacts, list):
            messagebox.showerror("错误", "联系人列表必须是列表类型")
            return False
        
        if not isinstance(file_path, str):
            messagebox.showerror("错误", "文件路径必须是字符串")
            return False
        
        if not contacts:
            messagebox.showwarning("警告", "没有联系人可以导出")
            return False
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("个人通讯录\n")
                f.write("=" * 50 + "\n\n")
                
                for i, contact in enumerate(contacts, 1):
                    if not isinstance(contact, Contact):
                        logger.warning(f"Skipping invalid contact: {contact}")
                        continue
                        
                    f.write(f"联系人 {i}:\n")
                    f.write(f"姓名: {contact.name}\n")
                    f.write(f"电话: {contact.phone}\n")
                    f.write(f"邮箱: {contact.email}\n")
                    f.write(f"国家/地区: {contact.country}\n")
                    f.write(f"备注: {contact.remark}\n")
                    f.write(f"常用联系人: {'是' if contact.is_frequent else '否'}\n")
                    f.write("-" * 50 + "\n\n")
            
            messagebox.showinfo("成功", f"联系人已导出到 {file_path}")
            logger.info(f"Successfully exported {len(contacts)} contacts to TXT: {file_path}")
            return True
        except PermissionError as e:
            error_msg = f"没有写入权限: {file_path}"
            messagebox.showerror("错误", error_msg)
            logger.error(f"Permission denied when exporting to TXT: {e}")
            return False
        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(f"Failed to export to TXT: {e}", exc_info=True)
            return False

class MDExporter:
    @staticmethod
    def export_to_md(contacts: List[Contact], file_path: str = "contacts.md") -> bool:
        """导出联系人为Markdown文件"""
        if not isinstance(contacts, list):
            messagebox.showerror("错误", "联系人列表必须是列表类型")
            return False
        
        if not isinstance(file_path, str):
            messagebox.showerror("错误", "文件路径必须是字符串")
            return False
        
        if not contacts:
            messagebox.showwarning("警告", "没有联系人可以导出")
            return False
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("# 个人通讯录\n\n")
                f.write("| 姓名 | 电话 | 邮箱 | 国家/地区 | 备注 | 常用联系人 |\n")
                f.write("|------|------|------|------------|------|------------|\n")
                
                for contact in contacts:
                    if not isinstance(contact, Contact):
                        logger.warning(f"Skipping invalid contact: {contact}")
                        continue
                        
                    f.write(f"| {contact.name} | {contact.phone} | {contact.email} | {contact.country} | {contact.remark} | {'是' if contact.is_frequent else '否'} |\n")
            
            messagebox.showinfo("成功", f"联系人已导出到 {file_path}")
            logger.info(f"Successfully exported {len(contacts)} contacts to Markdown: {file_path}")
            return True
        except PermissionError as e:
            error_msg = f"没有写入权限: {file_path}"
            messagebox.showerror("错误", error_msg)
            logger.error(f"Permission denied when exporting to Markdown: {e}")
            return False
        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(f"Failed to export to Markdown: {e}", exc_info=True)
            return False
