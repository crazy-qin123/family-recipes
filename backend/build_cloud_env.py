"""Create a local CloudBase environment-variable JSON file without printing secrets."""
import json
from pathlib import Path


def read_env(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


root = Path(__file__).resolve().parent
values = {}
for name in ('.env', 'search.env', '.env.cloud'):
    values.update(read_env(root / name))

required = ('DEEPSEEK_API_KEY', 'DEEPSEEK_MODEL', 'TAVILY_API_KEY',
            'CLOUDBASE_ENV_ID', 'CLOUDBASE_API_KEY', 'FAMILY_ACCESS_TOKEN')
missing = [key for key in required if not values.get(key)]
if missing:
    raise SystemExit('Missing variables: ' + ', '.join(missing))

target = root / '.env.cloud.json'
target.write_text(json.dumps({key: values[key] for key in required}, ensure_ascii=False, indent=2), encoding='utf-8')
print('Cloud environment JSON created. Secret values were not printed.')
