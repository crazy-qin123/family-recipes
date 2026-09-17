"""只输出字段计数，不保存或打印完整原文。"""
import json
from importer import import_recipe, ImportFailure

for url in ['https://mip.xiachufang.com/recipe/107777822/', 'https://hanwuji.xiachufang.com/recipe/107651597/']:
    try:
        result = import_recipe(url)
        draft = result['draft']
        print(json.dumps({'url': url, 'name': draft['name'], 'ingredients': len(draft['ingredients']), 'steps': len(draft['steps']), 'missingAmounts': sum(not x['amount'] for x in draft['ingredients']), 'aiUsed': result['aiUsed']}, ensure_ascii=False))
    except ImportFailure as error:
        print(json.dumps({'url': url, 'error': str(error), 'code': error.code}, ensure_ascii=False))
