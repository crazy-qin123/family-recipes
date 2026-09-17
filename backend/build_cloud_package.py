"""Build an allowlisted source archive; never include local secret files."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

FILES = ('Dockerfile', '.dockerignore', 'requirements.txt', 'cloud_app.py', 'cloud_store.py', 'url_recipe.py',
         'deepseek_recipe.py', 'importer.py', 'search_recipe.py')


def build():
    root = Path(__file__).resolve().parent
    destination = root.parent / 'dist'
    destination.mkdir(exist_ok=True)
    target = destination / 'family-recipes-api.zip'
    with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(root / name, name)
    with ZipFile(target) as archive:
        assert set(archive.namelist()) == set(FILES)
        assert archive.testzip() is None
    print(target)


if __name__ == '__main__':
    build()
