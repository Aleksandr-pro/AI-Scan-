#!/usr/bin/env python3
"""Verify white shulker UVs and all anvil damage textures, not game rendering."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
import prepare_white_shulker as shulker
import prepare_anvil as anvil

ROOT=Path('minecraft/realistic-dirt')


class WhiteShulkerAnvilTests(unittest.TestCase):
    def test_references_and_white_shulker_uv(self):
        hashes={'body.jpg':'09afedcedaac7b8221c926668fc96238f740b0ebe780acf94c520fd028b2a6cd',
                'top.jpg':'655c9e92f907096f30bc9dc2508b6ca545249a7a50af9a10beb8872cc27d784d',
                'vanilla-white.png':'e399b578e5a54c84a6bbd56df410b4b699b50049cf14395b1b0a826a990671fe'}
        for file,digest in hashes.items():self.assertEqual(hashlib.sha256((shulker.REFERENCE/file).read_bytes()).hexdigest(),digest)
        atlas,icon=shulker.textures(); s=shulker.SCALE; unit=16*s
        with Image.open(shulker.ENTITY) as im:
            self.assertEqual((im.mode,im.size),('RGBA',(64*s,64*s)))
            self.assertEqual(im.tobytes(),atlas.tobytes())
            self.assertEqual(im.crop((16*s,0,32*s,16*s)).tobytes(),shulker.photo('top',unit).convert('RGBA').tobytes())
            body=shulker.photo('body',unit).convert('RGBA')
            for x in (0,16,32,48):
                self.assertEqual(im.crop((x*s,16*s,(x+16)*s,28*s)).tobytes(),body.crop((0,0,unit,12*s)).tobytes())
                self.assertEqual(im.crop((x*s,44*s,(x+16)*s,52*s)).tobytes(),body.crop((0,8*s,unit,16*s)).tobytes())
            with Image.open(shulker.REFERENCE/'vanilla-white.png') as v:
                v=v.convert('RGBA').resize(im.size,Image.Resampling.NEAREST)
                self.assertEqual(im.crop((0,52*s,64*s,64*s)).tobytes(),v.crop((0,52*s,64*s,64*s)).tobytes())
        with Image.open(shulker.ICON) as im:
            self.assertEqual((im.mode,im.size),('RGB',(256,256)))
            self.assertEqual(im.tobytes(),icon.tobytes())

    def test_anvil_source_wear_and_uv(self):
        hashes={'top.jpg':'ee0ca28f13c300d6fda9256d183d471eb45a44c0111c6530c0f11729cfae03f2',
                'side.jpg':'653daea78432e988a2cec2687e83d626456a9f71098b2b9f2b07b1e7482bc7e1',
                'anvil_top_damaged_0.png':'de8580ab4c9ed4392fafebe83346514da3a8008714becbaca1a901eda026b2e5',
                'anvil_top_damaged_1.png':'4e89d82b5b87f3647a291df36c3ca61a1373f572885493d2d7a75c2b4392e3b9',
                'anvil_top_damaged_2.png':'296a2062c0dbeab9ca6f30a875ae9172d2a5d8efd3e4f864c49f7f6f0e70e274'}
        for file,digest in hashes.items():self.assertEqual(hashlib.sha256((anvil.REFERENCE/file).read_bytes()).hexdigest(),digest)
        with Image.open(anvil.BLOCKS/'anvil_base.png') as im:
            self.assertEqual((im.mode,im.size),('RGB',(256,256)))
            self.assertEqual(im.tobytes(),anvil.base().tobytes())
        variants=set()
        for i in range(3):
            with Image.open(anvil.BLOCKS/f'anvil_top_damaged_{i}.png') as im:
                self.assertEqual((im.mode,im.size),('RGBA',(256,256)))
                self.assertEqual(im.tobytes(),anvil.top(i).tobytes())
                self.assertEqual(im.getchannel('A').getbbox(),(48,0,208,256))
                variants.add(hashlib.sha256(im.tobytes()).digest())
        self.assertEqual(len(variants),3)

    def test_packs_and_scope(self):
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        for n in ('anvil_base','anvil_top_damaged_x','flattened_anvil_base','flattened_anvil_top','chipped_anvil_top','damaged_anvil_top','white_shulker_box','shulker_box_top'):
            self.assertNotIn(n,terrain)  # rely on vanilla indexed and modern entries
        blocks=json.loads((ROOT/'blocks.json').read_text())
        for n in ('anvil','chipped_anvil','damaged_anvil','white_shulker_box'):self.assertNotIn(n,blocks)
        paths=[shulker.ENTITY,shulker.ICON,anvil.BLOCKS/'anvil_base.png']+[anvil.BLOCKS/f'anvil_top_damaged_{i}.png' for i in range(3)]
        aliases={'quartz_block_chiseled_top':'quartz_block_chiseled','quartz_block_lines_top':'quartz_block_top'}
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2, 3, 0]);self.assertEqual(manifest['modules'][0]['version'],[2, 3, 0])
                for p in paths:self.assertEqual(z.read(p.relative_to(ROOT).as_posix()),p.read_bytes())
                self.assertNotIn('textures/entity/shulker/shulker_undyed.png',z.namelist())
                self.assertNotIn('entity/shulker.entity.json',z.namelist())
                for alias,base in aliases.items():
                    prefix='textures/blocks/'
                    self.assertNotIn(prefix+alias+'.png',z.namelist())
                    self.assertEqual(z.read(prefix+base+'.png'),(ROOT/(prefix+alias+'.png')).read_bytes())


if __name__=='__main__':unittest.main()
