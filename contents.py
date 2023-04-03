import os

from newspaper import fulltext, Article
import readability
import requests
import docx
import PyPDF2
from langdetect import detect


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
    doc = readability.Document(requests.get(url).text)
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
    contents = []
    for paragraph in document.paragraphs:
        contents.append(paragraph.text)
    lang = detect('\n'.join(contents))
    return contents, lang[0:2]


def get_contents() -> tuple[list[str], str]:
    """Get the contents."""

    while True:
        try:
            url = input("请输入文章链接或pdf/txt/docx文件路径：")
            if os.path.exists(url):
                if url.endswith('.pdf'):
                    return extract_text_from_pdf(url)
                elif url.endswith('.txt'):
                    return extract_text_from_txt(url)
                elif url.endswith('.docx'):
                    return extract_text_from_docx(url)
            else:
                return web_crawler_newspaper(url)
        except Exception as e:
            print("Error:", e)
