#!/usr/bin/env python3
"""Check potato crop textures and packages, not Minecraft rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_potatoes import SOURCE, BLOCKS, SIZE, HEIGHTS, prepare_stage

ROOT = Path('minecraft/realistic-dirt')


class PotatoTests(unittest.TestCase):
    def test_source_and_textures(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'cf10435575c3dcc948553a17fcd43fd4f90caa960583cd85a5ac69d42973c6fc')
        images = []
        for stage in range(4):
            with Image.open(BLOCKS / f'potatoes_stage_{stage}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare_stage(stage).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertGreater(alpha.histogram()[0], 160000)
                self.assertGreater(sum(alpha.histogram()[128:]), 10000)
                bbox = alpha.getbbox()
                self.assertEqual(bbox[3], SIZE)
                self.assertGreaterEqual(SIZE-bbox[1], HEIGHTS[stage]-3)
                self.assertLessEqual(SIZE-bbox[1], HEIGHTS[stage])
                if stage in (2, 3):
                    pixels = np.asarray(image)
                    self.assertGreater(((pixels[:,:,:3].min(axis=2) > 200) & (pixels[:,:,3] > 128)).sum(), 100)
                images.append(image.tobytes())
        self.assertEqual(len({hashlib.sha256(image).digest() for image in images}), 4)

    def test_scope_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        # Bedrock's vanilla potatoes atlas array selects the four stage paths.
        self.assertNotIn('potatoes', terrain)
        self.assertNotIn('potatoes', blocks)
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 82, 0])
                self.assertEqual(manifest['modules'][0]['version'], [1, 82, 0])
                for stage in range(4):
                    path = f'textures/blocks/potatoes_stage_{stage}.png'
                    self.assertEqual(archive.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/potato.png', archive.namelist())
                self.assertNotIn('textures/items/potato_baked.png', archive.namelist())


if __name__ == '__main__':
    unittest.main()
