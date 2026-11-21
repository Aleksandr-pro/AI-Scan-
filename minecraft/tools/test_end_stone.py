#!/usr/bin/env python3
"""Verify estimated maps, optional PBR and classic packs; not a render test."""
import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_end_stone import SOURCE, BLOCKS, SIZE, BOXES, MAPS_ZIP, PBR_PACK, name, colors, maps, png

ROOT = Path('minecraft/realistic-dirt')


class EndStoneTests(unittest.TestCase):
    def test_source_and_tile_variations(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '59fe45b9b9a0c9498fdd53ecd8c96c6be5953a05d5bd2a739a2b9f7c165524e5')
        self.assertEqual(len(BOXES),4)
        colors_ = colors(); arrays = []; hashes = set()
        for i in range(4):
            with Image.open(BLOCKS/(name(i)+'.png')) as im:
                self.assertEqual((im.mode,im.size),('RGB',(SIZE,SIZE)))
                self.assertEqual(im.tobytes(), colors_[i].tobytes())
                arrays.append(np.array(im));hashes.add(hashlib.sha256(im.tobytes()).digest())
        self.assertEqual(len(hashes),4)
        for a in arrays:
            np.testing.assert_array_equal(a[0],a[-1])
            np.testing.assert_array_equal(a[:,0],a[:,-1])
            for sl in (np.s_[:12], np.s_[-12:], np.s_[:,:12],np.s_[:,-12:]):
                np.testing.assert_array_equal(a[sl],arrays[0][sl])

    def test_atlas_and_classic_packages(self):
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        variations=[{'path':'textures/blocks/'+name(i),'weight':1} for i in range(4)]
        self.assertEqual(terrain['end_stone']['textures']['variations'],variations)
        self.assertNotIn('endframe_bottom', terrain)
        self.assertNotIn('end_stone',json.loads((ROOT/'blocks.json').read_text()))
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip()); manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2, 3, 0])
                self.assertEqual(manifest['modules'][0]['version'],[2, 3, 0])
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json')),json.loads((ROOT/'textures/terrain_texture.json').read_text()))
                for i in range(4):
                    p='textures/blocks/'+name(i)+'.png';self.assertEqual(z.read(p),(ROOT/p).read_bytes())
                    self.assertNotIn('textures/blocks/'+name(i)+'.texture_set.json',z.namelist())
                self.assertIn('textures/blocks/end_bricks.png',z.namelist())

    def test_estimated_maps_and_optional_pbr_contract(self):
        with zipfile.ZipFile(MAPS_ZIP) as z, zipfile.ZipFile(PBR_PACK) as p:
            self.assertIsNone(z.testzip());self.assertIsNone(p.testzip())
            manifest=json.loads(p.read('manifest.json'))
            self.assertIn('pbr',manifest['capabilities'])
            self.assertEqual(manifest['header']['min_engine_version'],[1,21,120])
            atlas=json.loads(p.read('textures/terrain_texture.json'))
            self.assertEqual(atlas['texture_data']['end_stone']['textures']['variations'],[
                {'path':'textures/blocks/'+name(i),'weight':1} for i in range(4)])
            for i,image in enumerate(colors()):
                generated=maps(image); n=name(i); root='textures/blocks/'
                for layer,im in generated.items():
                    content=z.read(f'variant_{i}/{layer}.png')
                    self.assertEqual(content,png(im))
                    decoded=Image.open(io.BytesIO(content));self.assertEqual(decoded.size,(SIZE,SIZE))
                    self.assertEqual(decoded.mode,'L' if layer in ('height','roughness','ao') else 'RGB')
                mer=np.asarray(generated['mer'])
                self.assertFalse(mer[:,:,0].any());self.assertFalse(mer[:,:,1].any())
                np.testing.assert_array_equal(mer[:,:,2],np.asarray(generated['roughness']))
                descriptor=json.loads(p.read(root+n+'.texture_set.json'))['minecraft:texture_set']
                self.assertEqual(descriptor,{'color':n,'normal':n+'_normal','metalness_emissive_roughness':n+'_mer'})
                for layer,suffix in (('albedo',''),('normal','_normal'),('mer','_mer')):
                    self.assertEqual(p.read(root+n+suffix+'.png'),png(generated[layer]))


if __name__ == '__main__':
    unittest.main()
