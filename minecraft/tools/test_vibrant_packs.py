#!/usr/bin/env python3
"""Check both VV archives, references, compatibility copy and safe settings.

This does not render Minecraft or certify GPU support.
"""
import json
import unittest
import zipfile
from pathlib import Path
from uuid import UUID

from PIL import Image

ROOT = Path('minecraft')


class VibrantPackTests(unittest.TestCase):
    def test_archives_and_compatibility_copy(self):
        with zipfile.ZipFile(ROOT / 'realistic-atmosphere.mcpack') as fx, \
             zipfile.ZipFile(ROOT / 'realistic-dirt.mcpack') as old, \
             zipfile.ZipFile(ROOT / 'realistic-dirt-vibrant.mcpack') as compat:
            self.assertIsNone(fx.testzip())
            self.assertIsNone(compat.testzip())
            self.assertEqual(set(old.namelist()), set(compat.namelist()))
            old_manifest = json.loads(old.read('manifest.json'))
            new_manifest = json.loads(compat.read('manifest.json'))
            fx_manifest = json.loads(fx.read('manifest.json'))
            self.assertIn('pbr', new_manifest['capabilities'])
            self.assertIn('pbr', fx_manifest['capabilities'])
            self.assertEqual(new_manifest['header']['min_engine_version'], [1, 21, 120])
            ids = [old_manifest['header']['uuid'], new_manifest['header']['uuid'], fx_manifest['header']['uuid'],
                   old_manifest['modules'][0]['uuid'], new_manifest['modules'][0]['uuid'], fx_manifest['modules'][0]['uuid']]
            self.assertEqual(len(set(ids)), len(ids))
            for item in ids:
                UUID(item)
            for name in old.namelist():
                if name != 'manifest.json':
                    self.assertEqual(old.read(name), compat.read(name), name)
            for name in fx.namelist():
                if not name.endswith('.texture_set.json'):
                    continue
                descriptor = json.loads(fx.read(name))['minecraft:texture_set']
                base = Path(name).parent / (descriptor['color'] + '.png')
                self.assertIn(base.as_posix(), compat.namelist(), name)
                self.assertEqual(len(descriptor['metalness_emissive_roughness_subsurface']), 4)

    def test_water_and_weather(self):
        pack = ROOT / 'realistic-atmosphere'
        water = json.loads((pack / 'water/water.json').read_text())['minecraft:water_settings']
        self.assertEqual(water['description']['identifier'], 'minecraft:default_water')
        self.assertTrue(water['waves']['enabled'])
        self.assertTrue(1 <= water['waves']['octaves'] <= 6)
        self.assertTrue(0 <= water['waves']['depth'] <= 3)
        rain = json.loads((pack / 'particles/rain_splash.json').read_text())['particle_effect']
        self.assertEqual(rain['description']['identifier'], 'minecraft:rain_splash_particle')
        self.assertEqual(rain['description']['basic_render_parameters']['texture'], 'textures/particle/realistic_rain_drop')
        self.assertIn('minecraft:particle_motion_collision', rain['components'])
        with Image.open(pack / 'textures/particle/realistic_rain_drop.png') as sprite:
            self.assertEqual((sprite.mode, sprite.size), ('RGBA', (64, 64)))
            alpha = sprite.getchannel('A')
            self.assertEqual(alpha.getpixel((0, 0)), 0)
            self.assertGreater(alpha.getextrema()[1], 100)
        fog = json.loads((pack / 'fogs/rain_haze.json').read_text())['minecraft:fog_settings']
        self.assertEqual(fog['description']['identifier'], 'minecraft:fog_default')
        self.assertEqual(set(fog['distance']), {'weather'})


if __name__ == '__main__':
    unittest.main()
