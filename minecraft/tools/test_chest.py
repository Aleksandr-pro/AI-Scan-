#!/usr/bin/env python3
"""Static chest atlas and package checks; not a Minecraft rendering test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_chest import REF, ROOT, SCALE, atlas, load, widen


class ChestTests(unittest.TestCase):
    def test_sources(self):
        expected = {
            'front.jpg': 'd193364566117408a156192845fb3bc9fbee10f012f74f782d3070255b793222',
            'side.jpg': 'd8402e16fa11c8e3863bb95a9d14f0a5979d0d6d3eb03bdfd47a8f10af37ac4a',
            'top.jpg': '722768df7e15d3e23cddcd2dec478c39b4e87ad3196e664fdd2df6e6beb84ca0',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((REF / name).read_bytes()).hexdigest(), digest)

    def test_atlases_match_generator_and_vanilla_footprint(self):
        for wide, name in ((False, 'normal'), (True, 'double_normal')):
            with Image.open(ROOT / f'textures/entity/chest/{name}.png') as actual, Image.open(REF / ('vanilla-double-mask.png' if wide else 'vanilla-normal-mask.png')) as vanilla:
                self.assertEqual(actual.mode, 'RGBA')
                self.assertEqual(actual.size, (vanilla.width*SCALE, vanilla.height*SCALE))
                self.assertEqual(actual.tobytes(), atlas(wide).tobytes())
                # Each pixel occupied in the vanilla UV net is fully opaque.
                alpha = actual.getchannel('A').resize(vanilla.size, Image.Resampling.NEAREST)
                for x in range(vanilla.width):
                    for y in range(vanilla.height):
                        if vanilla.getpixel((x, y))[3]:
                            self.assertEqual(alpha.getpixel((x, y)), 255)
        # Widen keeps the center of the original photograph exactly once.
        src = load('front')
        out = widen(src)
        center = src.crop((round(src.width*.32), 0, round(src.width*.68), src.height))
        start = round(src.width*.09) + (out.width - round(src.width*.09) - center.width - (src.width - round(src.width*.91)))//2
        self.assertEqual(out.crop((start, 0, start+center.width, center.height)).tobytes(), center.tobytes())

    def test_inventory_scope_and_packages(self):
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        textures = blocks['chest']['textures']
        self.assertEqual(textures['south'], 'photo_chest_front')
        self.assertEqual(textures['up'], 'photo_chest_top')
        self.assertEqual(textures['east'], 'photo_chest_side')
        self.assertNotIn('trapped_chest', blocks)
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        names = [f'textures/entity/chest/{n}.png' for n in ('normal', 'double_normal')]
        for name in ('front', 'side', 'top'):
            key = 'photo_chest_' + name
            self.assertEqual(terrain[key]['textures'], 'textures/blocks/' + key)
            path = f'textures/blocks/{key}.png'
            names.append(path)
            with Image.open(ROOT / path) as actual:
                self.assertEqual(actual.size, (512, 512))
                self.assertEqual(actual.tobytes(), load(name).resize((512, 512), Image.Resampling.LANCZOS).tobytes())
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as z:
                self.assertIsNone(z.testzip())
                manifest = json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 90, 0])
                for name in names + ['blocks.json', 'textures/terrain_texture.json']:
                    self.assertEqual(z.read(name), (ROOT / name).read_bytes())
                for other in ('trapped', 'double_trapped', 'ender', 'copper'):
                    self.assertFalse(any(p.startswith('textures/entity/chest/' + other) for p in z.namelist()))
                self.assertNotIn('textures/blocks/chest_side.png', z.namelist())
                self.assertNotIn('textures/blocks/chest_top.png', z.namelist())


if __name__ == '__main__':
    unittest.main()
