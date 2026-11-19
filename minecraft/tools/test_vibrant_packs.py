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

    def test_puddles_shadows_and_biome_bindings(self):
        pack = ROOT / 'realistic-atmosphere'
        read = lambda path: json.loads((pack / path).read_text())
        rain = read('particles/rain_splash.json')['particle_effect']
        self.assertEqual(rain['components']['minecraft:particle_lifetime_events']['creation_event'], 'realistic_atmosphere:rain_surface')
        choices = rain['events']['realistic_atmosphere:rain_surface']['randomize']
        self.assertEqual(sum(choice['weight'] for choice in choices), 10)
        self.assertTrue(any('particle_effect' not in choice for choice in choices))
        for name in ('puddle', 'ripple'):
            effect = read(f'particles/rain_{name}.json')['particle_effect']
            self.assertTrue(any(c.get('particle_effect') == {'effect': effect['description']['identifier'], 'type': 'particle'} for c in choices))
            components = effect['components']
            self.assertLessEqual(components['minecraft:emitter_rate_manual']['max_particles'], 72)
            self.assertEqual(components['minecraft:particle_appearance_billboard']['facing_camera_mode'], 'emitter_transform_xz')
            self.assertEqual(effect['description']['basic_render_parameters']['texture'], f'textures/particle/rain_{name}')
            with Image.open(pack / f'textures/particle/rain_{name}.png') as sprite:
                self.assertEqual((sprite.mode, sprite.size), ('RGBA', (128, 128)))
                self.assertEqual(sprite.getpixel((0, 0))[3], 0)
                self.assertGreater(sprite.getchannel('A').getextrema()[1], 50)
        self.assertEqual(read('shadows/global.json')['minecraft:shadow_settings']['shadow_style'], 'soft_shadows')
        lighting = read('lighting/mobile_lighting.json')['minecraft:lighting_settings']
        water = read('water/mobile_water.json')['minecraft:water_settings']
        self.assertEqual(lighting['sky']['intensity'], 0.65)
        for biome in ('plains', 'forest', 'birch_forest', 'meadow'):
            client = read(f'biomes/{biome}.client_biome.json')['minecraft:client_biome']
            self.assertEqual(client['description']['identifier'], f'minecraft:{biome}')
            components = client['components']
            self.assertEqual(components['minecraft:lighting_identifier']['lighting_identifier'], lighting['description']['identifier'])
            self.assertEqual(components['minecraft:water_identifier']['water_identifier'], water['description']['identifier'])
            self.assertIn('minecraft:fog_appearance', components)
            self.assertIn('minecraft:ambient_sounds', components)
        with zipfile.ZipFile(ROOT / 'realistic-atmosphere.mcpack') as archive:
            for path in pack.rglob('*'):
                if path.is_file():
                    self.assertEqual(archive.read(path.relative_to(pack).as_posix()), path.read_bytes())

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
