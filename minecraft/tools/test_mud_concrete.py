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
OPTIMIZED={f'textures/blocks/{name}.png' for name in (
    'amethyst_block_variant_1','amethyst_block_variant_2','amethyst_block_variant_3',
    'copper_ore_variant_1','copper_ore_variant_2','copper_ore_variant_3',
    'iron_ore_variant_1','iron_ore_variant_2','iron_ore_variant_3','stone_andesite')}
COLORS=('black','white','pink')
NEW={'textures/blocks/flower_pot.png','textures/blocks/oak_shelf.png'}

class TestMudConcrete(unittest.TestCase):
    def test_images_and_atlas(self):
        with zipfile.ZipFile(PACK) as z:
            self.assertIsNone(z.testzip())
            terrain=json.loads(z.read('textures/terrain_texture.json'))['texture_data']
            for key,name in [('packed_mud','packed_mud'),('white_concrete','concrete_white'),('red_concrete','concrete_red'),('stripped_oak_log_side','stripped_oak_log'),('andesite','stone_andesite'),('andesite_slab','stone_andesite'),('andesite_wall','stone_andesite')]:
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
            self.assertEqual(terrain['flower_pot']['textures'],'textures/blocks/flower_pot')
            self.assertEqual(terrain['oak_shelf']['textures'],['textures/blocks/oak_shelf'])
            with Image.open(io.BytesIO(z.read('textures/blocks/flower_pot.png'))) as pot:
                self.assertEqual((pot.size,pot.mode),((512,512),'RGBA'))
                with Image.open(ROOT/'pot-shelf-reference/vanilla-flower-pot.png') as vanilla:
                    self.assertIsNone(ImageChops.difference(pot.getchannel('A'),vanilla.convert('RGBA').getchannel('A').resize((512,512),Image.Resampling.NEAREST)).getbbox())
            with Image.open(io.BytesIO(z.read('textures/blocks/oak_shelf.png'))) as shelf:
                self.assertEqual((shelf.size,shelf.mode),((512,512),'RGB'))
                # Powered variants must remain different where supports join.
                self.assertIsNotNone(ImageChops.difference(shelf.crop((0,256,256,384)),shelf.crop((0,384,256,512))).getbbox())
            self.assertEqual(json.loads(z.read('manifest.json'))['header']['version'],[2,7,7])
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
            for key in ('flower_pot','oak_shelf'): after['texture_data'].pop(key)
            self.assertEqual(before,after)
            self.assertEqual(json.loads(old.read('blocks.json')),json.loads(new.read('blocks.json')))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args,unittest_args=parser.parse_known_args()
    BASELINE=args.baseline
    unittest.main(argv=[__file__,*unittest_args])
