import time
import os
import zipfile
import re
import uuid
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
from browser_manager import BrowserManager

class ExtractorCore:
    def __init__(self, log_callback=print):
        self.log = log_callback
        self.browser_manager = BrowserManager()
        self.browser = None

    def start_browser(self):
        """啟動瀏覽器"""
        self.log('正在啟動瀏覽器...')
        self.browser = self.browser_manager.get_browser()
        self.browser.get("https://www.bomtoon.com/login")
        self.log('瀏覽器已啟動。')
        self.log('1. 請在瀏覽器中【手動登錄】。')
        self.log('2. 登錄成功後，進入小說【第一話】。')
        self.log('3. 複製網址，貼回本程式開始。')
        return self.browser

    def process_download(self, url):
        """GUI 入口函數"""
        self.extract_current_chapter_and_next(url)

    def extract_current_chapter_and_next(self, start_url):
        """主邏輯"""
        if not self.browser:
            self.start_browser()
        
        self.log(f'正在前往第一話: {start_url}')
        self.browser.get(start_url)
        time.sleep(3)

        try:
            full_title = self.browser.title
            novel_title = full_title.split('-')[0].strip()
        except:
            novel_title = "Untitled_Novel"
        
        self.log(f'識別小說標題: {novel_title}')

        chapters_data = []
        current_index = 1
        
        # --- 循環抓取每一話 ---
        while True:
            try:
                chapter_title = self.browser.title.split('-')[1].strip()
            except:
                chapter_title = f"Chapter {current_index}"

            self.log(f'[{current_index}] 正在處理: {chapter_title}')
            
            # 完結檢測
            is_last_chapter = False
            if "최종화" in chapter_title or "완결" in chapter_title:
                is_last_chapter = True
                self.log(f'   🏁 檢測到完結關鍵字。')

            # 提取內容
            content, css = self._scrape_content_raw()
            
            if content:
                # 1. 深度清洗 HTML
                clean_content = self._deep_clean_html(content)
                
                # 2. 優化 CSS
                clean_css = self._optimize_css(css)
                
                chapters_data.append({
                    'index': current_index,
                    'title': chapter_title,
                    'content': clean_content,
                    'css': clean_css
                })
                self.log(f'   ✅ 提取並清洗成功')
            else:
                self.log(f'   ⚠️ 內容提取失敗，停止下載。')
                break

            if is_last_chapter:
                self.log('   🎉 已完成最終話。')
                break

            # 翻頁
            if not self._go_next_page():
                break
            
            current_index += 1

        # --- 打包 ---
        if chapters_data:
            self.create_apple_epub(novel_title, chapters_data)
        else:
            self.log('❌ 沒有下載到任何有效數據。')

    def _scrape_content_raw(self):
        """從瀏覽器提取原始數據"""
        try:
            # DrissionPage 新版語法修正
            iframe = self.browser.ele('#epub-viewer', timeout=10)
            if not iframe:
                cover_btn = self.browser.ele('.viewer-cover', timeout=2)
                if cover_btn:
                    cover_btn.click()
                    time.sleep(1)
                    iframe = self.browser.ele('#epub-viewer', timeout=5)
            if not iframe: return None, None

            # 滾動加載
            iframe.run_js("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.0)
            iframe.run_js("window.scrollTo(0, 0)")
            time.sleep(0.5)
            iframe.run_js("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.0)

            # 提取 CSS
            css_script = """
                let extractedCss = "";
                try {
                    for (let i = 0; i < document.styleSheets.length; i++) {
                        try {
                            const rules = document.styleSheets[i].cssRules;
                            if (rules) {
                                for (let j = 0; j < rules.length; j++) {
                                    extractedCss += rules[j].cssText + "\\n";
                                }
                            }
                        } catch (e) {}
                    }
                } catch(e) {}
                return extractedCss;
            """
            raw_css = iframe.run_js(css_script)
            
            # 提取 Body
            body_script = """
                const bodyClone = document.body.cloneNode(true);
                const junks = bodyClone.querySelectorAll('script, style, link, img');
                for (const el of junks) el.remove();
                return bodyClone.innerHTML;
            """
            raw_body = iframe.run_js(body_script)
            
            if len(raw_body) < 50: return None, None
            return raw_body, raw_css

        except Exception as e:
            return None, None

    def _go_next_page(self):
        """翻頁邏輯"""
        try:
            next_btn = self.browser.ele('text:다음화', timeout=2)
            if next_btn and next_btn.states.is_displayed:
                self.log('   發現下一話，跳轉中...')
                old_url = self.browser.url
                next_btn.click()
                for _ in range(10):
                    time.sleep(1)
                    if self.browser.url != old_url: break
                if "coin" in self.browser.url or "payment" in self.browser.url:
                    self.log('🛑 遇到付費牆，停止下載。')
                    return False
                time.sleep(2)
                return True
            else:
                self.log('🏁 未發現「下一話」按鈕，視為完結。')
                return False
        except:
            return False

    def _deep_clean_html(self, html_content):
        """深度清洗 HTML"""
        if not html_content: return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. 移除 style 屬性
        for tag in soup.find_all(True):
            if tag.has_attr('style'):
                del tag['style']

        # 2. 移除多餘容器
        if soup.main: soup.main.unwrap()

        # 3. 移除亂碼文字
        for element in soup.find_all(string=True):
            if isinstance(element, NavigableString):
                text = str(element).strip()
                if ("@import" in text) or \
                   ("{" in text and "}" in text and (":" in text or "body" in text)):
                    element.extract()

        return str(soup)

    def _optimize_css(self, css):
        """清洗 CSS"""
        if not css: return ""
        css = re.sub(r'@import[^;]+;', '', css)
        css = re.sub(r'width\s*:\s*720px', 'width: auto', css)
        css = re.sub(r'max-width\s*:\s*720px', 'max-width: 100%', css)
        return css

    def create_apple_epub(self, title, chapters):
        """打包 Apple Books 相容格式"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        filename = f"{safe_title}.epub"
        self.log(f'📦 正在打包 Apple Books 相容格式: {filename} ...')

        # 準備臨時目錄
        temp_dir = "temp_epub_build"
        if os.path.exists(temp_dir): 
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except: pass
            
        os.makedirs(temp_dir, exist_ok=True)
        
        oebps_dir = os.path.join(temp_dir, "OEBPS")
        text_dir = os.path.join(oebps_dir, "Text")
        styles_dir = os.path.join(oebps_dir, "Styles")
        meta_dir = os.path.join(temp_dir, "META-INF")
        
        os.makedirs(text_dir, exist_ok=True)
        os.makedirs(styles_dir, exist_ok=True)
        os.makedirs(meta_dir, exist_ok=True)

        # 1. 寫入 display-options.xml
        with open(os.path.join(meta_dir, "com.apple.ibooks.display-options.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?><display_options xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><platform name="ibooks"><option name="specified-fonts">true</option></platform></display_options>')

        # 2. 寫入 container.xml
        with open(os.path.join(meta_dir, "container.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')

        # 3. 處理章節
        manifest = []
        spine = []
        navs = []
        
        book_id = str(uuid.uuid4())
        
        manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')

        for chap in chapters:
            c_idx = chap['index']
            c_title = chap['title']
            
            xhtml_name = f"chapter_{c_idx:03d}.xhtml"
            css_name = f"style_{c_idx:03d}.css"
            
            # (A) 寫入 CSS
            final_css = chap['css'] + """
            /* Apple Books Fix */
            html, body { -webkit-text-size-adjust: none; background-color: transparent !important; margin: 0; padding: 10px; }
            div, p { max-width: 100% !important; box-sizing: border-box; }
            img { display: none !important; }
            """
            with open(os.path.join(styles_dir, css_name), "w", encoding="utf-8") as f:
                f.write(final_css)
            
            # (B) 寫入 XHTML
            xhtml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{c_title}</title>
  <link href="../Styles/{css_name}" rel="stylesheet" type="text/css"/>
</head>
<body>
  <h2>{c_title}</h2>
  {chap['content']}
</body>
</html>'''
            with open(os.path.join(text_dir, xhtml_name), "w", encoding="utf-8") as f:
                f.write(xhtml_content)

            # (C) 更新清單
            cid = f"chap_{c_idx}"
            cssid = f"css_{c_idx}"
            
            manifest.append(f'<item id="{cssid}" href="Styles/{css_name}" media-type="text/css"/>')
            manifest.append(f'<item id="{cid}" href="Text/{xhtml_name}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="{cid}"/>')
            navs.append(f'<navPoint id="nav{c_idx}" playOrder="{c_idx}"><navLabel><text>{c_title}</text></navLabel><content src="Text/{xhtml_name}"/></navPoint>')

        # 4. 生成 OPF (已移除錯誤的 cover meta)
        opf_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{title}</dc:title>
        <dc:language>ko</dc:language>
        <dc:identifier id="BookId" opf:scheme="UUID">{book_id}</dc:identifier>
        <dc:creator>Novel Extractor</dc:creator>
    </metadata>
    <manifest>{chr(10).join(manifest)}</manifest>
    <spine toc="ncx">{chr(10).join(spine)}</spine>
</package>'''
        with open(os.path.join(oebps_dir, "content.opf"), "w", encoding="utf-8") as f:
            f.write(opf_content)

        # 5. 生成 TOC
        ncx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head><meta name="dtb:uid" content="{book_id}"/></head>
    <docTitle><text>{title}</text></docTitle>
    <navMap>{chr(10).join(navs)}</navMap>
</ncx>'''
        with open(os.path.join(oebps_dir, "toc.ncx"), "w", encoding="utf-8") as f:
            f.write(ncx_content)

        # 6. 打包
        with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file == "mimetype": continue
                    fp = os.path.join(root, file)
                    rp = os.path.relpath(fp, temp_dir)
                    zf.write(fp, rp)
        
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except: pass
        
        self.log(f'✅ EPUB 製作完成！路徑: {os.path.abspath(filename)}')