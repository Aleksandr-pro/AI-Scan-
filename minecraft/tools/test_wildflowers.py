#!/usr/bin/env python3
"""Check flower processing, atlas variants and archives; not a rendering test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_wildflowers import SOURCE, BLOCKS, SIZE, FLOWERS, flower, rose

ROOT = Path('minecraft/realistic-dirt')


class WildflowerTests(unittest.TestCase):
    def test_source_and_ten_flowers(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '169b588ce582b28bbc9e126fa79c40cb4db4dfb452be366f1506ed226cecf1f9')
        self.assertEqual(len(FLOWERS), 10)
        hashes = []
        for name in FLOWERS:
            with Image.open(BLOCKS / f'{name}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), flower(name).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertGreater(alpha.histogram()[0], 25000)
                self.assertGreater(sum(alpha.histogram()[128:]), 10000)
                self.assertEqual(alpha.getbbox()[3], SIZE)
                hashes.append(hashlib.sha256(image.tobytes()).digest())
        self.assertEqual(len(set(hashes)), 10)

    def test_rose_halves_are_one_continuous_image(self):
        full = rose()
        for part, box in (('top', (0, 0, SIZE, SIZE)), ('bottom', (0, SIZE, SIZE, SIZE*2))):
            with Image.open(BLOCKS / f'double_plant_rose_{part}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), full.crop(box).tobytes())
                self.assertGreater(sum(image.getchannel('A').histogram()[128:]), 1000)
        self.assertEqual(full.getchannel('A').getbbox()[3], 2*SIZE)

    def test_variants_scope_and_distributions(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        expected = {'allium': ('flower_allium', 'photo_flower_violet'),
                    'dandelion': ('flower_dandelion', 'photo_flower_buttercup'),
                    'yellow_flower': ('flower_dandelion', 'photo_flower_buttercup')}
        for key, names in expected.items():
            self.assertEqual(terrain[key]['textures']['variations'], [
                {'path': 'textures/blocks/' + name, 'weight': 1} for name in names])
        self.assertNotIn('red_flower', terrain)  # vanilla indexed alias retained
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        for name in ('poppy', 'allium', 'rose_bush', 'double_plant'):
            self.assertNotIn(name, blocks)
        files = [f'textures/blocks/{name}.png' for name in FLOWERS]
        files += [f'textures/blocks/double_plant_rose_{part}.png' for part in ('top', 'bottom')]
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 90, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 90, 0])
                self.assertEqual(json.loads(pack.read('textures/terrain_texture.json')), json.loads((ROOT / 'textures/terrain_texture.json').read_text()))
                for path in files:
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())
                for color in ('red', 'orange', 'white', 'pink'):
                    self.assertNotIn(f'textures/blocks/flower_tulip_{color}.png', pack.namelist())
                self.assertNotIn('textures/blocks/double_plant_syringa_top.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
