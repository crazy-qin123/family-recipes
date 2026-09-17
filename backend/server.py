"""本机开发服务：仅监听回环地址，无第三方依赖。"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importer import import_recipe, ImportFailure
from deepseek_recipe import organize_text, AIError
from search_recipe import search_recipes, organize_candidate
from url_recipe import organize_url


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.reply(200 if self.path == '/health' else 404, {'status': 'ok', 'mode': 'local-development', 'aiUsed': False} if self.path == '/health' else {'error': '接口不存在'})

    def do_POST(self):
        self.connection.settimeout(90)
        if self.path not in ('/api/import', '/api/organize-text', '/api/search-recipes', '/api/organize-candidate', '/api/organize-url'):
            return self.reply(404, {'error': '接口不存在'})
        if self.headers.get('X-Recipe-Client') != 'local-miniprogram':
            return self.reply(403, {'error': '仅供本机小程序开发调试'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 80000:
                return self.reply(413, {'error': '请求内容为空或过大'})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            return self.reply(400, {'error': '请求格式不正确'})
        try:
            if self.path == '/api/search-recipes':
                result = search_recipes(body.get('query'))
            elif self.path == '/api/organize-candidate':
                result = organize_candidate(body.get('candidateId'))
            elif self.path == '/api/organize-text':
                result = organize_text(body.get('text'))
            elif self.path == '/api/organize-url':
                result = organize_url(body.get('url'))
            else:
                result = import_recipe(body.get('url'))
            self.reply(200, result)
        except AIError as error:
            self.reply(error.status, {'error': str(error)})
        except ImportFailure as error:
            self.reply(422, {'error': str(error), 'code': error.code, 'aiUsed': False})
        except Exception:
            self.reply(500, {'error': '导入服务暂时异常，请重试；没有保存任何菜谱。'})

    def log_message(self, format, *args):
        print('[local-api] ' + format % args, flush=True)


if __name__ == '__main__':
    print('Local recipe API: http://127.0.0.1:8765 (Ctrl+C to stop)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
