#!/usr/bin/env python3
"""Check user leaf image extraction, mapping and distributable resources."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_leaf_litter import SOURCE, OUTPUT, COLORMAP, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class LeafLitterTests(unittest.TestCase):
    def test_source_and_transparency(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'b67e806d44410cddd2a38d2c231d0b5334116aaa677982c3ee701f467cc2cb16')
        with Image.open(SOURCE) as source:
            self.assertEqual(source.size, (1024, 1024))
            self.assertEqual(source.mode, 'RGB')
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            alpha = image.getchannel('A')
            histogram = alpha.histogram()
            self.assertGreater(histogram[0], SIZE*SIZE*.35)
            self.assertGreater(histogram[255], SIZE*SIZE*.20)
            for point in ((3, 3), (15, 6), (25, 25), (265, 90), (390, 325)):
                self.assertEqual(alpha.getpixel(point), 0, point)
            for point in ((50, 80), (88, 59), (256, 256), (470, 50), (160, 32)):
                self.assertGreater(alpha.getpixel(point), 220, point)
            r, g, b, a = image.getpixel((88, 59))
            self.assertGreater(r, g); self.assertGreater(g, b)
        with Image.open(COLORMAP) as colormap:
            self.assertEqual((colormap.mode, colormap.size), ('RGB', (256, 256)))
            self.assertEqual(colormap.getextrema(), ((255, 255),)*3)

    def test_both_pack_mappings(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text(encoding='utf-8'))['texture_data']
        self.assertEqual(atlas['leaf_litter']['textures'], 'textures/blocks/leaf_litter')
        blocks = json.loads((ROOT / 'blocks.json').read_text(encoding='utf-8'))
        self.assertNotIn('leaf_litter', blocks)  # retain vanilla block mapping, sound and item
        self.assertFalse((ROOT / 'textures/items/leaf_litter.png').exists())
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 70, 0])
                self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
                for source in (OUTPUT, COLORMAP):
                    self.assertEqual(archive.read(source.relative_to(ROOT).as_posix()), source.read_bytes())
                self.assertEqual(json.loads(archive.read('textures/terrain_texture.json'))['texture_data']['leaf_litter'], atlas['leaf_litter'])
                self.assertNotIn('textures/items/leaf_litter.png', archive.namelist())
                self.assertNotIn('leaf-litter-reference/source.jpg', archive.namelist())


if __name__ == '__main__':
    unittest.main()
