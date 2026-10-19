import json
from pathlib import Path
import threading
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from catalog import Catalog, DATA, percentage
from app import Handler


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog()

    def test_catalogue_is_complete(self):
        raw = json.loads((DATA / 'items.json').read_text())
        rows = self.catalog.response('all')['items']
        self.assertEqual(len(rows), len(raw))
        self.assertGreater(len(rows), 1000)
        self.assertTrue(all(row['chance'] is None for row in rows))

    def test_every_source_probability_is_preserved(self):
        for key, path in self.catalog.paths.items():
            original = self.catalog.loot[path]
            actual = self.catalog.response(key)['items']
            self.assertEqual(len(original), len(actual))
            for drop, row in zip(original, actual):
                self.assertEqual(row['id'], drop['item'])
                self.assertAlmostEqual(row['chance'], drop['chance'] * 100)
                self.assertTrue(0 <= row['chance'] <= 100)

    def test_all_declared_images_are_local_files(self):
        for row in self.catalog.response('all')['items']:
            if row['image']:
                path = DATA / 'icons' / Path(row['image']).name
                self.assertTrue(path.is_file())
                self.assertEqual(path.read_bytes()[:4], b'RIFF')

    def test_elite_crate_scrap(self):
        path = 'assets/bundled/prefabs/radtown/crate_elite.prefab'
        key = next(key for key, value in self.catalog.paths.items() if value == path)
        scrap = next(row for row in self.catalog.response(key)['items'] if row['id'] == 'scrap')
        self.assertEqual(scrap['name'], 'Металлолом')
        self.assertEqual(scrap['chance'], 100)
        self.assertEqual(scrap['category'], 'Ресурсы')

    def test_small_chance_is_not_displayed_as_zero(self):
        self.assertEqual(percentage(.000001), '<0,01 %')
        self.assertEqual(percentage(1), '100 %')


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_ui_and_catalogue(self):
        self.assertIn('Состояние', urlopen(self.base).read().decode())
        crates = json.load(urlopen(self.base + '/api/crates'))
        self.assertGreater(len(crates), 100)
        rows = json.load(urlopen(self.base + '/api/loot?crate=all'))['items']
        self.assertGreater(len(rows), 1000)
        image = next(row['image'] for row in rows if row['image'])
        with urlopen(self.base + image) as response:
            self.assertEqual(response.headers['Content-Type'], 'image/webp')
            self.assertEqual(response.read()[:4], b'RIFF')

    def test_bad_container_and_traversal(self):
        for path, status in [('/api/loot?crate=invalid', 400), ('/icons/../meta.json', 404)]:
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base + path)
            self.assertEqual(error.exception.code, status)

    def test_icon_with_space(self):
        with urlopen(self.base + '/icons/legacy%20bow.webp') as response:
            self.assertEqual(response.read()[:4], b'RIFF')


if __name__ == '__main__':
    unittest.main()
