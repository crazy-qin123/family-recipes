"""Cloud WSGI entry point. Local development server remains separate."""
import hmac
import json
import os

from deepseek_recipe import AIError, organize_text
from importer import ImportFailure, import_recipe
from search_recipe import organize_candidate, search_recipes
from url_recipe import organize_url
import cloud_store

STORAGE_ROUTES = {'/api/shared/list': cloud_store.listing, '/api/shared/save': cloud_store.save, '/api/shared/remove': cloud_store.remove,
                  '/api/shared/shopping': cloud_store.shopping_batch}

ROUTES = {
    '/api/import': (import_recipe, 'url'),
    '/api/organize-text': (organize_text, 'text'),
    '/api/search-recipes': (search_recipes, 'query'),
    '/api/organize-candidate': (organize_candidate, 'candidateId'),
    '/api/organize-url': (organize_url, 'url'),
}


def application(environ, start_response):
    def reply(status, body):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
        labels = {200: 'OK', 400: 'Bad Request', 401: 'Unauthorized',
                  403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed',
                  409: 'Conflict', 413: 'Content Too Large', 422: 'Unprocessable Entity',
                  429: 'Too Many Requests', 500: 'Internal Server Error',
                  502: 'Bad Gateway', 503: 'Service Unavailable', 504: 'Gateway Timeout'}
        start_response(f'{status} {labels.get(status, "Error")}', [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Content-Length', str(len(payload))), ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff'),
        ])
        return [payload]

    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', '')
    if path == '/health' and method == 'GET':
        return reply(200, {'status': 'ok', 'mode': 'cloud', 'aiUsed': False})
    if path not in ROUTES and path not in STORAGE_ROUTES:
        return reply(404, {'error': '接口不存在'})
    if method != 'POST':
        return reply(405, {'error': '请使用 POST 请求'})
    # Never trust client-supplied OpenID headers or the local development header.
    # This bootstrap credential must be entered by family members, never bundled
    # into mini-program source. Empty/short configuration fails closed.
    token = os.environ.get('FAMILY_ACCESS_TOKEN', '')
    if len(token) < 32 or not token.isascii():
        return reply(503, {'error': '尚未配置家庭访问凭证'})
    supplied = environ.get('HTTP_AUTHORIZATION', '')
    if not hmac.compare_digest(supplied.encode('utf-8'), ('Bearer ' + token).encode('ascii')):
        return reply(401, {'error': '请先输入家庭访问凭证'})
    try:
        size = int(environ.get('CONTENT_LENGTH') or '0')
        if not 0 < size <= 80000:
            return reply(413, {'error': '请求内容为空或过大'})
        raw = environ['wsgi.input'].read(size)
        if len(raw) != size:
            raise ValueError()
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError()
    except (ValueError, UnicodeError):
        return reply(400, {'error': '请求格式不正确'})
    try:
        if path in STORAGE_ROUTES:
            return reply(200, STORAGE_ROUTES[path](body))
        action, field = ROUTES[path]
        return reply(200, action(body.get(field)))
    except AIError as error:
        return reply(error.status, {'error': str(error)})
    except ImportFailure as error:
        return reply(422, {'error': str(error), 'code': error.code, 'aiUsed': False})
    except Exception:
        return reply(500, {'error': '服务暂时异常，请稍后重试'})
