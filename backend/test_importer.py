import unittest
from unittest.mock import patch
from importer import normalize_url, parse_page, import_recipe, ImportFailure

URL = 'https://www.xiachufang.com/recipe/123/'
HTML = '''<html><title>演示菜</title><script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Recipe","name":"演示菜","author":{"name":"测试作者"}}]}</script><div class="ings"><table><tr><td class="name"><a>鸡蛋</a></td><td class="unit">2 个</td></tr><tr><td class="name">盐</td><td class="unit"></td></tr></table></div><div class="steps"><ol><li><p class="text">充分加热至熟透。</p></li></ol></div></html>'''


class ImportTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_url('https://mip.xiachufang.com/recipe/123/?a=1'), URL)
        self.assertEqual(normalize_url('https://hanwuji.xiachufang.com/recipe/123/'), URL)

    def test_reject_addresses(self):
        for value in ['http://www.xiachufang.com/recipe/123/', 'https://127.0.0.1/recipe/123/', 'https://www.xiachufang.com.evil.test/recipe/123/', 'https://user@www.xiachufang.com/recipe/123/', 'https://www.xiachufang.com:8080/recipe/123/', 'https://www.xiachufang.com/auth/', None]:
            with self.subTest(value=value), self.assertRaises(ImportFailure):
                normalize_url(value)

    def test_fields(self):
        result = parse_page(HTML, URL, URL)
        self.assertFalse(result['aiUsed'])
        self.assertEqual(result['draft']['ingredients'], [{'name': '鸡蛋', 'amount': '2 个'}, {'name': '盐', 'amount': ''}])
        self.assertEqual(result['draft']['steps'], ['充分加热至熟透。'])
        self.assertEqual(result['draft']['sourceAuthor'], '测试作者')

    def test_captcha_and_incomplete(self):
        for html in ['<title>滑动验证</title>', '<h1>没有步骤</h1>']:
            with self.assertRaises(ImportFailure):
                parse_page(html, URL, URL)

    def test_schema_fallback_preserves_ingredient(self):
        html = '<script type="application/ld+json">{"@type":"Recipe","name":"测试","recipeIngredient":["鸡蛋 2个"],"recipeInstructions":[{"@type":"HowToSection","itemListElement":[{"text":"煮熟"}]}]}</script>'
        result = parse_page(html, URL, URL)
        self.assertEqual(result['draft']['ingredients'][0], {'name': '鸡蛋 2个', 'amount': ''})
        self.assertEqual(result['draft']['steps'], ['煮熟'])

    def test_invalid_url_not_fetched(self):
        with patch('importer.fetch_page') as fetch:
            with self.assertRaises(ImportFailure):
                import_recipe('https://localhost/recipe/123/')
            fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
