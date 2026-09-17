import io
import json
import os
import unittest
from unittest.mock import patch

import cloud_app


class CloudTests(unittest.TestCase):
    def request(self, token='', body=b'{"text":"test"}', path='/api/organize-text', method='POST'):
        result = []
        env = {'PATH_INFO': path, 'REQUEST_METHOD': method,
               'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body),
               'HTTP_AUTHORIZATION': token, 'HTTP_X_RECIPE_CLIENT': 'local-miniprogram'}
        data = b''.join(cloud_app.application(env, lambda status, headers: result.append(status)))
        return int(result[0].split()[0]), json.loads(data)

    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ, {'FAMILY_ACCESS_TOKEN': ''}):
            self.assertEqual(self.request()[0], 503)

    def test_local_header_cannot_authorize_cloud(self):
        with patch.dict(os.environ, {'FAMILY_ACCESS_TOKEN': 'x' * 40}):
            self.assertEqual(self.request()[0], 401)

    def test_authorized_request_and_invalid_json(self):
        with patch.dict(os.environ, {'FAMILY_ACCESS_TOKEN': 'x' * 40}), patch.dict(
                cloud_app.ROUTES, {'/api/organize-text': (lambda text: {'draft': text}, 'text')}):
            self.assertEqual(self.request('Bearer ' + 'x' * 40), (200, {'draft': 'test'}))
            self.assertEqual(self.request('Bearer ' + 'x' * 40, b'[]')[0], 400)
            self.assertEqual(self.request('Bearer ' + 'x' * 40, b'x' * 80001)[0], 413)

    def test_health_does_not_need_keys(self):
        self.assertEqual(self.request(path='/health', method='GET')[0], 200)


if __name__ == '__main__':
    unittest.main()
