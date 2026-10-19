"""Offline catalogue from a pinned Rust game export."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'
CATEGORIES = dict(zip(
    ['Ammunition', 'Attire', 'Component', 'Construction', 'Electrical', 'Food', 'Fun',
     'Items', 'Medical', 'Misc', 'Resources', 'Tool', 'Traps', 'Weapon'],
    ['Боеприпасы', 'Одежда', 'Компоненты', 'Строительство', 'Электричество', 'Еда',
     'Развлечения', 'Предметы', 'Медицина', 'Прочее', 'Ресурсы', 'Инструменты', 'Ловушки', 'Оружие']))
RU_ITEMS = {
    'scrap': 'Металлолом', 'smgbody': 'Корпус пистолета-пулемёта',
    'metalpipe': 'Металлическая труба', 'metal.refined': 'Металл высокого качества',
    'techparts': 'Старые микросхемы', 'riflebody': 'Корпус винтовки',
    'ammo.rocket.mlrs': 'Ракета РСЗО', 'targeting.computer': 'Компьютер наведения',
    'cctv.camera': 'Камера видеонаблюдения', 'ammo.pistol': 'Пистолетный патрон',
    'advancedblueprintfragment': 'Фрагмент продвинутого чертежа',
    'ammo.shotgun': 'Картечь 12-го калибра', 'ammo.rifle': 'Патрон 5.56 мм',
    'pistol.semiauto': 'Полуавтоматический пистолет', 'grenade.f1': 'Граната F1',
    'grenade.molotov': 'Коктейль Молотова', 'rifle.ak': 'Штурмовая винтовка',
    'rifle.lr300': 'Штурмовая винтовка LR-300', 'rifle.bolt': 'Болтовая винтовка',
    'lmg.m249': 'Пулемёт M249', 'smg.mp5': 'MP5A4', 'smg.thompson': 'Томпсон',
    'semibody': 'Корпус полуавтомата', 'gears': 'Шестерни', 'metalspring': 'Металлическая пружина',
    'rope': 'Верёвка', 'sewingkit': 'Набор для шитья', 'tarp': 'Брезент',
    'roadsigns': 'Дорожные знаки', 'sheetmetal': 'Листовой металл',
    'metalblade': 'Металлическое лезвие', 'propanetank': 'Пустой пропановый баллон',
    'fuse': 'Предохранитель', 'wood': 'Дерево', 'stones': 'Камни',
    'metal.fragments': 'Фрагменты металла', 'cloth': 'Ткань', 'sulfur': 'Сера',
    'lowgradefuel': 'Топливо низкого качества', 'crude.oil': 'Сырая нефть',
    'syringe.medical': 'Медицинский шприц', 'largemedkit': 'Большая аптечка',
    'bandage': 'Бинт', 'explosive.timed': 'Взрывчатка с таймером',
    'ammo.rocket.basic': 'Ракета', 'explosive.satchel': 'Взрывной ранец',
}


CONFIG = DATA.parent / 'config' / 'containers.json'
LOCALIZATION = DATA.parent / 'localization'


def selected_loot(payload):
    """Keep exactly the requested prefab paths, including reverse lookups."""
    selection = json.loads(CONFIG.read_text(encoding='utf-8'))
    wanted = {row['path'] for row in selection if row['path']}
    containers = {path: rows for path, rows in payload['containers'].items() if path in wanted}
    reverse = {}
    for item, rows in payload.get('items', {}).items():
        kept = [row for row in rows if row['container'] in containers]
        if kept:
            reverse[item] = kept
    return {'containers': containers, 'items': reverse}


def percentage(value):
    percent = value * 100
    if 0 < percent < .01:
        return '<0,01 %'
    return f'{percent:.2f}'.rstrip('0').rstrip('.').replace('.', ',') + ' %'


class Catalog:
    def __init__(self, directory=DATA):
        self.directory = Path(directory)
        self.meta = json.loads((self.directory / 'meta.json').read_text())
        self.provenance = json.loads((self.directory / 'provenance.json').read_text())
        self.items = {x['shortname']: x for x in json.loads((self.directory / 'items.json').read_text())}
        self.loot = json.loads((self.directory / 'loot-probabilities.json').read_text())['containers']
        self.selection = json.loads(CONFIG.read_text(encoding='utf-8'))
        self.translations = json.loads((LOCALIZATION / 'items.ru.json').read_text(encoding='utf-8'))
        self.translation_source = json.loads((LOCALIZATION / 'provenance.json').read_text(encoding='utf-8'))
        self.paths = {row['id']: row['path'] for row in self.selection if row['path'] in self.loot}

    def containers(self):
        return {'all': 'Все предметы · каталог', **{row['id']: row['name'] for row in self.selection}}

    def item(self, shortname, drop=None):
        raw = self.items[shortname]
        image = self.directory / raw.get('icon', 'missing')
        row = {'id': shortname, 'name': self.translations.get(shortname, RU_ITEMS.get(shortname, raw['name'])),
               'english_name': raw['name'], 'category': CATEGORIES.get(raw['category'], raw['category']),
               'image': '/icons/' + image.name if image.is_file() else '',
               'condition': '—', 'amount': '—', 'chance': None, 'chance_text': 'Не выбран ящик',
               'hidden': raw.get('hidden', False)}
        if drop is not None:
            low, high = drop['min'], drop['max']
            condition = drop.get('condition')
            if condition:
                a, b = (round(condition[k] * 100) for k in ('min', 'max'))
                row['condition'] = f'{a} %' if a == b else f'{a}–{b} %'
            elif raw.get('condition', {}).get('enabled'):
                row['condition'] = '100 %'
            row.update(chance=drop['chance'] * 100, chance_text=percentage(drop['chance']),
                       amount=str(low) if low == high else f'{low}–{high}')
        return row

    def response(self, key):
        if key == 'all':
            rows = [self.item(shortname) for shortname in self.items]
        elif key in self.paths:
            rows = [self.item(drop['item'], drop) for drop in self.loot[self.paths[key]]]
        elif key in self.containers():
            rows = []
        else:
            raise KeyError(key)
        return {'items': rows, 'meta': self.meta, 'source': self.provenance['repository'],
                'commit': self.provenance['commit'], 'crate': key, 'offline': True,
                'total_items': len(self.items), 'total_containers': len(self.selection),
                'available_containers': len(self.paths), 'translation_source': self.translation_source,
                'translated_items': len(self.translations.keys() & self.items.keys()),
                'warning': ('Для этого контейнера нет таблицы в текущей базе. Вероятности не подставлены из других ящиков.'
                            if key != 'all' and key not in self.paths else '')}
