#!/usr/bin/env python3
"""Static checks for the pale oak tile and distributable packs, not game tests."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from prepare_pale_oak import SOURCE,OUTPUT,SIZE,CROP,prepare

ROOT=Path('minecraft/realistic-dirt')


class PaleOakTests(unittest.TestCase):
    def test_source_and_tile(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         '794087a05c2403f68d724ded55ed871a2dca12f5391c3a1c26aeabea5a881c02')
        self.assertEqual(CROP,(0,157,1024,958))
        with Image.open(OUTPUT) as im:
            self.assertEqual((im.mode,im.size),('RGB',(SIZE,SIZE)))
            self.assertEqual(im.tobytes(),prepare().tobytes())
            a=np.asarray(im)
            np.testing.assert_array_equal(a[0,:,:],a[-1,:,:])
            np.testing.assert_array_equal(a[:,0,:],a[:,-1,:])
            # Five horizontal courses and strong seams must remain visible.
            mean=a.mean(axis=(1,2)); self.assertGreater(float(mean.max()-mean.min()),40)

    def test_vanilla_mapping_and_packs(self):
        atlas=json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        self.assertNotIn('pale_oak_planks',atlas)  # vanilla entry points to this filename
        blocks=json.loads((ROOT/'blocks.json').read_text())
        for n in ('pale_oak_planks','pale_oak_slab','pale_oak_stairs','pale_oak_fence','pale_oak_button'):
            self.assertNotIn(n,blocks)
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip());m=json.loads(z.read('manifest.json'))
                self.assertEqual(m['header']['version'],[2, 2, 0]);self.assertEqual(m['modules'][0]['version'],[2, 2, 0])
                self.assertEqual(z.read(OUTPUT.relative_to(ROOT).as_posix()),OUTPUT.read_bytes())
                self.assertNotIn('textures/blocks/pale_oak_log_side.png',z.namelist())
                self.assertNotIn('textures/blocks/pale_oak_door_top.png',z.namelist())
                self.assertNotIn('textures/entity/boat/pale_oak_boat.png',z.namelist())


if __name__=='__main__':unittest.main()
