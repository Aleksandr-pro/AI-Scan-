#!/usr/bin/env python3
"""Static tests for smooth stone and slab assets, not an in-game render test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_smooth_stone import SOURCE, BLOCKS, BOX, make_textures

ROOT=Path('minecraft/realistic-dirt')
REFERENCE=Path('minecraft/smooth-stone-reference/vanilla-sample.json')
FACE='photo_smooth_stone'
SIDE='photo_smooth_stone_slab_side'
KEYS={'smooth_stone':FACE, 'smooth_stone_slab_top':FACE,
      'smooth_stone_slab_bottom':FACE,'smooth_stone_slab_side':SIDE}


class SmoothStoneTests(unittest.TestCase):
    def test_source_and_assets(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '7c07d59929d090dddf9f03df3a0ef249fce44a3d82ae3f3d0993d4d98df8532c')
        self.assertEqual(BOX,(221,35,1043,808))
        for name,expected in zip((FACE,SIDE),make_textures()):
            with Image.open(BLOCKS/(name+'.png')) as img:
                self.assertEqual(img.mode,'RGB')
                self.assertEqual(img.size,expected.size)
                self.assertEqual(img.tobytes(),expected.tobytes())
        with Image.open(BLOCKS/(SIDE+'.png')) as img:
            self.assertEqual(img.size,(128,128))
            self.assertEqual(img.crop((0,0,128,64)).tobytes(),img.crop((0,64,128,128)).tobytes())

    def test_keys_packaging_and_isolation(self):
        sample=json.loads(REFERENCE.read_text());old=sample['terrain'];blocks=sample['blocks']
        self.assertEqual(old['smooth_stone']['textures'],'textures/blocks/stone_slab_top')
        self.assertEqual(blocks['smooth_stone']['textures'],'smooth_stone')
        for name in ('smooth_stone_slab','smooth_stone_double_slab'):
            self.assertEqual(blocks[name]['textures'],{'up':'smooth_stone_slab_top',
                'down':'smooth_stone_slab_bottom','side':'smooth_stone_slab_side'})
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())
        data=terrain['texture_data']
        for key,texture in KEYS.items():
            self.assertEqual(data[key],{'textures':'textures/blocks/'+texture})
        # Do not replace the globally shared stone_slab textures or legacy
        # indexed arrays: repeaters, comparators and other slabs keep theirs.
        for key in ('stone_slab_top','stone_slab_bottom','stone_slab_side','repeater_floor','comparator_stone_slab'):
            self.assertNotIn(key,data)
        self.assertNotIn('smooth_stone',json.loads((ROOT/'blocks.json').read_text()))
        self.assertNotIn('smooth_stone_slab',json.loads((ROOT/'blocks.json').read_text()))
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json')),terrain)
                manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2, 4, 0])
                self.assertEqual(manifest['modules'][0]['version'],[2, 4, 0])
                for name in (FACE,SIDE):
                    self.assertEqual(z.read(f'textures/blocks/{name}.png'),(BLOCKS/(name+'.png')).read_bytes())
                self.assertNotIn('textures/blocks/stone_slab_top.png',z.namelist())
                self.assertNotIn('textures/blocks/stone_slab_side.png',z.namelist())


if __name__=='__main__':unittest.main()
