#!/usr/bin/env python3
"""Static checks for photo glass blocks; not a Minecraft render test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_stained_glass import REFERENCE, BLOCKS, SIZE, TINTS, prepare

ROOT=Path('minecraft/realistic-dirt')
HASHES={
    'black':'041cd8c7022432c1d5eaf8844dd84af1e2a7e32a2d512cb8eb490b9ac974c066',
    'white':'8cfba7ca4c4c1d4946ab0d504a51901c4f93e960ce398da506800704de8c3aaa',
    'pink':'ba7800c13dd79a3433d48a4569934388ded1d3238b28e3f930c053f982f88d44',
}


class StainedGlassTests(unittest.TestCase):
    def test_originals_and_processed_images(self):
        for color,tint in TINTS.items():
            with self.subTest(color=color):
                self.assertEqual(hashlib.sha256((REFERENCE/f'{color}.jpg').read_bytes()).hexdigest(),HASHES[color])
                with Image.open(BLOCKS/f'photo_stained_glass_{color}.png') as im:
                    self.assertEqual((im.mode,im.size),('RGBA',(SIZE,SIZE)))
                    self.assertEqual(im.tobytes(),prepare(color).tobytes())
                    # All the centre is a single semitransparent colour: no JPG checkerboard.
                    centre=im.crop((16,16,SIZE-16,SIZE-16))
                    for band in centre.split():
                        self.assertEqual(band.getextrema()[0],band.getextrema()[1])
                    self.assertEqual(centre.getpixel((0,0))[3],tint[3])
                    for actual,expected in zip(centre.getpixel((0,0))[:3],tint[:3]):
                        self.assertLessEqual(abs(actual-expected),1)
                    # Detailed opaque frame on all four sides.
                    for xy in ((SIZE//2,3),(SIZE//2,SIZE-4),(3,SIZE//2),(SIZE-4,SIZE//2)):
                        self.assertGreater(im.getpixel(xy)[3],240)
                    self.assertGreater(len({im.getpixel((x,y)) for x in range(SIZE) for y in range(10)}),50)

    def test_isolation_and_packages(self):
        blocks=json.loads((ROOT/'blocks.json').read_text())
        atlas=json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        for color in TINTS:
            key=f'photo_stained_glass_{color}'
            self.assertEqual(blocks[f'{color}_stained_glass'],{'sound':'glass','textures':key})
            self.assertNotIn(f'{color}_stained_glass_pane',blocks)
            self.assertNotIn(f'{color}_stained_glass',atlas)
            self.assertFalse((BLOCKS/f'glass_{color}.png').exists())
            self.assertEqual(atlas[key],{'textures':f'textures/blocks/{key}'})
        self.assertNotIn('stained_glass',blocks)
        self.assertNotIn('stained_glass',atlas)
        for name in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/name
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                packed_blocks=json.loads(z.read('blocks.json'))
                packed_atlas=json.loads(z.read('textures/terrain_texture.json'))['texture_data']
                self.assertEqual(json.loads(z.read('manifest.json'))['header']['version'],[1,98,0])
                for color in TINTS:
                    key=f'photo_stained_glass_{color}'
                    self.assertEqual(packed_blocks[f'{color}_stained_glass'],blocks[f'{color}_stained_glass'])
                    self.assertEqual(packed_atlas[key],atlas[key])
                    self.assertEqual(z.read(f'textures/blocks/{key}.png'),(BLOCKS/f'{key}.png').read_bytes())
                    self.assertNotIn(f'textures/blocks/glass_{color}.png',z.namelist())
                    self.assertNotIn(f'{color}_stained_glass_pane',packed_blocks)


if __name__=='__main__':unittest.main()
