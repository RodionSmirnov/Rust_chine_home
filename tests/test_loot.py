import unittest
from loot import parse_loot, safe_image

# Synthetic fixture: these numbers are parser inputs, not Rust loot data.
HTML = '''<table><tr><th>Item</th><th>Amount</th><th>Chance</th></tr>
<tr><td><a href="/item/test-item"><img src="/img/items180/test.png">Test item</a></td><td>1–3</td><td>12.5 %</td></tr>
<tr><td><a href="/item/rare">Rare</a></td><td>1</td><td>&lt;0.1 %</td></tr></table>'''


class ParserTests(unittest.TestCase):
    def test_table(self):
        items = parse_loot(HTML)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['chance'], 12.5)
        self.assertEqual(items[0]['amount'], '1–3')
        self.assertEqual(items[0]['image'], 'https://wiki.rustclash.com/img/items180/test.png')
        self.assertTrue(items[1]['approximate'])
        self.assertEqual(items[1]['chance_text'], '<0.1 %')

    def test_blocked_page(self):
        with self.assertRaises(ValueError):
            parse_loot('<html>Please verify you are human</html>')

    def test_invalid_percentage(self):
        self.assertEqual(len(parse_loot(HTML.replace('12.5 %', '150%'))), 1)

    def test_untrusted_image(self):
        self.assertEqual(safe_image('javascript:alert(1)'), '')
        self.assertEqual(safe_image('https://example.com/test.png'), '')


if __name__ == '__main__':
    unittest.main()
