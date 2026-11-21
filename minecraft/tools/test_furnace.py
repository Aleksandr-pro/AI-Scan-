#!/usr/bin/env python3
"""Static furnace source, state mapping and archive checks (not in-game)."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_furnace import REFERENCE, BLOCKS, FACES, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class FurnaceTests(unittest.TestCase):
    def test_sources_and_preparation(self):
        hashes={'body':'ca4bb0fb7e12f1ddff58547682d4362ea7b1c9046a73a2d8ddd1759d8033f120',
                'front_on':'df1325261cf30e9dbb8d61e3166c5337a96009cd1c745f49462960e8bbed79ff',
                'front_off':'40aa4c51872d606d95e7bea6035352d679ce90d201fdc2129804b84099a8a780'}
        prepared=set()
        for face in FACES:
            self.assertEqual(hashlib.sha256((REFERENCE/(face+'.jpg')).read_bytes()).hexdigest(),hashes[face])
            with Image.open(BLOCKS/f'photo_furnace_{face}.png') as image:
                self.assertEqual((image.mode,image.size),('RGB',(SIZE,SIZE)))
                self.assertEqual(image.tobytes(),prepare(face).tobytes())
                prepared.add(hashlib.sha256(image.tobytes()).digest())
        self.assertEqual(len(prepared),3)

    def test_furnace_states_and_packs(self):
        blocks=json.loads((ROOT/'blocks.json').read_text())
        expected={'furnace':{'down':'photo_furnace_body','east':'photo_furnace_body',
                 'north':'photo_furnace_body','south':'photo_furnace_front_off',
                 'up':'photo_furnace_body','west':'photo_furnace_body'},
                 'lit_furnace':{'down':'photo_furnace_body','east':'photo_furnace_front_on',
                 'north':'photo_furnace_body','south':'photo_furnace_body',
                 'up':'photo_furnace_body','west':'photo_furnace_body'}}
        for key,value in expected.items():
            self.assertEqual(blocks[key],{'sound':'stone','textures':value})
        for key in ('dispenser','dropper','blast_furnace','lit_blast_furnace','smoker','lit_smoker'):
            self.assertNotIn(key,blocks)
        terrain=json.loads((ROOT/'textures/terrain_texture.json').read_text())['texture_data']
        for part in FACES:
            key='photo_furnace_'+part
            self.assertEqual(terrain[key],{'textures':'textures/blocks/'+key})
        for key in ('furnace','furnace_front','furnace_front_off','furnace_front_on','furnace_side','furnace_top','dispenser_top','dropper_top'):
            self.assertNotIn(key,terrain)  # shared vanilla resources remain intact
        files=['blocks.json','textures/terrain_texture.json']+[f'textures/blocks/photo_furnace_{part}.png' for part in FACES]
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                manifest=json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[1,94,0])
                self.assertEqual(manifest['modules'][0]['version'],[1,94,0])
                for item in files:
                    self.assertEqual(archive.read(item),(ROOT/item).read_bytes())
                for item in ('furnace_top','furnace_side','furnace_front_off','furnace_front_on'):
                    self.assertNotIn(f'textures/blocks/{item}.png',archive.namelist())


if __name__=='__main__':
    unittest.main()
