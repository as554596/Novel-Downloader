# app_gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from extractor_core import ExtractorCore

class ExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('小說提取器 (自動翻頁版)')
        self.root.geometry('600x550')

        # 初始化核心邏輯
        self.core = ExtractorCore(log_callback=self.log)
        
        self.setup_ui()

    def setup_ui(self):
        # --- 頂部操作區 ---
        frame_top = ttk.LabelFrame(self.root, text="操作步驟")
        frame_top.pack(fill="x", padx=10, pady=10)

        # 步驟 1
        btn_browser = ttk.Button(frame_top, text="1. 打開瀏覽器 (首次需登錄，之後自動保存)", command=self.open_browser)
        btn_browser.pack(fill="x", padx=5, pady=5)
        
        lbl_tip = ttk.Label(frame_top, text="提示: 登錄狀態會保存在 UserData 資料夾中，下次無需再登", foreground="gray")
        lbl_tip.pack(anchor="w", padx=5)

        ttk.Separator(frame_top, orient='horizontal').pack(fill='x', pady=5)

        # 步驟 2
        lbl_url = ttk.Label(frame_top, text="2. 登錄後，進入【第一話】閱讀頁，貼上網址:")
        lbl_url.pack(anchor="w", padx=5)
        
        # 網址輸入區塊 (輸入框 + 清空按鈕)
        url_frame = ttk.Frame(frame_top)
        url_frame.pack(fill="x", padx=5, pady=5)
        
        self.entry_url = ttk.Entry(url_frame)
        self.entry_url.pack(side="left", fill="x", expand=True)
        
        # 清空按鈕
        btn_clear = ttk.Button(url_frame, text="清空", command=self.clear_url)
        btn_clear.pack(side="right", padx=(5, 0))

        # 步驟 3
        self.btn_start = ttk.Button(frame_top, text="3. 開始從本話往後提取", command=self.start_download_thread)
        self.btn_start.pack(fill="x", padx=5, pady=10)

        # --- 底部日誌區 ---
        frame_log = ttk.LabelFrame(self.root, text="執行日誌")
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(frame_log, state='disabled', height=15)
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, message):
        """線程安全的日誌輸出"""
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')
        self.root.update_idletasks()

    def clear_url(self):
        """清空輸入框"""
        self.entry_url.delete(0, tk.END)

    def open_browser(self):
        """打開瀏覽器"""
        try:
            self.core.start_browser()
        except Exception as e:
            self.log(f"瀏覽器啟動失敗: {e}")
            messagebox.showerror("錯誤", f"瀏覽器啟動失敗:\n{e}")

    def start_download_thread(self):
        """開啟線程進行下載，避免卡死 GUI"""
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("提示", "請輸入第一話網址！")
            return

        self.btn_start.config(state="disabled")
        thread = threading.Thread(target=self.run_process, args=(url,), daemon=True)
        thread.start()

    def run_process(self, url):
        try:
            self.core.process_download(url)
            messagebox.showinfo("完成", "任務已結束！")
        except Exception as e:
            self.log(f"發生錯誤: {e}")
            # messagebox.showerror("錯誤", f"執行過程中發生錯誤:\n{e}")
        finally:
            self.btn_start.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = ExtractorApp(root)
    root.mainloop()