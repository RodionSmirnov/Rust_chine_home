"""Offline catalogue from a pinned Rust game export."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'
CATEGORIES = dict(zip(
    ['Ammunition', 'Attire', 'Component', 'Construction', 'Electrical', 'Food', 'Fun',
     'Items', 'Medical', 'Misc', 'Resources', 'Tool', 'Traps', 'Weapon'],
    ['Боеприпасы', 'Одежда', 'Компоненты', 'Строительство', 'Электричество', 'Еда',
     'Развлечения', 'Предметы', 'Медицина', 'Прочее', 'Ресурсы', 'Инструменты', 'Ловушки', 'Оружие']))
NAMES = {
    'crate_basic': 'Простой ящик', 'crate_normal_2': 'Обычный ящик',
    'crate_normal': 'Военный ящик', 'crate_elite': 'Элитный ящик',
    'crate_tools': 'Ящик с инструментами', 'crate_normal_2_medical': 'Медицинский ящик',
    'crate_normal_2_food': 'Продовольственный ящик', 'foodbox': 'Коробка с едой',
    'supply_drop': 'Груз снабжения', 'codelockedhackablecrate': 'Запертый ящик',
    'codelockedhackablecrate_oilrig': 'Запертый ящик · нефтяная вышка',
    'codelockedhackablecrate_ghostship': 'Запертый ящик · корабль-призрак',
    'bradley_crate': 'Ящик БТР Bradley', 'heli_crate': 'Ящик вертолёта',
    'loot_barrel_1': 'Бочка · тип 1', 'loot_barrel_2': 'Бочка · тип 2',
    'loot-barrel-1': 'Бочка · автоспавн 1', 'loot-barrel-2': 'Бочка · автоспавн 2',
    'oil_barrel': 'Нефтяная бочка', 'crate_underwater_advanced': 'Большой подводный ящик',
    'crate_underwater_basic': 'Подводный ящик', 'crate_basic_jungle': 'Ящик в джунглях',
    'crate_mine': 'Шахтёрский ящик', 'crate_shore': 'Прибрежный ящик',
    'crate_cannons': 'Ящик с пушечными припасами', 'minecart': 'Вагонетка',
    'vehicle_parts': 'Детали транспорта', 'vehicle_parts_advanced': 'Продвинутые детали транспорта',
    'crate_ammunition': 'Ящик с боеприпасами', 'crate_medical': 'Медицинский ящик',
    'crate_fuel': 'Ящик с топливом', 'crate_food_1': 'Продовольствие · тип 1',
    'crate_food_2': 'Продовольствие · тип 2', 'tech_parts_1': 'Технические детали · тип 1',
    'tech_parts_2': 'Технические детали · тип 2',
}
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


def container_name(path):
    key = Path(path).stem
    name = NAMES.get(key, key.replace('_', ' ').replace('-', ' '))
    if '/underwater_labs/' in path:
        name += ' · подводная лаборатория'
    elif '/modding/' in path:
        name += ' · моддинг'
    return name


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
        paths = sorted(self.loot, key=lambda p: (not p.endswith('/radtown/crate_normal_2.prefab'), container_name(p)))
        self.paths = {str(i): path for i, path in enumerate(paths)}

    def containers(self):
        return {'all': 'Все предметы · каталог', **{key: container_name(path) for key, path in self.paths.items()}}

    def item(self, shortname, drop=None):
        raw = self.items[shortname]
        image = self.directory / raw.get('icon', 'missing')
        row = {'id': shortname, 'name': RU_ITEMS.get(shortname, raw['name']),
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
        else:
            rows = [self.item(drop['item'], drop) for drop in self.loot[self.paths[key]]]
        return {'items': rows, 'meta': self.meta, 'source': self.provenance['repository'],
                'commit': self.provenance['commit'], 'crate': key, 'offline': True,
                'total_items': len(self.items), 'total_containers': len(self.paths)}
