#!/usr/bin/env python3
"""Static source, texture, atlas and archive checks; not a Minecraft render test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_moss_lilies import SOURCE, BLOCKS, SIZE, LILY_BOXES, MOSS_BOXES, lily, moss

ROOT = Path('minecraft/realistic-dirt')


def name(kind, i):
    return kind + (f'_variant_{i}' if i else '')


class MossLilyTests(unittest.TestCase):
    def test_source_and_lily_variations(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '820224a0858b08891fbb4c9b23f924cab470a320f09215ff7d86f9ba1a46651c')
        self.assertEqual(len(LILY_BOXES), 6)
        seen = set()
        for i in range(6):
            with Image.open(BLOCKS / (name('waterlily', i) + '.png')) as im:
                self.assertEqual((im.mode, im.size), ('RGBA', (SIZE,SIZE)))
                self.assertEqual(im.tobytes(), lily(i).tobytes())
                alpha = im.getchannel('A')
                self.assertEqual(alpha.getpixel((0,0)), 0)
                self.assertGreater(alpha.histogram()[0], 20000)
                self.assertGreater(sum(alpha.histogram()[128:]), 15000)
                seen.add(hashlib.sha256(im.tobytes()).digest())
        self.assertEqual(len(seen), 6)

    def test_moss_variants_share_tileable_borders(self):
        self.assertEqual(len(MOSS_BOXES), 4)
        expected = moss()
        seen = set()
        arrays = []
        for i in range(4):
            with Image.open(BLOCKS / (name('moss_block', i) + '.png')) as im:
                self.assertEqual((im.mode, im.size), ('RGB', (SIZE,SIZE)))
                self.assertEqual(im.tobytes(), expected[i].tobytes())
                arrays.append(np.array(im))
                seen.add(hashlib.sha256(im.tobytes()).digest())
        self.assertEqual(len(seen), 4)
        for a in arrays:
            np.testing.assert_array_equal(a[0], a[-1])
            np.testing.assert_array_equal(a[:,0], a[:,-1])
            np.testing.assert_array_equal(a[:32], arrays[0][:32])
            np.testing.assert_array_equal(a[-32:], arrays[0][-32:])
            np.testing.assert_array_equal(a[:,:32], arrays[0][:,:32])
            np.testing.assert_array_equal(a[:,-32:], arrays[0][:,-32:])

    def test_atlas_and_archives(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        lily_tex = terrain['waterlily']['textures'][0]
        self.assertEqual(lily_tex['tint_color'].lower(), '#ffffff')
        for kind, count, entry in (('waterlily', 6, lily_tex), ('moss_block', 4, terrain['moss_block']['textures'])):
            self.assertEqual(entry['variations'], [{'path': 'textures/blocks/' + name(kind,i), 'weight': 1} for i in range(count)])
        self.assertNotIn('waterlily_carried', terrain)
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        for key in ('waterlily', 'moss_block', 'moss_carpet'):
            self.assertNotIn(key, blocks)
        names = ['textures/blocks/' + name(kind,i) + '.png' for kind,count in (('waterlily',6),('moss_block',4)) for i in range(count)]
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / package) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1,92,0])
                self.assertEqual(manifest['modules'][0]['version'], [1,92,0])
                self.assertEqual(json.loads(pack.read('textures/terrain_texture.json')), json.loads((ROOT/'textures/terrain_texture.json').read_text()))
                for p in names:
                    self.assertEqual(pack.read(p), (ROOT / p).read_bytes())
                self.assertNotIn('textures/blocks/carried_waterlily.png', pack.namelist())
                self.assertNotIn('textures/blocks/pale_moss_block.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
