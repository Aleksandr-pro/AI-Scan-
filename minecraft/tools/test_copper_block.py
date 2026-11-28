#!/usr/bin/env python3
"""Check copper-block texture and preservation of the previous pack (Pillow).

Pass --baseline /path/to/v2.7.6.mcpack to compare every archive entry.
These tests do not verify in-game rendering or performance.
"""
import argparse
import io
import json
from pathlib import Path
import unittest
import zipfile
from PIL import Image
import prepare_copper_block
from build_complete_snow_bundle import png_semantic_content

ROOT=Path('minecraft')
PACK=ROOT/'realistic-dirt.mcpack'
BASELINE=None
FILE='textures/blocks/copper_block.png'


def vanilla(name):
    raw=(ROOT/'catalog-source/bedrock-1.26.30.5'/name).read_text(encoding='utf-8-sig')
    return json.loads('\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('//')))

class CopperBlockTests(unittest.TestCase):
    def test_photo_atlas_and_vanilla_mappings(self):
        blocks=vanilla('vanilla-blocks.json')
        atlas=vanilla('vanilla-terrain.json')['texture_data']
        self.assertEqual(atlas['copper_block']['textures'],'textures/blocks/copper_block')
        for key in ('copper_block','waxed_copper'):
            self.assertEqual(blocks[key]['textures'],'copper_block')
        for key in ('exposed_copper','weathered_copper','oxidized_copper','cut_copper'):
            self.assertNotEqual(blocks[key]['textures'],'copper_block')
        with zipfile.ZipFile(PACK) as pack:
            self.assertIsNone(pack.testzip())
            self.assertLess(PACK.stat().st_size,100*1024*1024)
            m=json.loads(pack.read('manifest.json'))
            self.assertEqual(m['header']['version'],[2,7,11])
            self.assertTrue(all(x['version']==[2,7,11] for x in m['modules']))
            terrain=json.loads(pack.read('textures/terrain_texture.json'))['texture_data']
            self.assertEqual(terrain['copper_block'],{'textures':'textures/blocks/copper_block'})
            data=pack.read(FILE)
            self.assertEqual(data,(ROOT/'realistic-dirt'/FILE).read_bytes())
            with Image.open(io.BytesIO(data)) as image:
                self.assertEqual((image.mode,image.size),('RGB',(512,512)))
                self.assertEqual(image.tobytes(),prepare_copper_block.prepare().tobytes(),'whole supplied photo including bevel should be retained')

    def test_other_files_preserved(self):
        if BASELINE is None:self.skipTest('pass --baseline to compare the previous archive')
        with zipfile.ZipFile(BASELINE) as old, zipfile.ZipFile(PACK) as new:
            self.assertEqual(set(new.namelist()),set(old.namelist())|{FILE,'textures/blocks/ice.png'})
            for name in old.namelist():
                if name=='textures/blocks/clay.png':
                    self.assertEqual(png_semantic_content(new.read(name)),png_semantic_content(old.read(name)),name)
                elif name not in ('manifest.json','textures/terrain_texture.json'):
                    self.assertEqual(new.read(name),old.read(name),name)
            before=json.loads(old.read('textures/terrain_texture.json'))
            after=json.loads(new.read('textures/terrain_texture.json'))
            self.assertEqual(after['texture_data'].pop('copper_block'),{'textures':'textures/blocks/copper_block'})
            self.assertEqual(after['texture_data'].pop('ice'),{'textures':'textures/blocks/ice'})
            self.assertEqual(after,before)
            before=json.loads(old.read('manifest.json'))
            after=json.loads(new.read('manifest.json'))
            before['header']['version']=[2,7,11]
            for item in before['modules']:item['version']=[2,7,11]
            self.assertEqual(before,after)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path)
    args,rest=parser.parse_known_args();BASELINE=args.baseline
    unittest.main(argv=[__file__,*rest])
