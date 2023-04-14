import os
import time

from newspaper import fulltext, Article
import readability
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import docx
import PyPDF2
from langdetect import detect
import xxhash


def web_crawler_newspaper(url: str) -> tuple[list[str], str]:
    """Run the web crawler."""
    raw_html, lang = _get_raw_html(url)
    try:
        text = fulltext(raw_html, language=lang)
    except:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text
    contents = [text.strip() for text in text.splitlines() if text.strip()]
    return contents, lang


def _get_raw_html(url):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36')

    with webdriver.Chrome(options=chrome_options) as driver:
        driver.get(url)
        print("等10s网页加载完成")
        time.sleep(10)
        html = driver.page_source

    doc = readability.Document(html)
    html = doc.summary()
    lang = detect(html)
    return html, lang[0:2]


def extract_text_from_pdf(file_path: str) -> tuple[list[str], str]:
    """Extract text content from a PDF file."""
    with open(file_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        contents = []
        for page in pdf_reader.pages:
            page_text = page.extract_text().strip()
            raw_text = [text.strip() for text in page_text.splitlines() if text.strip()]
            new_text = ''
            for text in raw_text:
                new_text += text
                if text[-1] in ['.', '!', '?', '。', '！', '？', '…', ';', '；', ':', '：', '”', '’', '）', '】', '》', '」',
                                '』', '〕', '〉', '》', '〗', '〞', '〟', '»', '"', "'", ')', ']', '}']:
                    contents.append(new_text)
                    new_text = ''
            if new_text:
                contents.append(new_text)
        lang = detect('\n'.join(contents))
        return contents, lang[0:2]


def extract_text_from_txt(file_path: str) -> tuple[list[str], str]:
    """Extract text content from a TXT file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        contents = [text.strip() for text in f.readlines() if text.strip()]
        lang = detect('\n'.join(contents))
        return contents, lang[0:2]


def extract_text_from_docx(file_path: str) -> tuple[list[str], str]:
    """Extract text content from a DOCX file."""
    document = docx.Document(file_path)
    contents = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    lang = detect('\n'.join(contents))
    return contents, lang[0:2]


def get_contents() -> tuple[list[str], str, str]:
    """Get the contents."""

    while True:
        try:
            url = input("请输入文章链接或pdf/txt/docx文件路径：").strip()
            if os.path.exists(url):
                if url.endswith('.pdf'):
                    contents, data = extract_text_from_pdf(url)
                elif url.endswith('.txt'):
                    contents, data = extract_text_from_txt(url)
                elif url.endswith('.docx'):
                    contents, data = extract_text_from_docx(url)
                else:
                    print("不支持的文件格式")
                    continue
            else:
                contents, data = web_crawler_newspaper(url)
            return contents, data, xxhash.xxh3_128_hexdigest('\n'.join(contents))
        except Exception as e:
            print("Error:", e)
