#!/usr/bin/env python3
"""Check new snow images and optionally compare every entry with prior pack.

Run from repo root: python minecraft/tools/test_snow_normal.py --baseline old.mcpack
Requires Pillow. These checks do not test rendering, FPS or import in Minecraft.
"""
import argparse
import io
import json
from pathlib import Path
import unittest
import zipfile
from PIL import Image, ImageChops

ROOT = Path('minecraft')
PACK = ROOT / 'realistic-dirt.mcpack'
BLOCKS = ROOT / 'realistic-dirt/textures/blocks'
BASELINE = None
MATERIALS = ('snow', 'realistic_snow_top')
NAMES = {f'textures/blocks/{material}{suffix}.png' for material in MATERIALS
         for suffix in ('', '_variant_1', '_variant_2', '_variant_3')}

class TestSnow(unittest.TestCase):
    def test_files_atlas_and_sides(self):
        with zipfile.ZipFile(PACK) as archive:
            self.assertIsNone(archive.testzip())
            self.assertLess(PACK.stat().st_size,100*1024*1024)
            manifest=json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['header']['version'],[2,7,7])
            self.assertTrue(all(m['version']==[2,7,7] for m in manifest['modules']))
            atlas=json.loads(archive.read('textures/terrain_texture.json'))['texture_data']
            blocks=json.loads(archive.read('blocks.json'))
            for key in ('snow','snow_layer'):
                self.assertEqual(blocks[key]['textures'],{'up':'realistic_snow_top','side':'snow','down':'snow'})
            self.assertNotIn('powder_snow',blocks)
            for material in MATERIALS:
                paths=[f'textures/blocks/{material}{suffix}' for suffix in ('','_variant_1','_variant_2','_variant_3')]
                self.assertEqual([v['path'] for v in atlas[material]['textures']['variations']],paths)
                self.assertEqual((BLOCKS/f'{material}_variant_0.png').read_bytes(),(BLOCKS/f'{material}.png').read_bytes())
                for path in paths:
                    data=archive.read(path+'.png')
                    self.assertEqual(data,(ROOT/'realistic-dirt'/(path+'.png')).read_bytes())
                    with Image.open(io.BytesIO(data)) as im:
                        self.assertEqual((im.size,im.mode),((512,512),'RGB'))
                        self.assertIsNone(ImageChops.difference(im.crop((0,0,1,512)),im.crop((511,0,512,512))).getbbox(),path)
                        self.assertIsNone(ImageChops.difference(im.crop((0,0,512,1)),im.crop((0,511,512,512))).getbbox(),path)
            for suffix in ('','_variant_1','_variant_2','_variant_3'):
                self.assertEqual(archive.read(f'textures/blocks/snow{suffix}.png'),archive.read(f'textures/blocks/realistic_snow_top{suffix}.png'))
            with Image.open(io.BytesIO(archive.read('textures/blocks/snow.png'))) as base:
                for index,rotation in [(1,Image.Transpose.ROTATE_90),(2,Image.Transpose.ROTATE_180),(3,Image.Transpose.ROTATE_270)]:
                    with Image.open(io.BytesIO(archive.read(f'textures/blocks/snow_variant_{index}.png'))) as variant:
                        self.assertIsNone(ImageChops.difference(base.transpose(rotation),variant).getbbox())

    def test_every_other_entry_unchanged(self):
        if BASELINE is None:self.skipTest('provide --baseline to compare every archive entry')
        with zipfile.ZipFile(BASELINE) as old, zipfile.ZipFile(PACK) as new:
            self.assertEqual(set(old.namelist())|{'textures/blocks/copper_block.png'},set(new.namelist()))
            for name in old.namelist():
                if name not in NAMES and name not in ('manifest.json','textures/terrain_texture.json'):
                    self.assertEqual(old.read(name),new.read(name),name)
            before=json.loads(old.read('textures/terrain_texture.json'))
            after=json.loads(new.read('textures/terrain_texture.json'))
            self.assertEqual(after['texture_data'].pop('copper_block'),{'textures':'textures/blocks/copper_block'})
            self.assertEqual(before,after)
            old_manifest=json.loads(old.read('manifest.json'))
            new_manifest=json.loads(new.read('manifest.json'))
            old_manifest['header']['version']=[2,7,7]
            for module in old_manifest['modules']:module['version']=[2,7,7]
            self.assertEqual(old_manifest,new_manifest)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path)
    args,rest=parser.parse_known_args();BASELINE=args.baseline
    unittest.main(argv=[__file__,*rest])
