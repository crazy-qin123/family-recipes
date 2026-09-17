import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from server import Handler
from importer import parse_page
from test_importer import HTML, URL


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:%s' % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, value, headers=True):
        request = Request(self.base + '/api/import', data=json.dumps(value).encode(), headers={'Content-Type': 'application/json', **({'X-Recipe-Client': 'local-miniprogram'} if headers else {})})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_http_success_with_fixture(self):
        # 只模拟外部网页，实际经过 HTTP handler 和真实解析器。
        with patch('importer.fetch_page', return_value=HTML):
            status, result = self.post({'url': URL})
        self.assertEqual(status, 200)
        self.assertEqual(result['draft']['name'], '演示菜')
        self.assertFalse(result['aiUsed'])

    def test_invalid_body_and_address(self):
        self.assertEqual(self.post([])[0], 400)
        self.assertEqual(self.post({'url': 'https://localhost/recipe/1/'})[0], 422)

    def test_client_header_required(self):
        self.assertEqual(self.post({'url': URL}, headers=False)[0], 403)


if __name__ == '__main__':
    unittest.main()
