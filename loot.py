"""Read loot tables without guessing probabilities."""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse

SOURCE = 'https://wiki.rustclash.com'
CRATES = {
    'crate': 'Обычный ящик',
    'military-crate': 'Военный ящик',
    'elite-tier-crate': 'Элитный ящик',
    'locked-crate': 'Запертый ящик',
    'tool-box': 'Ящик с инструментами',
    'medical-crate': 'Медицинский ящик',
    'supply-drop': 'Груз снабжения',
    'bradley-apc-crate': 'Ящик БТР Bradley',
    'helicopter-crate': 'Ящик вертолёта',
}


def safe_image(value):
    url = urljoin(SOURCE, value)
    parsed = urlparse(url)
    return url if parsed.scheme == 'https' and parsed.hostname in {
        'wiki.rustclash.com', 'rustlabs.com', 'cdn.rusthelp.com'
    } else ''


class LootParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = {'text': '', 'item': '', 'image': ''}
        elif self.cell is not None:
            if tag == 'a' and '/item/' in attrs.get('href', ''):
                self.cell['item'] = attrs['href'].split('/item/', 1)[1].split('?', 1)[0]
            if tag == 'img':
                self.cell['image'] = safe_image(attrs.get('data-src') or attrs.get('src', ''))

    def handle_data(self, data):
        if self.cell is not None:
            self.cell['text'] += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.cell['text'] = ' '.join(self.cell['text'].split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_loot(html):
    parser = LootParser()
    parser.feed(html)
    items = []
    for table in parser.tables:
        chance_col = quantity_col = None
        for row in table:
            labels = [c['text'].lower() for c in row]
            for i, label in enumerate(labels):
                if label in ('chance', 'probability', 'шанс'):
                    chance_col = i
                if label in ('amount', 'quantity', 'количество'):
                    quantity_col = i
            if chance_col is None or chance_col >= len(row):
                continue
            item_cell = next((c for c in row if c['item']), None)
            if not item_cell:
                continue
            chance_text = row[chance_col]['text']
            match = re.fullmatch(r'\s*([<>≤≥~≈]?)\s*(\d+(?:[.,]\d+)?)\s*%\s*', chance_text)
            if not match:
                continue
            chance = float(match[2].replace(',', '.'))
            if not 0 <= chance <= 100:
                continue
            items.append({
                'id': item_cell['item'], 'name': item_cell['text'] or item_cell['item'],
                'image': item_cell['image'], 'chance': chance,
                'chance_text': chance_text, 'approximate': bool(match[1]),
                'amount': row[quantity_col]['text'] if quantity_col is not None and quantity_col < len(row) else '—',
            })
        if items:
            break  # Only the first probability table: do not merge unrelated tabs.
    if not items:
        raise ValueError('Таблица лута не найдена. Возможно, сайт изменил формат или вернул страницу защиты.')
    return items
