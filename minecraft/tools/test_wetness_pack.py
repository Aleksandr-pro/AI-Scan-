#!/usr/bin/env python3
"""Structural checks only; no Minecraft rendering or gameplay is tested."""
import io
import json
import unittest
import zipfile
from pathlib import Path
from uuid import UUID
from PIL import Image

ROOT = Path('minecraft')
SOURCE = ROOT / 'rain-wetness'


class WetnessPackTests(unittest.TestCase):
    def test_packs_and_bundle(self):
        paths = [('behavior', ROOT / 'rain-wetness-behavior.mcpack'), ('resources', ROOT / 'rain-wetness-resources.mcpack')]
        archives = {}
        for folder, path in paths:
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                expected = {p.relative_to(SOURCE / folder).as_posix() for p in (SOURCE / folder).rglob('*') if p.is_file()}
                self.assertEqual(set(z.namelist()), expected)
                for name in expected:
                    self.assertEqual(z.read(name), (SOURCE / folder / name).read_bytes())
                archives[folder] = {name: z.read(name) for name in expected}
        bp = json.loads(archives['behavior']['manifest.json'])
        rp = json.loads(archives['resources']['manifest.json'])
        ids = [bp['header']['uuid'], rp['header']['uuid']] + [m['uuid'] for m in bp['modules'] + rp['modules']]
        for identifier in ids:
            UUID(identifier)
        self.assertEqual(len(set(ids)), len(ids))
        self.assertIn({'uuid': rp['header']['uuid'], 'version': rp['header']['version']}, bp['dependencies'])
        self.assertIn({'module_name': '@minecraft/server', 'version': '2.8.0'}, bp['dependencies'])
        self.assertIn('pbr', rp['capabilities'])
        with zipfile.ZipFile(ROOT / 'rain-wetness.mcaddon') as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(set(z.namelist()), {p.name for _, p in paths})
            for _, path in paths:
                self.assertEqual(z.read(path.name), path.read_bytes())
        texture_data = json.loads(archives['resources']['textures/terrain_texture.json'])['texture_data']
        for name in ('rainwet_dirt', 'rainwet_stone', 'rainwet_grass_top', 'rainwet_grass_side'):
            self.assertEqual(texture_data[name]['textures'], 'textures/blocks/' + name)
            path = 'textures/blocks/' + name
            with Image.open(io.BytesIO(archives['resources'][path + '.png'])) as im:
                self.assertEqual(im.size, (256, 256))
                self.assertEqual(im.mode, 'RGB')
            tex = json.loads(archives['resources'][path + '.texture_set.json'])['minecraft:texture_set']
            self.assertEqual(tex['color'], name)
            self.assertEqual(tex['metalness_emissive_roughness_subsurface'], [0, 0, 90, 0])
        for kind in ('dirt', 'grass', 'stone'):
            block = json.loads(archives['behavior'][f'blocks/{kind}.json'])['minecraft:block']
            self.assertEqual(block['description']['identifier'], f'rainwet:{kind}')
            c = block['components']
            self.assertEqual(c['minecraft:movable']['movement_type'], 'immovable')
            self.assertIn(c['minecraft:loot'], archives['behavior'])
            for material in c['minecraft:material_instances'].values():
                self.assertIn(material['texture'], texture_data)
        self.assertEqual(json.loads(archives['behavior']['blocks/grass.json'])['minecraft:block']['components']['minecraft:material_instances']['up']['tint_method'], 'grass')


if __name__ == '__main__':
    unittest.main()
