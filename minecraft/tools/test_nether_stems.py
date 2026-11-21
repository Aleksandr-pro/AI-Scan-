#!/usr/bin/env python3
"""Static checks for Nether stems; actual game rendering is not tested."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_nether_stems import SOURCE, BLOCKS, SIZE, BOXES, prepare

ROOT=Path('minecraft/realistic-dirt')
HASHES={'warped':'81e651837a55356ff477a1d0e91c37e6e75dc8dcd076e78a5fecf460bd74be63',
        'crimson':'55ba541071fa5b048056397a18e76fbccd929a225f5a1e134ff8825f639e3395'}
KEYS={'crimson':{'top':'crimson_log_top','side':'crimson_log_side'},
      'warped':{'top':'warped_stem_top','side':'warped_stem_side'}}

class NetherStemTests(unittest.TestCase):
    def test_photos_split_and_processed(self):
        self.assertEqual(BOXES,{'top':(3,0,723,720),'side':(733,0,1453,720)})
        for kind in ('crimson','warped'):
            self.assertEqual(hashlib.sha256((SOURCE/(kind+'.jpg')).read_bytes()).hexdigest(),HASHES[kind])
            for face in ('top','side'):
                path=BLOCKS/f'photo_{kind}_stem_{face}.png'
                with Image.open(path) as im:
                    self.assertEqual((im.mode,im.size),('RGB',(SIZE,SIZE)))
                    self.assertEqual(im.tobytes(),prepare(kind,face).tobytes())
                    a=np.asarray(im);mean=a.mean((0,1))
                    if kind=='warped':self.assertGreater(mean[1],2*mean[0])
                    else:self.assertGreater(mean[0],2*mean[1])
                    if face=='side':
                        np.testing.assert_array_equal(a[0],a[-1])
                        np.testing.assert_array_equal(a[:,0],a[:,-1])
                        # Interior keeps the supplied bark, without blending.
                        with Image.open(SOURCE/(kind+'.jpg')) as src:
                            raw=src.convert('RGB').crop(BOXES['side']).resize((SIZE,SIZE),Image.Resampling.LANCZOS)
                        np.testing.assert_array_equal(a[14:-14,20:-20],np.asarray(raw)[14:-14,20:-20])

    def test_mapping_and_archives(self):
        sample=json.loads((SOURCE/'vanilla-sample.json').read_text())
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())
        data=terrain['texture_data'];blocks=json.loads((ROOT/'blocks.json').read_text())
        for kind in ('crimson','warped'):
            top=KEYS[kind]['top']; side=KEYS[kind]['side']
            stem=sample['blocks'][kind+'_stem']['textures']
            hyphae=sample['blocks'][kind+'_hyphae']['textures']
            self.assertEqual(stem['up'],top);self.assertEqual(stem['down'],top)
            for face in ('east','north','south','west'):
                self.assertEqual(stem[face],side)
            self.assertEqual(set(hyphae.values()),{side})
            for face,key in KEYS[kind].items():
                self.assertIn(key,sample['terrain'])
                self.assertEqual(data[key],{'textures':f'textures/blocks/photo_{kind}_stem_{face}'})
                self.assertNotIn(f'stripped_{kind}_stem_{face}',data)
            for block in (kind+'_stem',kind+'_hyphae'):
                self.assertNotIn(block,blocks)
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip());manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2,5,0])
                self.assertEqual(manifest['modules'][0]['version'],[2,5,0])
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json')),terrain)
                for kind in ('crimson','warped'):
                    for face in ('top','side'):
                        name=f'textures/blocks/photo_{kind}_stem_{face}.png'
                        self.assertEqual(z.read(name),(ROOT/name).read_bytes())
                        self.assertNotIn(f'textures/blocks/huge_fungus/stripped_{kind}_stem_{face}.png',z.namelist())

if __name__=='__main__':unittest.main()
