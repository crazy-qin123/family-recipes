import copy
import json
import time
import unittest
from unittest.mock import patch, MagicMock
import search_recipe as search
from deepseek_recipe import AIError

TEXT = '番茄炒蛋。食材：番茄2个，鸡蛋3个，油和盐适量。番茄洗净切块，鸡蛋打散。锅中放油炒熟鸡蛋盛出，番茄炒出汁后加入鸡蛋，炒至熟透调味。'


class SearchTests(unittest.TestCase):
    def setUp(self):
        search.CACHE.clear()

    def results(self, items):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'results': items}).encode()
        with patch('search_recipe.search_key', return_value='test-only'), patch('search_recipe.build_opener') as opener:
            opener.return_value.open.return_value = response
            return search.search_recipes('番茄炒蛋')['results']

    def test_missing_key(self):
        with patch('search_recipe.search_key', return_value=''), patch('search_recipe.build_opener') as opener:
            with self.assertRaises(AIError) as error:
                search.search_recipes('番茄炒蛋')
            self.assertEqual(error.exception.status, 503)
            opener.assert_not_called()

    def test_summary_not_used_as_body(self):
        results = self.results([{'title': '测试', 'url': 'https://example.com/recipe', 'content': TEXT}])
        self.assertFalse(results[0]['canOrganize'])
        with patch('search_recipe.organize_text') as model:
            with self.assertRaises(AIError):
                search.organize_candidate(results[0]['id'])
            model.assert_not_called()

    def test_provenance_and_cached_retry(self):
        results = self.results([{'title': '测试菜谱', 'url': 'https://example.com/recipe', 'content': '摘要', 'raw_content': TEXT}])
        self.assertNotIn('raw_content', results[0])
        with patch('search_recipe.organize_text', return_value={'draft': {'sourceUrl': 'https://wrong.test'}, 'warnings': [], 'aiUsed': True}) as model:
            first = search.organize_candidate(results[0]['id'])
            first['draft']['sourceUrl'] = 'changed'
            second = search.organize_candidate(results[0]['id'])
            self.assertEqual(second['draft']['sourceUrl'], 'https://example.com/recipe')
            self.assertEqual(second['draft']['sourceType'], 'ai-search')
            self.assertEqual(model.call_count, 1)
            self.assertIn(TEXT, model.call_args.args[0])

    def test_expiry_and_unknown(self):
        with self.assertRaises(AIError):
            search.organize_candidate('https://localhost/')
        results = self.results([{'title': '测试', 'url': 'https://example.com/recipe', 'raw_content': TEXT}])
        search.CACHE[results[0]['id']]['expires'] = time.monotonic() - 1
        with self.assertRaises(AIError) as error:
            search.organize_candidate(results[0]['id'])
        self.assertEqual(error.exception.status, 410)

    def test_filter_and_limits(self):
        results = self.results([{'url': 'http://127.0.0.1/recipe', 'raw_content': TEXT}, {'url': 'https://example.com/recipe', 'raw_content': '菜' * 11501}])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]['canOrganize'])
        for value in ['', '菜' * 61, None]:
            with self.assertRaises(AIError):
                search.search_recipes(value)


if __name__ == '__main__':
    unittest.main()
