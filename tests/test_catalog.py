import json
from pathlib import Path
import threading
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from catalog import Catalog, DATA, percentage, selected_loot
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

    def test_russian_database_names_are_used(self):
        self.assertEqual(len(self.catalog.translations), 638)
        for shortname, translated in self.catalog.translations.items():
            self.assertEqual(self.catalog.item(shortname)['name'], translated)
        self.assertEqual(self.catalog.item('hat.wolf')['name'], 'Шапка из волка')

    def test_only_screenshot_containers_are_included(self):
        selection = self.catalog.selection
        self.assertEqual(len(selection), 45)
        self.assertEqual(len({row['id'] for row in selection}), 45)
        self.assertEqual(len(self.catalog.paths), 42)
        self.assertEqual(set(self.catalog.loot), set(self.catalog.paths.values()))
        self.assertNotIn('oil_barrel', self.catalog.containers())
        self.assertNotIn('loot_barrel_1', self.catalog.containers())
        self.assertEqual(self.catalog.paths['wagon_crate_normal'],
                         'assets/content/vehicles/trains/wagons/subents/wagon_crate_normal.prefab')
        self.assertEqual(self.catalog.paths['lab_crate_normal_2'],
                         'assets/bundled/prefabs/radtown/underwater_labs/crate_normal_2.prefab')

    def test_unavailable_tables_are_not_other_crates(self):
        for key in ['foodbox2', 'scientist_pt_drybox', 'scientist_rhib_drybox']:
            response = self.catalog.response(key)
            self.assertTrue(response['warning'])
            self.assertEqual(response['items'], [])

    def test_updater_cannot_restore_excluded_containers(self):
        selected = self.catalog.paths['crate_normal_2']
        unwanted = 'assets/bundled/prefabs/radtown/oil_barrel.prefab'
        payload = {'containers': {selected: [], unwanted: []},
                   'items': {'scrap': [{'container': selected}, {'container': unwanted}]}}
        result = selected_loot(payload)
        self.assertEqual(set(result['containers']), {selected})
        self.assertEqual(result['items']['scrap'], [{'container': selected}])


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
        self.assertEqual(len(crates), 46)  # 45 requested containers plus full item catalogue.
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
