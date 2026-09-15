from DrissionPage import ChromiumPage
import time

class CloudflareBypasser:
    """
    Handles Cloudflare Turnstile and other basic checks using DrissionPage.
    """
    def __init__(self, page: ChromiumPage):
        self.page = page

    def is_cloudflare_active(self) -> bool:
        """
        Checks if the current page is a Cloudflare challenge page.
        """
        try:
            title = self.page.title.lower()
        except:
            return False

        if 'just a moment' in title or 'security check' in title or 'attention required' in title:
            return True
        
        # 檢查是否有 turnstile iframe
        if self.page.ele('xpath://iframe[contains(@src, "turnstile")]'):
            return True
        
        # 檢查是否有 challenge stage
        if self.page.ele('#challenge-stage'):
            return True
            
        return False

    def bypass(self):
        """
        Attempts to bypass Cloudflare protection.
        """
        print('Cloudflare detection: Checking...')
        max_retries = 10
        
        for i in range(max_retries):
            if not self.is_cloudflare_active():
                print('Cloudflare not detected or passed.')
                return True
            
            print(f'Cloudflare detected. Attempt {i + 1}/{max_retries}...')
            
            # 嘗試尋找 turnstile 框架
            turnstile = self.page.ele('xpath://iframe[contains(@src, "turnstile")]')
            if turnstile:
                print('Found Turnstile iframe.')

            # 方法 1: 嘗試點擊常見的 checkbox 元素
            try:
                cb = self.page.ele('.chk-box') or \
                     self.page.ele('#turnstile-wrapper') or \
                     self.page.ele('input[type="checkbox"]')
                if cb:
                    cb.click()
                    time.sleep(2)
            except:
                pass

            # 方法 2: 如果有 iframe，嘗試直接點擊 iframe 的中心點 (暴力解法)
            if turnstile:
                try:
                    rect = turnstile.rect
                    x, y = rect.midpoint
                    self.page.actions.move_to(x, y).click()
                    time.sleep(1)
                except:
                    pass
            
            time.sleep(3)
            
        return not self.is_cloudflare_active()