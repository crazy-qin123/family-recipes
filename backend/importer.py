"""读取下厨房公开网页；不调用模型，不绕过验证码，不保存菜谱。"""
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

HOSTS = {'www.xiachufang.com', 'xiachufang.com', 'mip.xiachufang.com', 'hanwuji.xiachufang.com'}
MAX_BYTES = 2_000_000


class ImportFailure(Exception):
    def __init__(self, message, code='IMPORT_FAILED'):
        super().__init__(message)
        self.code = code


def normalize_url(raw):
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ImportFailure('请输入有效的下厨房菜谱链接。', 'INVALID_URL')
    try:
        url = urlsplit(raw.strip())
        match = re.fullmatch(r'/recipe/(\d{1,20})/?', url.path)
        if url.scheme != 'https' or url.hostname not in HOSTS or url.username or url.password or url.port not in (None, 443) or not match:
            raise ValueError()
    except ValueError:
        raise ImportFailure('仅支持 HTTPS 下厨房菜谱链接，格式为 /recipe/数字/。', 'INVALID_URL')
    return 'https://www.xiachufang.com/recipe/' + match[1] + '/'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_page(url):
    try:
        # 固定请求经校验的主站，不跟随重定向到验证页或其他地址。
        with build_opener(NoRedirect()).open(Request(url), timeout=15) as response:
            if 'text/html' not in response.headers.get('Content-Type', '').lower():
                raise ImportFailure('网站没有返回菜谱网页。')
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ImportFailure('网页内容过大，暂时无法导入。')
            return raw.decode('utf-8', errors='replace')
    except HTTPError as error:
        if error.code in (301, 302, 303, 307, 308, 401, 403, 429):
            raise ImportFailure('下厨房要求验证或限制了访问。请在浏览器查看原文，改用手动填写。', 'ACCESS_BLOCKED')
        raise ImportFailure('菜谱网页无法访问（HTTP %s）。' % error.code)
    except (URLError, TimeoutError, OSError):
        raise ImportFailure('无法连接下厨房或请求超时，请稍后重试。', 'NETWORK_ERROR')


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)

    def find(self, predicate):
        result = [self] if predicate(self) else []
        for child in self.children:
            if isinstance(child, Node):
                result.extend(child.find(predicate))
        return result

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def clean(value):
    return re.sub(r'\s+', ' ', value).strip() if isinstance(value, str) else ''


def recipe_objects(value):
    if isinstance(value, list):
        for child in value:
            yield from recipe_objects(child)
    elif isinstance(value, dict):
        kind = value.get('@type', [])
        if kind == 'Recipe' or isinstance(kind, list) and 'Recipe' in kind:
            yield value
        for child in value.values():
            if isinstance(child, (list, dict)):
                yield from recipe_objects(child)


def instruction_text(value):
    if isinstance(value, str):
        return [clean(value)] if clean(value) else []
    if isinstance(value, list):
        return [line for child in value for line in instruction_text(child)]
    if isinstance(value, dict):
        if value.get('itemListElement'):
            return instruction_text(value['itemListElement'])
        return instruction_text(value.get('text', ''))
    return []


def parse_page(html, original, canonical):
    doc = Document()
    doc.feed(html)
    root = doc.root
    titles = root.find(lambda n: n.tag == 'title')
    if titles and any(word in titles[0].text() for word in ('滑动验证', '安全验证', '登录')):
        raise ImportFailure('下厨房返回了验证页面，请改用手动填写。', 'ACCESS_BLOCKED')
    schema = {}
    for script in root.find(lambda n: n.tag == 'script' and n.attrs.get('type', '').lower() == 'application/ld+json'):
        try:
            schema = next(recipe_objects(json.loads(script.text())), {})
        except (ValueError, RecursionError):
            continue
        if schema:
            break
    headings = root.find(lambda n: n.tag == 'h1')
    name = clean(schema.get('name')) or (clean(headings[0].text()) if headings else '')
    ingredients = []
    for table in root.find(lambda n: n.has_class('ings')):
        for row in table.find(lambda n: n.tag == 'tr'):
            names = row.find(lambda n: n.has_class('name'))
            amounts = row.find(lambda n: n.has_class('unit'))
            if names and clean(names[0].text()):
                ingredients.append({'name': clean(names[0].text()), 'amount': clean(amounts[0].text()) if amounts else ''})
    warnings = []
    if not ingredients:
        lines = schema.get('recipeIngredient', [])
        if isinstance(lines, list):
            ingredients = [{'name': clean(line), 'amount': ''} for line in lines if clean(line)]
            if ingredients:
                warnings.append('食材原文暂未拆分用量，请逐项检查名称与用量。')
    steps = []
    for section in root.find(lambda n: n.has_class('steps')):
        steps.extend(clean(node.text()) for node in section.find(lambda n: n.has_class('text')) if clean(node.text()))
    if not steps:
        steps = instruction_text(schema.get('recipeInstructions'))
    if not name or not ingredients or not steps:
        raise ImportFailure('页面缺少可提取的菜名、食材或步骤，请查看原文并手动填写。', 'INCOMPLETE_RECIPE')
    if len(ingredients) > 100 or len(steps) > 100 or len(name) > 60 or any(len(i['name']) > 60 or len(i['amount']) > 40 for i in ingredients) or any(len(step) > 2000 for step in steps):
        raise ImportFailure('菜谱内容超过当前表单支持范围，请手动整理后填写。', 'CONTENT_TOO_LONG')
    # 不推断用量、耗时或份量；仅映射适合当前表单的文本字段。
    servings = clean(schema.get('recipeYield'))
    if len(servings) > 30:
        servings = ''
    warnings.append('网页提取，未调用大模型。分类默认为家常菜，请对照原文确认。')
    if any(not i['amount'] for i in ingredients):
        warnings.append('部分食材用量未注明，请核对。')
    author = schema.get('author', {})
    author = clean(author.get('name')) if isinstance(author, dict) else ''
    return {'draft': {'name': name, 'summary': '', 'servings': servings, 'time': '', 'note': '', 'category': '家常菜', 'ingredients': ingredients, 'steps': steps, 'sourceType': 'web', 'sourceUrl': original.strip(), 'canonicalUrl': canonical, 'sourceAuthor': author}, 'warnings': warnings, 'method': 'web-extraction', 'aiUsed': False}


def import_recipe(raw):
    canonical = normalize_url(raw)
    return parse_page(fetch_page(canonical), raw, canonical)
