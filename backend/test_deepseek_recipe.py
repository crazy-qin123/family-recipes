import json
import unittest
from unittest.mock import patch, MagicMock
from deepseek_recipe import organize_text, validate_draft, AIError, GATE

RECIPE = {'isRecipe': True, 'name': '蛋汤', 'category': '汤羹', 'ingredients': [{'name': '鸡蛋', 'amount': ''}], 'steps': ['将鸡蛋煮熟。']}


class DeepSeekTests(unittest.TestCase):
    def test_missing_key_does_not_call(self):
        with patch('deepseek_recipe.settings', return_value=('', 'model')), patch('deepseek_recipe.build_opener') as opener:
            with self.assertRaises(AIError) as error:
                organize_text('蛋汤，鸡蛋一个，放入沸水煮熟。')
            self.assertEqual(error.exception.status, 503)
            opener.assert_not_called()

    def test_validation(self):
        draft = validate_draft(RECIPE)
        self.assertEqual(draft['ingredients'][0]['amount'], '')
        self.assertEqual(draft['sourceType'], 'ai-text')
        for bad in [{}, {'isRecipe': False}, dict(RECIPE, steps=[]), dict(RECIPE, ingredients=[{'name': '鸡蛋', 'amount': 2}])]:
            with self.assertRaises(AIError):
                validate_draft(bad)

    def test_success_and_empty_output(self):
        for content, success in [(json.dumps(RECIPE), True), ('', False)]:
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]}).encode()
            with patch('deepseek_recipe.settings', return_value=('test-key', 'test-model')), patch('deepseek_recipe.build_opener') as opener:
                opener.return_value.open.return_value = response
                if success:
                    result = organize_text('蛋汤，鸡蛋一个，放入沸水煮熟。')
                    self.assertTrue(result['aiUsed'])
                    self.assertNotIn('test-key', json.dumps(result))
                else:
                    with self.assertRaises(AIError):
                        organize_text('蛋汤，鸡蛋一个，放入沸水煮熟。')
                self.assertEqual(opener.return_value.open.call_count, 1)
            self.assertFalse(GATE.locked())

    def test_oversize_rejected(self):
        with self.assertRaises(AIError):
            organize_text('菜' * 12001)


if __name__ == '__main__':
    unittest.main()
