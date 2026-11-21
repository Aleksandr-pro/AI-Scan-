#!/usr/bin/env python3
"""Static checks of ordinary vine variants and packages, not Minecraft rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_vines import SOURCE, BLOCKS, SIZE, CROPS, prepare

ROOT = Path('minecraft/realistic-dirt')


class VineTests(unittest.TestCase):
    def test_source_and_six_variants(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'b3ce1bdaca4858c21b2c33eafefddfee14dc2d71d8fb63677a902423a8c4756c')
        self.assertEqual(len(CROPS), 6)
        hashes = []
        for i in range(6):
            name = 'vine' if i == 0 else f'vine_variant_{i}'
            with Image.open(BLOCKS / f'{name}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare(i).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertGreater(alpha.histogram()[0], 30000)
                self.assertGreater(sum(alpha.histogram()[128:]), 1500)
                self.assertEqual(alpha.getbbox()[1], 0)
                if i == 5:
                    self.assertLess(alpha.getbbox()[3], SIZE//2+10)
                else:
                    self.assertGreater(alpha.getbbox()[3], SIZE-10)
                hashes.append(hashlib.sha256(image.tobytes()).digest())
        self.assertEqual(len(set(hashes)), 6)

    def test_atlas_scope_and_packs(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        expected = [{'path': 'textures/blocks/vine' + (f'_variant_{i}' if i else ''), 'weight': 1}
                    for i in range(6)]
        self.assertEqual(terrain['vine']['textures']['variations'], expected)
        self.assertNotIn('vine_carried', terrain)
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('vine', blocks)
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 89, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 89, 0])
                self.assertEqual(json.loads(pack.read('textures/terrain_texture.json'))['texture_data']['vine'], terrain['vine'])
                for item in expected:
                    path = item['path'] + '.png'
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/blocks/vine_carried.png', pack.namelist())
                self.assertNotIn('textures/blocks/cave_vines_body.png', pack.namelist())
                self.assertNotIn('textures/blocks/weeping_vines.png', pack.namelist())
                self.assertNotIn('textures/blocks/twisting_vines_bottom.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
