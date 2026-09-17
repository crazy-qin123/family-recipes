"""Tavily 搜索单一来源，DeepSeek 整理；搜索正文只短期缓存在内存。"""
import copy
import ipaddress
import json
import os
import secrets
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from importer import NoRedirect
from deepseek_recipe import AIError, organize_text

CONFIG = Path(__file__).with_name('search.env')
CACHE = {}
CACHE_LOCK = Lock()
SEARCH_LOCK = Lock()
TTL = 1800
DOMESTIC_RECIPE_DOMAINS = [
    'meishij.net', 'meishichina.com', 'xinshipu.com', 'haodou.com',
    'cookpad.com', 'douguo.com', 'sohu.com', '163.com', 'qq.com'
]


def search_key():
    key = os.environ.get('TAVILY_API_KEY', '')
    if key:
        return key
    if CONFIG.exists():
        for line in CONFIG.read_text(encoding='utf-8-sig').splitlines():
            if line.strip().startswith('TAVILY_API_KEY='):
                return line.split('=', 1)[1].strip().strip('\"\'')
    return ''


def public_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        url = urlsplit(value)
        host = (url.hostname or '').lower()
        if url.scheme not in ('https', 'http') or url.username or url.password or url.port not in (None, 80, 443) or '.' not in host or host.endswith(('.local', '.localhost', '.internal')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except ValueError:
        return False


def search_recipes(query):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 60:
        raise AIError('请输入 1～60 字的菜名。', 400)
    try:
        key = search_key()
    except OSError:
        raise AIError('无法读取搜索配置，请检查 backend/search.env。', 503)
    if not key:
        raise AIError('尚未配置 Tavily Key，请在电脑的 backend/search.env 中填写。', 503)
    if not SEARCH_LOCK.acquire(blocking=False):
        raise AIError('正在搜索，请稍后重试。', 429)
    try:
        payload = {'query': query.strip() + ' 菜谱 食材 用量 制作步骤', 'topic': 'general', 'search_depth': 'basic', 'max_results': 10, 'include_answer': False, 'include_raw_content': 'text', 'include_images': False, 'auto_parameters': False, 'include_domains': DOMESTIC_RECIPE_DOMAINS, 'exclude_domains': ['xiachufang.com', 'facebook.com', 'youtube.com', 'baike.baidu.com']}
        request = Request('https://api.tavily.com/search', data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with build_opener(NoRedirect()).open(request, timeout=40) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise AIError('搜索结果过大，请换个更具体的菜名。', 502)
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('results'), list):
                raise ValueError()
        except HTTPError as error:
            message = {401: 'Tavily Key 无效，请检查本地配置。', 429: '搜索请求过于频繁，请稍后重试。', 432: 'Tavily 搜索额度不足或达到限制。', 433: 'Tavily 搜索额度达到限制。'}.get(error.code, '搜索服务暂时不可用，请稍后重试。')
            raise AIError(message, 502)
        except (URLError, TimeoutError, OSError):
            raise AIError('连接 Tavily 失败或超时，未自动重试。请检查本地网络。', 502)
        except (ValueError, TypeError):
            raise AIError('搜索服务返回格式异常，请稍后重试。', 502)
        candidates = []
        seen = set()
        with CACHE_LOCK:
            now = time.monotonic()
            for token in list(CACHE):
                if CACHE[token]['expires'] <= now:
                    del CACHE[token]
            for item in data['results'][:5]:
                if not isinstance(item, dict) or not public_url(item.get('url')) or item['url'] in seen:
                    continue
                url = item['url']
                seen.add(url)
                title = item.get('title') if isinstance(item.get('title'), str) else urlsplit(url).hostname
                snippet = item.get('content') if isinstance(item.get('content'), str) else ''
                content = item.get('raw_content') if isinstance(item.get('raw_content'), str) else ''
                content = content.strip()
                reason = ''
                if len(content) < 50:
                    reason = '未取得足够正文，可复制链接查看或改用粘贴菜谱。'
                elif len(content) > 11500:
                    reason = '正文过长，请复制需要的菜谱文字后使用粘贴整理。'
                elif '滑动验证' in content[:200] or '请完成验证' in content[:200]:
                    reason = '来源要求验证，暂时无法整理。'
                token = secrets.token_urlsafe(24)
                candidate = {'id': token, 'title': title[:200], 'url': url, 'domain': urlsplit(url).hostname, 'snippet': snippet[:350], 'canOrganize': not reason, 'reason': reason}
                while len(CACHE) >= 100:
                    del CACHE[next(iter(CACHE))]
                CACHE[token] = {'expires': now + TTL, 'candidate': candidate, 'content': content if not reason else '', 'result': None, 'busy': False}
                candidates.append(candidate)
        return {'results': candidates, 'aiUsed': False}
    finally:
        SEARCH_LOCK.release()


def organize_candidate(token):
    if not isinstance(token, str):
        raise AIError('请选择有效的搜索结果。', 400)
    with CACHE_LOCK:
        entry = CACHE.get(token)
        if not entry or entry['expires'] <= time.monotonic():
            raise AIError('搜索结果已过期或后端已重启，请重新搜索。', 410)
        if not entry['candidate']['canOrganize']:
            raise AIError(entry['candidate']['reason'])
        if entry['result']:
            return copy.deepcopy(entry['result'])
        if entry['busy']:
            raise AIError('这份菜谱正在整理，请稍候。', 429)
        entry['busy'] = True
    try:
        candidate = entry['candidate']
        # 不信任前端传入的 URL、正文或来源；只使用服务端搜索记录。
        result = organize_text('网页标题：' + candidate['title'] + '\n网页正文：\n' + entry['content'])
        result['draft'].update(sourceType='ai-search', sourceUrl=candidate['url'], canonicalUrl=candidate['url'], sourceAuthor='', sourceTitle=candidate['title'])
        result['warnings'] = ['仅根据你选择的这一篇网页整理，未混合其他搜索结果，请对照原文核对。'] + [warning for warning in result['warnings'] if '粘贴原文' not in warning]
        result['method'] = 'tavily-deepseek'
        with CACHE_LOCK:
            entry['result'] = copy.deepcopy(result)
        return result
    finally:
        with CACHE_LOCK:
            entry['busy'] = False
