import unittest
from unittest.mock import patch
from deepseek_recipe import AIError
import cloud_store as store


class StorageTests(unittest.TestCase):
    def recipe(self, version=0):
        return {'collection': 'recipes', 'version': version,
                'item': {'id': 'test-1', 'data': {'name': '测试菜',
                         'ingredients': [{'name': '鸡蛋', 'amount': '2 个'}], 'steps': ['煮熟']}}}

    def test_update_uses_version_filter(self):
        with patch.object(store, 'request', return_value=[{'id': 'test-1', 'version': 3}]) as call:
            store.save(self.recipe(2))
            self.assertEqual(call.call_args.args[2], {'id': 'eq.test-1', 'version': 'eq.2'})
            self.assertEqual(call.call_args.args[3]['version'], 3)

    def test_stale_update_conflicts(self):
        with patch.object(store, 'request', return_value=[]):
            with self.assertRaises(AIError) as error:
                store.save(self.recipe(2))
            self.assertEqual(error.exception.status, 409)

    def test_create_retry_preserves_different_content(self):
        with patch.object(store, 'request', side_effect=[AIError('conflict', 409), [{'data': {'name': 'other'}}]]):
            with self.assertRaises(AIError) as error:
                store.save(self.recipe())
            self.assertEqual(error.exception.status, 409)

    def test_validation_precedes_network(self):
        with patch.object(store, 'request') as call:
            for body in [self.recipe(True), {'collection': 'invalid'},
                         {'collection': 'recipes', 'item': {'id': 'a,b', 'data': {}}}]:
                with self.assertRaises(AIError):
                    store.save(body)
            call.assert_not_called()

    def test_shopping_is_single_rpc(self):
        with patch.object(store, 'request', return_value={'saved': True}) as call:
            result = store.shopping_batch({'operationId': 'op-1', 'changes': [
                {'id': 'a', 'name': '鸡蛋', 'amount': '2 个', 'done': False, 'sources': [], 'version': 0},
                {'id': 'b', 'delete': True, 'version': 2}]})
            self.assertEqual(result, {'saved': True})
            call.assert_called_once()
            self.assertEqual(call.call_args.args, ('POST', 'rpc/family_apply_shopping'))

    def test_shopping_rejects_duplicate_ids(self):
        with self.assertRaises(AIError):
            store.shopping_batch({'operationId': 'op-1', 'changes': [
                {'id': 'a', 'delete': True, 'version': 1}, {'id': 'a', 'delete': True, 'version': 1}]})


if __name__ == '__main__':
    unittest.main()
