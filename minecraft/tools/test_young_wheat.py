#!/usr/bin/env python3
"""Check early wheat stages and distributions; does not run Minecraft."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_young_wheat import SOURCE, BLOCKS, HEIGHTS, SIZE, prepare_stages

ROOT = Path('minecraft/realistic-dirt')


class YoungWheatTests(unittest.TestCase):
    def test_photo_and_prepared_stages(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '88d259db1d2995f702e64b5ee32f6ff16d258b48e98f2819235dd7b5bf53c4e0')
        prepared = prepare_stages()
        self.assertEqual(len(prepared), 5)
        for stage, image in enumerate(prepared):
            with Image.open(BLOCKS / f'wheat_stage_{stage}.png') as saved:
                self.assertEqual((saved.mode, saved.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(saved.tobytes(), image.tobytes())
                alpha = saved.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                bbox = alpha.getbbox()
                self.assertEqual(bbox[3], SIZE)
                self.assertGreaterEqual(SIZE - bbox[1], HEIGHTS[stage] - 2)
                self.assertLessEqual(SIZE - bbox[1], HEIGHTS[stage])
                self.assertGreater(sum(alpha.histogram()[128:]), 200)

    def test_package_scope_and_mature_wheat_retained(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('wheat', terrain)
        self.assertNotIn('wheat', blocks)
        self.assertEqual(hashlib.sha256((BLOCKS / 'wheat_stage_7.png').read_bytes()).hexdigest(),
                         'cd63d741efc3aac41a1629085b602da08f33d8c5b9a04924f97e79a682145701')
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as z:
                self.assertIsNone(z.testzip())
                manifest = json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [2, 1, 0])
                self.assertEqual(manifest['modules'][0]['version'], [2, 1, 0])
                for i in (*range(5), 7):
                    path = f'textures/blocks/wheat_stage_{i}.png'
                    self.assertEqual(z.read(path), (ROOT / path).read_bytes())
                for i in (5, 6):
                    path = f'textures/blocks/wheat_stage_{i}.png'
                    self.assertEqual(z.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/wheat.png', z.namelist())


if __name__ == '__main__':
    unittest.main()
