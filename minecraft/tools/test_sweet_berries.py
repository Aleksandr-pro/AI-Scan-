#!/usr/bin/env python3
"""Static sweet berry bush and archive checks; not an in-game test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_sweet_berries import SOURCE, BLOCKS, SIZE, HEIGHTS, prepare_stage

ROOT = Path('minecraft/realistic-dirt')


class SweetBerryTests(unittest.TestCase):
    def test_sources_and_textures(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'dc52e7b877e3812aeeab7cc2a6a4139e13a28bc7ccaeb95728af91661abc963f')
        outputs = []
        for stage in range(4):
            with Image.open(BLOCKS / f'sweet_berry_bush_stage{stage}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare_stage(stage).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                self.assertGreater(alpha.histogram()[0], 90000)
                self.assertGreater(sum(alpha.histogram()[128:]), 25000)
                bbox = alpha.getbbox()
                self.assertEqual(bbox[3], SIZE)
                self.assertGreaterEqual(SIZE-bbox[1], HEIGHTS[stage]-3)
                self.assertLessEqual(SIZE-bbox[1], HEIGHTS[stage])
                pixels = np.asarray(image).astype(int)
                red = (pixels[:,:,0] > pixels[:,:,1] * 1.5) & (pixels[:,:,0] > 100) & (pixels[:,:,3] > 128)
                if stage == 0:
                    self.assertLess(red.sum(), 25)
                else:
                    self.assertGreater(red.sum(), 100)
                outputs.append(image.tobytes())
        self.assertEqual(len({hashlib.sha256(output).digest() for output in outputs}), 4)

    def test_scope_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('sweet_berry_bush', blocks)
        for stage in range(4):
            self.assertNotIn(f'sweet_berry_bush_{stage}', terrain)
        self.assertFalse((ROOT / 'textures/items/sweet_berries.png').exists())
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [2, 2, 0])
                self.assertEqual(manifest['modules'][0]['version'], [2, 2, 0])
                for stage in range(4):
                    path = f'textures/blocks/sweet_berry_bush_stage{stage}.png'
                    self.assertEqual(archive.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/sweet_berries.png', archive.namelist())


if __name__ == '__main__':
    unittest.main()
