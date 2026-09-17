"""Search, organize and save a bounded recipe batch to CloudBase."""
import json
import os
from pathlib import Path
from search_recipe import search_recipes, organize_candidate
from cloud_store import request


def load_cloud_env():
    path = Path(__file__).with_name('.env.cloud')
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def run(names, category):
    load_cloud_env()
    report = []
    for index, name in enumerate(names, 1):
        try:
            found = search_recipes(name)
            candidates = [x for x in found.get('results', []) if x.get('canOrganize')]
            if not candidates:
                report.append({'name': name, 'status': 'no-source'})
                continue
            result = organize_candidate(candidates[0]['id'])
            draft = result.get('draft')
            if not draft:
                report.append({'name': name, 'status': 'no-draft'})
                continue
            draft['category'] = category
            # Use the requested canonical dish name; preserve source wording in the body.
            draft['name'] = name
            draft['id'] = 'bulk-' + name
            draft['sourceType'] = 'ai-search'
            draft['sourceUrl'] = candidates[0].get('url', '')
            draft['canonicalUrl'] = candidates[0].get('url', '')
            draft['sourceTitle'] = candidates[0].get('title', '')
            draft['sourceAuthor'] = candidates[0].get('domain', '')
            rows = request('POST', 'family_recipes', body={'id': draft['id'], 'data': draft})
            report.append({'name': name, 'status': 'saved', 'source': draft['sourceUrl'], 'id': rows[0]['id']})
        except Exception as error:
            report.append({'name': name, 'status': 'error', 'message': str(error)[:120]})
        print(json.dumps({'progress': f'{index}/{len(names)}', **report[-1]}, ensure_ascii=False), flush=True)
    Path(__file__).with_name('bulk-import-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'done': len(names), 'saved': sum(x['status'] == 'saved' for x in report)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    run(['番茄炒蛋', '红烧肉', '可乐鸡翅', '鱼香肉丝', '宫保鸡丁', '青椒肉丝',
         '土豆炖牛肉', '麻婆豆腐', '糖醋排骨', '回锅肉', '蒜薹炒肉', '木须肉',
         '地三鲜', '家常豆腐', '清炒西兰花'], '家常菜')
