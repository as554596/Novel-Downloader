from DrissionPage import ChromiumPage, ChromiumOptions
import os
import sys

class BrowserManager:
    _instance = None
    _browser = None

    @classmethod
    def get_browser(cls):
        # 如果瀏覽器已經存在且活著，直接返回
        if cls._browser is not None:
            try:
                if cls._browser.process_id: # 簡單檢查是否還活著
                    return cls._browser
            except:
                cls._browser = None

        cls._browser = cls._init_browser()
        return cls._browser

    @staticmethod
    def _init_browser():
        """初始化瀏覽器配置 (強化版)"""
        co = ChromiumOptions()
        
        # 1. 設定 UserData 路徑 (使用絕對路徑，確保萬無一失)
        # 獲取當前腳本所在的目錄
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        user_data_path = os.path.join(base_path, 'UserData')
        
        # 確保資料夾存在
        if not os.path.exists(user_data_path):
            os.makedirs(user_data_path)
            
        print(f"📂 User Data 存儲路徑: {user_data_path}")

        # 2. 關鍵配置
        co.set_argument(f'--user-data-dir={user_data_path}')
        co.set_argument('--profile-directory=Default') # 強制使用默認配置檔
        
        # 3. 穩定性配置
        # 注意: 不可使用 co.auto_port(True)，開啟後 DrissionPage 會無視上面設定的
        # user-data-dir，改用系統暫存資料夾的臨時路徑，且關閉瀏覽器時會刪除該目錄，
        # 導致登入狀態(cookie)每次都消失。改用固定端口以確保 UserData 路徑生效。
        co.set_local_port(9666)
        co.set_argument('--no-first-run') # 跳過首次運行歡迎頁
        co.set_argument('--no-default-browser-check') # 不檢查默認瀏覽器
        co.set_argument('--disable-infobars') # 隱藏 "Chrome 正在受到控制"
        co.set_argument('--password-store=basic') # 防止跳出密碼儲存提示
        
        # 4. 啟動瀏覽器
        try:
            browser = ChromiumPage(co)
            return browser
        except Exception as e:
            print(f'❌ 瀏覽器啟動失敗: {e}')
            print('嘗試清理殘留進程...')
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
            except: pass
            raise e

    @classmethod
    def close(cls):
        if cls._browser:
            try:
                cls._browser.quit()
            except:
                pass
            cls._browser = None