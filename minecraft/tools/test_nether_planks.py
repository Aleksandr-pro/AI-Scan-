#!/usr/bin/env python3
"""Static source, tiling and package tests; not an in-game render test."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_nether_planks import SOURCE, BLOCKS, SIZE, CROPS, prepare

ROOT=Path('minecraft/realistic-dirt')
REFERENCE=SOURCE/'vanilla-sample.json'
HASHES={'warped':'6fb36a32d0ed0e5bdc8d6e08c2b3f33ea66f1ee1b2e850feff5db7f27961e0bd',
        'crimson':'e2f7ad1ba4c66eb736d35976a3501a45015c754b953ef54dd500bbaacd2637d2'}

class NetherPlankTests(unittest.TestCase):
    def test_source_colors_and_tile_seams(self):
        self.assertEqual(CROPS,{'warped':(0,93,1024,854),'crimson':(0,95,1024,844)})
        for kind in ('warped','crimson'):
            self.assertEqual(hashlib.sha256((SOURCE/(kind+'.jpg')).read_bytes()).hexdigest(),HASHES[kind])
            with Image.open(BLOCKS/f'photo_{kind}_planks.png') as image:
                self.assertEqual((image.mode,image.size),('RGB',(SIZE,SIZE)))
                self.assertEqual(image.tobytes(),prepare(kind).tobytes())
                a=np.asarray(image)
                np.testing.assert_array_equal(a[0],a[-1])
                np.testing.assert_array_equal(a[:,0],a[:,-1])
                mean=a.mean(axis=(0,1))
                if kind=='warped':
                    self.assertGreater(mean[1],mean[0]*1.5);self.assertGreater(mean[2],mean[0]*1.5)
                else:
                    self.assertGreater(mean[0],mean[1]*2);self.assertGreater(mean[0],mean[2]*2)
                # Horizontal joints remain substantially darker than the wood.
                rows=a.mean(axis=(1,2))
                self.assertGreater(float(rows.max()-rows.min()),15)

    def test_atlas_bindings_and_archives(self):
        sample=json.loads(REFERENCE.read_text()); terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())
        atlas=terrain['texture_data']; blocks=json.loads((ROOT/'blocks.json').read_text())
        for kind in ('warped','crimson'):
            key=kind+'_planks'; sign=kind+'_sign'
            vanilla='textures/blocks/huge_fungus/'+key
            self.assertEqual(sample['terrain'][key]['textures'],vanilla)
            self.assertEqual(sample['terrain'][sign]['textures'],vanilla)
            for suffix in ('planks','slab','double_slab','stairs','fence','fence_gate','button','pressure_plate'):
                name=kind+'_'+suffix
                self.assertEqual(sample['blocks'][name]['textures'],key)
                self.assertNotIn(name,blocks)
            self.assertEqual(atlas[key],{'textures':'textures/blocks/photo_'+key})
            self.assertNotIn(sign,atlas)
            self.assertNotIn(kind+'_door',blocks)
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json')),terrain)
                manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2, 5, 0])
                self.assertEqual(manifest['modules'][0]['version'],[2, 5, 0])
                for kind in ('warped','crimson'):
                    name=f'textures/blocks/photo_{kind}_planks.png'
                    self.assertEqual(z.read(name),(ROOT/name).read_bytes())
                    self.assertNotIn(f'textures/blocks/huge_fungus/{kind}_planks.png',z.namelist())

if __name__=='__main__':unittest.main()
