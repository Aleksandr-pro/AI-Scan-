#!/usr/bin/env python3
"""Check carrot crop stages and pack contents; does not run Minecraft."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_young_carrots import SOURCE, BLOCKS, SIZE, HEIGHTS, prepare_stage

ROOT = Path('minecraft/realistic-dirt')


class YoungCarrotTests(unittest.TestCase):
    def test_source_and_early_stages(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '1afe8edf1195edef482ebd0e5fa9b37cd280f2d3172bce2c4566022b96b51c7b')
        for stage in range(3):
            with Image.open(BLOCKS / f'carrots_stage_{stage}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare_stage(stage).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                bbox = alpha.getbbox()
                self.assertEqual(bbox[3], SIZE)
                self.assertGreaterEqual(SIZE - bbox[1], HEIGHTS[stage]-2)
                self.assertLessEqual(SIZE - bbox[1], HEIGHTS[stage])
                self.assertGreater(sum(alpha.histogram()[128:]), 150)
                self.assertGreater(sum(alpha.crop((0, SIZE-4, SIZE, SIZE)).histogram()[128:]), 5)

    def test_scope_and_distributables(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('carrots', terrain)
        self.assertNotIn('carrots', blocks)
        self.assertEqual(hashlib.sha256((BLOCKS / 'carrots_stage_3.png').read_bytes()).hexdigest(),
                         'cc3bf8fe10443d9f9cd59090e40b4ba4b3e6ac906d574edacbf2c61d2d655f10')
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [2, 4, 0])
                self.assertEqual(manifest['modules'][0]['version'], [2, 4, 0])
                for stage in range(4):
                    path = f'textures/blocks/carrots_stage_{stage}.png'
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/carrot.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
