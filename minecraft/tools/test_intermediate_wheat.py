#!/usr/bin/env python3
"""Verify intermediate wheat textures and archives, not Minecraft rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_intermediate_wheat import SOURCE, BLOCKS, SIZE, HEIGHTS, prepare_stage

ROOT = Path('minecraft/realistic-dirt')


class IntermediateWheatTests(unittest.TestCase):
    def test_source_and_extractions(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'ed2385052938891bda7dae4f6462af2f1c83e5b0de9225df7de48c79379738fb')
        with Image.open(SOURCE) as src:
            self.assertEqual((src.size, src.mode), ((1536, 1024), 'RGBA'))
        for stage in (5, 6):
            with Image.open(BLOCKS / f'wheat_stage_{stage}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare_stage(stage).tobytes())
                alpha = image.getchannel('A')
                self.assertEqual(alpha.getpixel((0, 0)), 0)
                bbox = alpha.getbbox()
                self.assertEqual(bbox[3], SIZE)
                self.assertGreaterEqual(SIZE-bbox[1], HEIGHTS[stage]-2)
                self.assertLessEqual(SIZE-bbox[1], HEIGHTS[stage])
                self.assertGreater(sum(alpha.histogram()[128:]), 25000)

    def test_eight_stages_and_pack_contents(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('wheat', terrain)
        self.assertNotIn('wheat', blocks)
        self.assertEqual(hashlib.sha256((BLOCKS / 'wheat_stage_7.png').read_bytes()).hexdigest(),
                         'cd63d741efc3aac41a1629085b602da08f33d8c5b9a04924f97e79a682145701')
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [2, 4, 0])
                self.assertEqual(manifest['modules'][0]['version'], [2, 4, 0])
                for stage in range(8):
                    path = f'textures/blocks/wheat_stage_{stage}.png'
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())
                self.assertNotIn('textures/items/wheat.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
