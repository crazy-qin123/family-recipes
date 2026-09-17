"""Server-only CloudBase REST storage with optimistic concurrency control."""
import json
import os
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from deepseek_recipe import AIError
from importer import NoRedirect

TABLES = {'recipes': 'family_recipes', 'shopping': 'family_shopping_items'}


def request(method, table, query=None, body=None):
    env = os.environ.get('CLOUDBASE_ENV_ID', '')
    key = os.environ.get('CLOUDBASE_API_KEY', '')
    if not re.fullmatch(r'[a-z0-9-]+', env) or not key:
        raise AIError('共享数据库尚未配置', 503)
    url = f'https://{env}.api.tcloudbasegateway.com/v1/rdb/rest/{table}'
    if query:
        url += '?' + urlencode(query)
    req = Request(url, method=method,
                  data=json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None,
                  headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
                           'Prefer': 'return=representation'})
    try:
        with build_opener(NoRedirect).open(req, timeout=20) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise AIError('数据过大，请缩小读取范围', 502)
            return json.loads(raw) if raw else []
    except HTTPError as error:
        if error.code == 409:
            raise AIError('记录已存在，请刷新后查看，避免重复保存', 409) from None
        raise AIError('共享数据库访问失败，请检查服务端配置', 502) from None
    except (URLError, TimeoutError, ValueError):
        raise AIError('共享数据库连接失败，请刷新确认保存结果后再操作', 503) from None


def table_for(body):
    table = TABLES.get(body.get('collection'))
    if not table:
        raise AIError('数据类型不正确', 400)
    return table


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,120}', value):
        raise AIError('记录编号不正确', 400)
    return value


def listing(body):
    table = table_for(body)
    offset = body.get('offset', 0)
    if type(offset) is not int or not 0 <= offset <= 100000:
        raise AIError('分页参数不正确', 400)
    rows = request('GET', table, {'order': 'id.asc', 'limit': 100, 'offset': offset})
    return {'items': rows, 'nextOffset': offset + len(rows) if len(rows) == 100 else None}


def text(value, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise AIError('填写内容不完整或过长', 400)
    return value.strip()


def validated(body):
    item = body.get('item')
    if not isinstance(item, dict):
        raise AIError('记录格式不正确', 400)
    identifier(item.get('id'))
    if body['collection'] == 'recipes':
        data = item.get('data')
        if not isinstance(data, dict):
            raise AIError('菜谱格式不正确', 400)
        clean = {k: text(data.get(k, ''), limit, k == 'name') for k, limit in
                 [('name', 60), ('summary', 120), ('note', 2000), ('servings', 30), ('imageUrl', 2000),
                  ('time', 30), ('category', 30), ('symbol', 20), ('sourceType', 30),
                  ('sourceTitle', 500), ('sourceUrl', 2000), ('canonicalUrl', 2000), ('sourceAuthor', 200)]}
        ingredients, steps = data.get('ingredients'), data.get('steps')
        if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 100 or not isinstance(steps, list) or not 1 <= len(steps) <= 100:
            raise AIError('请填写食材和步骤', 400)
        if any(not isinstance(i, dict) for i in ingredients):
            raise AIError('食材格式错误', 400)
        clean['ingredients'] = [{'name': text(i.get('name'), 60, True), 'amount': text(i.get('amount', ''), 40) or '未注明'} for i in ingredients]
        clean['steps'] = [text(s, 2000, True) for s in steps]
        clean['id'] = item['id']
        return {'data': clean}
    sources = item.get('sources', [])
    if not isinstance(sources, list) or len(sources) > 100 or type(item.get('done')) is not bool:
        raise AIError('清单格式不正确', 400)
    return {'name': text(item.get('name'), 120, True), 'amount': text(item.get('amount', ''), 120) or '未注明',
            'done': item['done'], 'sources': [text(s, 120) for s in sources]}


def save(body):
    table = table_for(body)
    if body['collection'] != 'recipes':
        raise AIError('清单请使用事务接口', 400)
    fields = validated(body)
    item_id = body['item']['id']
    version = body.get('version', 0)
    if type(version) is not int or not 0 <= version < 2147483647:
        raise AIError('版本号错误', 400)
    if version == 0:
        # Replaying the same create is safe; differing content never overwrites.
        try:
            rows = request('POST', table, body={'id': item_id, **fields})
        except AIError as error:
            if error.status != 409:
                raise
            rows = request('GET', table, {'id': 'eq.' + item_id})
            if not rows or any(rows[0].get(k) != v for k, v in fields.items()):
                raise error
    else:
        from datetime import datetime, timezone
        rows = request('PATCH', table, {'id': 'eq.' + item_id, 'version': 'eq.' + str(version)},
                       {**fields, 'version': version + 1, 'updated_at': datetime.now(timezone.utc).isoformat()})
        if not rows:
            raise AIError('家人已修改或删除这条记录。你的填写内容已保留，请刷新后核对', 409)
    return {'item': rows[0]}


def remove(body):
    table = table_for(body)
    item_id = identifier(body.get('id'))
    version = body.get('version')
    if type(version) is not int or version < 1:
        raise AIError('版本号错误', 400)
    rows = request('DELETE', table, {'id': 'eq.' + item_id, 'version': 'eq.' + str(version)})
    if not rows:
        raise AIError('记录已变化，请刷新后确认', 409)
    return {'deleted': True}


def shopping_batch(body):
    operation_id = identifier(body.get('operationId'))
    changes = body.get('changes')
    if not isinstance(changes, list) or not 1 <= len(changes) <= 200:
        raise AIError('清单操作格式不正确', 400)
    clean = []
    ids = set()
    for change in changes:
        if not isinstance(change, dict):
            raise AIError('清单操作格式不正确', 400)
        item_id = identifier(change.get('id'))
        version = change.get('version', 0)
        if type(version) is not int or not 0 <= version < 2147483647 or item_id in ids:
            raise AIError('清单版本或编号不正确', 400)
        ids.add(item_id)
        if change.get('delete') is True:
            if version == 0:
                raise AIError('删除版本错误', 400)
            clean.append({'id': item_id, 'version': version, 'delete': True})
        else:
            clean.append({'id': item_id, 'version': version, **validated({'collection': 'shopping', 'item': change})})
    return request('POST', 'rpc/family_apply_shopping', body={'operation_id': operation_id, 'changes': clean})
