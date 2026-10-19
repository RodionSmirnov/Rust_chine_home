#!/usr/bin/env python3
"""Refresh the bundled export and icons from one Git commit. Requires Git."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
REPOSITORY = 'https://github.com/bobosneefdev/rust-items-json.git'


def install(source):
    source = Path(source).resolve()
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Некорректная версия источника')
    items = json.loads((source / 'data/items.json').read_text())
    loot = json.loads((source / 'data/loot-probabilities.json').read_text())['containers']
    meta = json.loads((source / 'data/meta.json').read_text())
    names = {item['shortname'] for item in items}
    if not items or len(names) != len(items) or not loot or not meta.get('build'):
        raise ValueError('Неполный экспорт')
    for item in items:
        if not re.fullmatch(r'[a-zA-Z0-9_. -]+', item['shortname']):
            raise ValueError('Некорректный shortname')
        if 'icon' in item and item['icon'] != f"icons/{item['shortname']}.webp":
            raise ValueError('Некорректный путь изображения')
    for rows in loot.values():
        for row in rows:
            if row['item'] not in names or not 0 <= row['chance'] <= 1:
                raise ValueError('Некорректная таблица выпадения')
    # Stage and validate all files before touching the working snapshot.
    with tempfile.TemporaryDirectory(prefix='.data-update-', dir=ROOT) as tmp:
        staged = Path(tmp) / 'data'
        staged.mkdir()
        (staged / 'icons').mkdir()
        for name in ['items.json', 'loot-probabilities.json', 'meta.json']:
            shutil.copy2(source / 'data' / name, staged / name)
        for item in items:
            icon = source / 'data' / item.get('icon', 'missing')
            if icon.is_file():
                shutil.copy2(icon, staged / 'icons' / icon.name)
        shutil.copy2(source / 'LICENSE', staged / 'SOURCE-LICENSE.txt')
        (staged / 'provenance.json').write_text(json.dumps({
            'repository': REPOSITORY.removesuffix('.git'), 'commit': commit,
            'files': ['data/items.json', 'data/loot-probabilities.json', 'data/meta.json', 'data/icons/'],
            'note': 'Data and icons belong to Facepunch Studios.'}, indent=2) + '\n')
        from catalog import Catalog
        catalog = Catalog(staged)
        for key in catalog.containers():
            catalog.response(key)
        destination = ROOT / 'data'
        backup = Path(tmp) / 'previous'
        if destination.exists():
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
    print(f"База: сборка {meta['build']}, проверка {meta['checked']}, {len(items)} предметов, {len(loot)} контейнеров")
    print('Перезапусти app.py, чтобы применить новую базу.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Existing clean checkout of the source export')
    args = parser.parse_args()
    if args.source:
        install(args.source)
    else:
        with tempfile.TemporaryDirectory(prefix='rust-export-') as directory:
            subprocess.run(['git', 'clone', '--depth', '1', REPOSITORY, directory], check=True)
            install(directory)
