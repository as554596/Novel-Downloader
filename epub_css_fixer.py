import zipfile
import os
import shutil
import uuid
import re
from datetime import datetime
from bs4 import BeautifulSoup

def clean_css_content(original_css):
    """
    從原本亂七八糟的 CSS 中，只提取有用的顏色/氣泡樣式，
    丟棄所有導致排版崩壞的垃圾代碼 (width, font-family, body 等)。
    """
    if not original_css: return ""
    
    clean_lines = []
    # 定義我們要保留的關鍵字 (氣泡、顏色、背景)
    keep_keywords = ['color', 'background', 'border', 'radius', 'padding', 'margin']
    # 定義我們要丟棄的關鍵字 (寬度鎖死、字體、捲軸)
    drop_keywords = ['width', 'max-width', 'font-family', 'scrollbar', 'overflow', 'text-size-adjust']
    
    # 簡單的正則提取：提取 .class { ... } 區塊
    # 這裡我們不完全解析，而是採用白名單策略重寫一個標準 CSS
    return "" # 為了保險，我們直接使用內建的標準 CSS，不依賴舊的

def get_standard_css():
    """
    生成一套完美的、標準的、Apple Books 相容的 CSS
    """
    return """
@charset "utf-8";

/* 1. 基礎重置 (Reset) */
html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: auto;
    -webkit-text-size-adjust: none; /* 禁止 iOS 自動調整字體大小 */
    background-color: transparent !important; /* 讓閱讀器決定背景色 */
}

/* 2. 排版核心 (Layout) */
body {
    padding: 5% 5% 20% 5%; /* 上 右 下 左 邊距 */
    font-family: -apple-system, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
    line-height: 1.6;
    text-align: justify;
    color: inherit;
}

/* 3. 解鎖所有容器寬度 */
div, p, span, section, article {
    max-width: 100% !important;
    width: auto !important;
    box-sizing: border-box;
}

/* 4. 標題樣式 */
h2 {
    text-align: center;
    margin: 2em 0 1em 0;
    font-size: 1.4em;
    font-weight: bold;
    border-bottom: 1px solid #ddd;
    padding-bottom: 10px;
}

/* 5. 段落樣式 */
p {
    margin-bottom: 1em;
    word-break: break-all; /* 防止長單詞撐開版面 */
}

/* 6. (選用) 聊天氣泡樣式復刻 
   如果原文中有 .chat 或 .msg 類別，這些樣式會生效 */
.chat, .msg, .box {
    display: block;
    background-color: #f0f0f0;
    border-radius: 10px;
    padding: 10px 15px;
    margin: 10px 0;
    border: 1px solid #ddd;
}

/* 7. 隱藏殘留圖片 */
img { display: none !important; }
"""

def rebuild_epub_clean(input_path, output_path):
    base_dir = "temp_final_rebuild"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir)

    print(f"📦 [1/5] 解壓檔案: {input_path}")
    try:
        with zipfile.ZipFile(input_path, 'r') as zf:
            zf.extractall(base_dir)
    except:
        print("❌ 解壓失敗")
        return

    # 建立標準目錄
    oebps_dir = os.path.join(base_dir, "OEBPS")
    text_dir = os.path.join(oebps_dir, "Text")
    styles_dir = os.path.join(oebps_dir, "Styles")
    meta_inf_dir = os.path.join(base_dir, "META-INF")
    
    for d in [text_dir, styles_dir, meta_inf_dir]:
        if not os.path.exists(d): os.makedirs(d)

    # 寫入我們的新標準 CSS
    print("🎨 [2/5] 生成全新標準 CSS...")
    standard_css = get_standard_css()
    css_filename = "standard.css"
    with open(os.path.join(styles_dir, css_filename), "w", encoding="utf-8") as f:
        f.write(standard_css)

    # 處理 HTML 檔案
    print("HTML [3/5] 清洗 HTML 並連結新 CSS...")
    chapters = []
    
    # 遍歷尋找所有 HTML
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.xhtml') or f.endswith('.html'):
                # 移動並處理
                src_path = os.path.join(root, f)
                dst_path = os.path.join(text_dir, f)
                
                # 讀取內容
                with open(src_path, 'r', encoding='utf-8') as html_file:
                    soup = BeautifulSoup(html_file, 'html.parser')
                
                # 清洗 Head
                if soup.head:
                    # 刪除所有舊的 style 和 link
                    for tag in soup.head.find_all(['style', 'link']):
                        tag.decompose()
                    
                    # 插入新 CSS 連結
                    link = soup.new_tag("link", href=f"../Styles/{css_filename}", rel="stylesheet", type="text/css")
                    soup.head.append(link)
                
                # 清洗 Body (移除行內樣式)
                if soup.body:
                    for tag in soup.body.find_all(True):
                        if tag.has_attr('style'):
                            del tag['style'] # 刪除 style="width:720px"
                            
                # 寫入新位置
                with open(dst_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(str(soup))
                
                chapters.append(f)
                
                # 如果原位置不是目標位置，刪除原檔
                if src_path != dst_path:
                    os.remove(src_path)

    chapters.sort()

    # 生成 Apple Books 設定檔
    print("🍎 [4/5] 加入 Apple Books 設定...")
    with open(os.path.join(meta_inf_dir, "com.apple.ibooks.display-options.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?><display_options xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><platform name="ibooks"><option name="specified-fonts">true</option></platform></display_options>')
    
    with open(os.path.join(meta_inf_dir, "container.xml"), "w", encoding="utf-8") as f:
         f.write('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')

    # 重建 OPF
    print("📝 [5/5] 重建 OPF 索引...")
    book_id = str(uuid.uuid4())
    book_title = "Novel Rebuild"
    
    manifest = []
    spine = []
    
    manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    manifest.append(f'<item id="css_std" href="Styles/{css_filename}" media-type="text/css"/>')
    
    for i, chap in enumerate(chapters):
        cid = f"chap_{i+1}"
        manifest.append(f'<item id="{cid}" href="Text/{chap}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{cid}"/>')

    opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{book_title}</dc:title>
        <dc:language>ko</dc:language>
        <dc:identifier id="BookId" opf:scheme="UUID">{book_id}</dc:identifier>
        <meta name="cover" content="cover-image"/>
    </metadata>
    <manifest>{chr(10).join(manifest)}</manifest>
    <spine toc="ncx">{chr(10).join(spine)}</spine>
</package>'''

    with open(os.path.join(oebps_dir, "content.opf"), "w", encoding="utf-8") as f:
        f.write(opf)
        
    # 重建 TOC
    ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{book_id}"/></head>
<docTitle><text>{book_title}</text></docTitle>
<navMap>'''
    for i, chap in enumerate(chapters):
        ncx += f'<navPoint id="nav{i+1}" playOrder="{i+1}"><navLabel><text>Chapter {i+1}</text></navLabel><content src="Text/{chap}"/></navPoint>'
    ncx += '</navMap></ncx>'
    
    with open(os.path.join(oebps_dir, "toc.ncx"), "w", encoding="utf-8") as f:
        f.write(ncx)

    # 打包
    print(f"📦 打包中: {output_path}")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file == "mimetype": continue
                fp = os.path.join(root, file)
                rp = os.path.relpath(fp, base_dir)
                zf.write(fp, rp)
    
    shutil.rmtree(base_dir)
    print("✅ 完成！")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python epub_css_fixer.py <輸入檔案.epub> [輸出檔案.epub]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.rsplit('.', 1)[0] + "_Clean_Rebuild.epub"

    if os.path.exists(input_file):
        rebuild_epub_clean(input_file, output_file)
    else:
        print("請確認檔案是否存在")