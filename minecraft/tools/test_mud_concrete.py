#!/usr/bin/env python3
"""Check block images and archive; optionally compare prior pack with --baseline.

Requires Pillow. Minecraft rendering, import and mip behavior require game tests.
"""
import argparse
import io
import json
from pathlib import Path
import unittest
import zipfile
from PIL import Image, ImageChops

ROOT=Path('minecraft')
PACK=ROOT/'realistic-dirt.mcpack'
BASELINE=None
OPTIMIZED={'textures/blocks/log_big_oak.png'}
COLORS=('black','white','pink')
NEW={f'textures/blocks/photo_stained_glass_{c}_pane_edge.png' for c in COLORS}

class TestMudConcrete(unittest.TestCase):
    def test_images_and_atlas(self):
        with zipfile.ZipFile(PACK) as z:
            self.assertIsNone(z.testzip())
            terrain=json.loads(z.read('textures/terrain_texture.json'))['texture_data']
            for key,name in [('packed_mud','packed_mud'),('white_concrete','concrete_white'),('red_concrete','concrete_red'),('stripped_oak_log_side','stripped_oak_log')]:
                self.assertEqual(terrain[key]['textures'],f'textures/blocks/{name}')
                data=z.read(f'textures/blocks/{name}.png')
                self.assertEqual(data,(ROOT/f'realistic-dirt/textures/blocks/{name}.png').read_bytes())
                with Image.open(io.BytesIO(data)) as im:
                    self.assertEqual((im.size,im.mode),((512,512),'RGB'))
                    # Exact edge equality avoids visible hard jumps; no claim
                    # is made for game filtering/mipmapping or corner UVs.
                    self.assertIsNone(ImageChops.difference(im.crop((0,0,1,512)),im.crop((511,0,512,512))).getbbox())
                    self.assertIsNone(ImageChops.difference(im.crop((0,0,512,1)),im.crop((0,511,512,512))).getbbox())
            blocks=json.loads(z.read('blocks.json'))
            for color in COLORS:
                face=f'photo_stained_glass_{color}'
                edge=f'{face}_pane_edge'
                self.assertEqual(blocks[f'{color}_stained_glass_pane'],{
                    'sound':'glass','textures':{'down':face,'east':edge,'north':face,
                                                'south':face,'up':face,'west':face}})
                self.assertEqual(terrain[edge]['textures'],f'textures/blocks/{edge}')
                with Image.open(io.BytesIO(z.read(f'textures/blocks/{face}.png'))) as image:
                    self.assertEqual(image.mode,'RGBA')
                    self.assertLess(image.getpixel((128,128))[3],255)
                    self.assertGreater(image.getpixel((128,0))[3],200)
                with Image.open(io.BytesIO(z.read(f'textures/blocks/{edge}.png'))) as image:
                    self.assertEqual((image.size,image.mode),((256,256),'RGBA'))
            self.assertEqual(json.loads(z.read('manifest.json'))['header']['version'],[2,7,3])
            self.assertLess(PACK.stat().st_size,100*1024*1024)

    def test_existing_pack(self):
        if not BASELINE:self.skipTest('pass --baseline to compare previous archive')
        with zipfile.ZipFile(BASELINE) as old, zipfile.ZipFile(PACK) as new:
            self.assertEqual(set(new.namelist()),set(old.namelist())|NEW)
            for name in old.namelist():
                a,b=old.read(name),new.read(name)
                if name in ('manifest.json','textures/terrain_texture.json','blocks.json'):continue
                if name in OPTIMIZED:
                    with Image.open(io.BytesIO(a)) as im_a, Image.open(io.BytesIO(b)) as im_b:
                        self.assertEqual((im_a.size,im_a.mode,im_a.tobytes()),(im_b.size,im_b.mode,im_b.tobytes()),name)
                else:self.assertEqual(a,b,name)
            before=json.loads(old.read('textures/terrain_texture.json'))
            after=json.loads(new.read('textures/terrain_texture.json'))
            for color in COLORS: after['texture_data'].pop(f'photo_stained_glass_{color}_pane_edge')
            self.assertEqual(before,after)
            before=json.loads(old.read('blocks.json'))
            after=json.loads(new.read('blocks.json'))
            for color in COLORS:after.pop(f'{color}_stained_glass_pane')
            self.assertEqual(before,after)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args,unittest_args=parser.parse_known_args()
    BASELINE=args.baseline
    unittest.main(argv=[__file__,*unittest_args])
