"""Fetch an approved domestic recipe page and let DeepSeek extract a draft."""
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from importer import NoRedirect, ImportFailure
from deepseek_recipe import organize_text

ALLOWED = ('.meishichina.com', '.meishij.net', '.douguo.com', '.xinshipu.com', '.haodou.com', '.cookpad.com', '.xiachufang.com')


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.skip = 0; self.parts = []; self.image = ''
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('property') in ('og:image', 'og:image:url') and attrs.get('content'):
            self.image = attrs['content'].strip()
        if tag in ('script', 'style', 'noscript', 'svg'): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg') and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def organize_url(raw):
    if not isinstance(raw, str) or len(raw.strip()) > 2048:
        raise ImportFailure('请输入有效的菜谱网页链接。', 'INVALID_URL')
    try:
        url = urlsplit(raw.strip()); host = (url.hostname or '').lower()
        if url.scheme != 'https' or not host or not any(host == x[1:] or host.endswith(x) for x in ALLOWED) or url.username or url.password or url.port not in (None, 443):
            raise ValueError()
    except ValueError:
        raise ImportFailure('目前仅支持国内常见菜谱网站的 HTTPS 链接。', 'INVALID_URL')
    try:
        with build_opener(NoRedirect()).open(Request(raw.strip(), headers={'User-Agent': 'family-recipes/1.0'}), timeout=20) as response:
            if 'text/html' not in response.headers.get('Content-Type', '').lower(): raise ImportFailure('链接不是网页。')
            raw_html = response.read(2_000_001)
            if len(raw_html) > 2_000_000: raise ImportFailure('网页过大，请复制正文使用。')
        parser = Text(); parser.feed(raw_html.decode('utf-8', errors='replace'))
        text = re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()
        if len(text) < 80: raise ImportFailure('网页正文不足，请复制菜谱正文使用。', 'INCOMPLETE_RECIPE')
        result = organize_text(text[:12000])
        result['draft'].update(sourceType='ai-search', sourceUrl=raw.strip(), canonicalUrl=raw.strip(), sourceTitle='', sourceAuthor='', imageUrl=parser.image)
        result['warnings'] = ['AI 根据网页正文整理，请对照原网页核对食材和步骤。'] + result.get('warnings', [])
        return result
    except HTTPError as error:
        raise ImportFailure('网页暂时无法访问，请复制正文使用。', 'ACCESS_BLOCKED') from None
    except (URLError, TimeoutError, OSError):
        raise ImportFailure('网页连接超时，请复制正文使用。', 'NETWORK_ERROR') from None
