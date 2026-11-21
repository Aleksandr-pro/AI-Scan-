#!/usr/bin/env python3
"""Check generated seagrass flipbook strips and packages (not game rendering)."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image, ImageOps
from prepare_seagrass import SOURCE, BLOCKS, SIZE, SHORT_FRAMES, TALL_FRAMES, canvas, sway, strips

ROOT = Path('minecraft/realistic-dirt')


class SeagrassTests(unittest.TestCase):
    def test_deterministic_strips_and_continuous_halves(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'fa5d82f4055f742925752fe0b9b63cce089298e193993e085126384a83d3762c')
        expected = strips()
        self.assertEqual(len(expected), 5)
        for name, generated in expected.items():
            with Image.open(BLOCKS / name) as actual:
                self.assertEqual(actual.mode, 'RGBA')
                n = SHORT_FRAMES if name == 'seagrass.png' else TALL_FRAMES
                self.assertEqual(actual.size, (SIZE, SIZE*n))
                self.assertEqual(actual.tobytes(), generated.tobytes())
                alpha = actual.getchannel('A')
                self.assertGreater(alpha.histogram()[0], 10000)
                self.assertGreater(sum(alpha.histogram()[128:]), 10000)
                first = actual.crop((0,0,SIZE,SIZE))
                fourth = actual.crop((0,4*SIZE,SIZE,5*SIZE))
                self.assertNotEqual(first.tobytes(), fourth.tobytes())
        tall = canvas(SIZE*2)
        for i in range(TALL_FRAMES):
            frame = sway(tall, i, TALL_FRAMES)
            for side in 'ab':
                top = expected[f'seagrass_doubletall_top_{side}.tga'].crop((0, SIZE*i, SIZE, SIZE*(i+1)))
                bottom = expected[f'seagrass_doubletall_bottom_{side}.tga'].crop((0, SIZE*i, SIZE, SIZE*(i+1)))
                combined = Image.new('RGBA', (SIZE, SIZE*2)); combined.paste(top, (0,0)); combined.paste(bottom, (0,SIZE))
                self.assertEqual(combined.tobytes(), (frame if side == 'a' else ImageOps.mirror(frame)).tobytes())

    def test_pack_scope_and_archive_contents(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        for key in ('seagrass_short', 'seagrass_tall_bot_a', 'seagrass_tall_bot_b', 'seagrass_tall_top_a', 'seagrass_tall_top_b', 'kelp_a'):
            self.assertNotIn(key, terrain)  # inherit vanilla atlas and animation entries
        self.assertNotIn('seagrass', json.loads((ROOT / 'blocks.json').read_text()))
        names = ['seagrass.png'] + [f'seagrass_doubletall_{half}_{side}.tga' for side in 'ab' for half in ('top','bottom')]
        for packname in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / packname) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 98, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 98, 0])
                for name in names:
                    path = 'textures/blocks/' + name
                    self.assertEqual(pack.read(path), (BLOCKS / name).read_bytes())
                self.assertNotIn('textures/flipbook_textures.json', pack.namelist())
                self.assertNotIn('textures/blocks/kelp_a.tga', pack.namelist())
                self.assertNotIn('textures/blocks/seagrass_carried.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
