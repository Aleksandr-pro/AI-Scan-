#!/usr/bin/env python3
"""Four tall-grass pairs and pack checks; this does not render Bedrock."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_tall_grass import SOURCES, BLOCKS, SIZE, HEIGHT, JOIN_BAND, extract, prepared_plants

ROOT = Path('minecraft/realistic-dirt')
OLD = {
    '7fe5d573c09301370069cf0c8fb59375bb693cfff3e84e1feff6c98464683b65',
    '1da538f92237a9f03be94b0b3a8933b2896b6ec8300d9e863e48115faf9d9ee2',
}
SHORT = [
    '2ab9ebb382553b5e8fa38bf7d62101f367fa8a0fa8f3cbb7222a6661b13c0e37',
    '2daaf801767bd0abb93a30c48c9189cf52ffd18ed8c4e6f64c79fb50a910b69b',
    '00713f1cdee452c7533e3d8236a164c5cd698cbaded3e12f5220825ca4e8d2e0',
    'a2383ca34235d4421feb21642a6bbd8f253192d2787740b7a557e79aeb7119d7',
    '2201b0a5357635c3e6bda28725b6ea57d6e4185f03018eeaa09e657045aafcbe',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TallGrassTests(unittest.TestCase):
    def test_four_inputs_and_matched_halves(self):
        self.assertEqual([digest(p) for p in SOURCES], [
            '79da4819f0d47e00edb8ff51ce2b11609f5e554551f34a8f49e9f1400c369694',
            '0e44835c9b05b054c2a48f1e89877787522ec3bcbc02d8405d888903c6e99f71',
        ])
        originals = [extract(s, h) for s in SOURCES for h in (0, 1)]
        plants = prepared_plants()
        self.assertEqual(len({hashlib.sha256(p.tobytes()).hexdigest() for p in plants}), 4)
        for i, plant in enumerate(plants):
            self.assertEqual((plant.mode, plant.size), ('RGBA', (SIZE, HEIGHT)))
            for rect in ((0, 0, SIZE, SIZE-JOIN_BAND), (0, SIZE+JOIN_BAND, SIZE, HEIGHT)):
                self.assertEqual(plant.crop(rect).tobytes(), originals[i].crop(rect).tobytes())
            self.assertEqual(plant.getpixel((0, 0))[3], 0)
            self.assertEqual(plant.getpixel((SIZE-1, HEIGHT-1))[3], 0)
            alpha = plant.getchannel('A')
            self.assertGreater(alpha.histogram()[0], SIZE*HEIGHT*.35)
            self.assertGreater(sum(alpha.histogram()[100:]), SIZE*HEIGHT*.15)
            # Regardless of variant, rows touching the split use the same image.
            self.assertEqual(plant.crop((0, SIZE-2, SIZE, SIZE+2)).tobytes(), plants[0].crop((0, SIZE-2, SIZE, SIZE+2)).tobytes())
            suffix = '' if i == 0 else f'_variant_{i}'
            for part, rect in [('top', (0, 0, SIZE, SIZE)), ('bottom', (0, SIZE, SIZE, HEIGHT))]:
                path = BLOCKS / f'double_plant_grass_{part}{suffix}.png'
                with Image.open(path) as image:
                    self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                    self.assertEqual(image.tobytes(), plant.crop(rect).tobytes())
                self.assertNotIn(digest(path), OLD)
        self.assertEqual([digest(BLOCKS / f'short_grass_variant_{i}.png') for i in range(5)], SHORT)

    def test_atlas_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        for part in ('top', 'bottom'):
            names = ['textures/blocks/double_plant_grass_' + part] + [f'textures/blocks/double_plant_grass_{part}_variant_{i}' for i in range(1, 4)]
            variants = terrain[f'tall_grass_{part}']['textures']['variations']
            self.assertEqual([v['path'] for v in variants], names)
            self.assertEqual([v['weight'] for v in variants], [1]*4)
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('tall_grass', blocks)
        self.assertNotIn('double_plant', blocks)
        self.assertNotIn('large_fern_top', terrain)
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 72, 0])
                self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
                archive_terrain = json.loads(archive.read('textures/terrain_texture.json'))['texture_data']
                for part in ('top', 'bottom'):
                    self.assertEqual(archive_terrain[f'tall_grass_{part}'], terrain[f'tall_grass_{part}'])
                    for i in range(4):
                        suffix = '' if i == 0 else f'_variant_{i}'
                        path = BLOCKS / f'double_plant_grass_{part}{suffix}.png'
                        self.assertEqual(archive.read(path.relative_to(ROOT).as_posix()), path.read_bytes())
                for i, checksum in enumerate(SHORT):
                    self.assertEqual(hashlib.sha256(archive.read(f'textures/blocks/short_grass_variant_{i}.png')).hexdigest(), checksum)
                self.assertNotIn('textures/blocks/double_plant_fern_top.png', archive.namelist())


if __name__ == '__main__':
    unittest.main()
