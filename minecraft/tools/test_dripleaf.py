#!/usr/bin/env python3
"""Static dripleaf UV layouts, generated textures and package checks."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from dripleaf_masks import MASKS
from prepare_dripleaf import SOURCE, BLOCKS, SIZE, LEAVES, textures

ROOT = Path('minecraft/realistic-dirt')


class DripleafTests(unittest.TestCase):
    def test_source_and_texture_layout(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         'c06a3b6e0d34ed0a525acdc08625ddd255eb08c9c609f75f727768c2bbe780f1')
        self.assertEqual(len(MASKS), 8)
        self.assertEqual(len(LEAVES), 4)
        generated = textures()
        self.assertEqual(len(generated), 14)
        for name, expected in generated.items():
            with Image.open(BLOCKS / f'{name}.png') as image:
                self.assertEqual((image.mode,image.size), ('RGBA',(SIZE,SIZE)))
                self.assertEqual(image.tobytes(),expected.tobytes())
                base = name.split('_variant_')[0]
                for y,row in enumerate(MASKS[base]):
                    for x,value in enumerate(row):
                        self.assertEqual(image.getchannel('A').getpixel((x*16+8,y*16+8)) >= 128, value == '#', f'{name}: {x},{y}')
        for kind in ('big_dripleaf_top','small_dripleaf_top'):
            hashes = {hashlib.sha256(generated[kind + (f'_variant_{i}' if i else '')].tobytes()).digest() for i in range(4)}
            self.assertEqual(len(hashes),4)

    def test_atlas_and_pack_contents(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        for kind in ('big_dripleaf_top','small_dripleaf_top'):
            self.assertEqual(terrain[kind]['textures']['variations'], [
                {'path':'textures/blocks/'+kind+(f'_variant_{i}' if i else ''),'weight':1}
                for i in range(4)])
        for kind in MASKS:
            if not kind.endswith('_top') or kind.endswith('stem_top'):
                self.assertNotIn(kind, terrain)  # unchanged vanilla atlas entries
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('big_dripleaf',blocks)
        self.assertNotIn('small_dripleaf_block',blocks)
        names = [f'textures/blocks/{name}.png' for name in textures()]
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path = Path('minecraft') / package
            self.assertLess(path.stat().st_size, 100*1024*1024)
            with zipfile.ZipFile(path) as pack:
                self.assertIsNone(pack.testzip())
                manifest = json.loads(pack.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1,91,0])
                self.assertEqual(manifest['modules'][0]['version'], [1,91,0])
                self.assertEqual(json.loads(pack.read('textures/terrain_texture.json')), json.loads((ROOT/'textures/terrain_texture.json').read_text()))
                for name in names:
                    self.assertEqual(pack.read(name), (ROOT / name).read_bytes())
                self.assertNotIn('textures/blocks/dripstone_block.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
