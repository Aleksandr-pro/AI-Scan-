#!/usr/bin/env python3
"""Check fern assets and custom add-on structure, not Minecraft rendering."""
import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path
from uuid import UUID
from PIL import Image
from prepare_fern import SOURCE, OUTPUT, SIZE, prepare
from build_fern_fan import (
    RP, BP, TARGET, RHEADER, RMODULE, BHEADER, BMODULE,
    IDENTIFIER, GEOMETRY, TEXTURE, make_atlas, geometry,
)

ROOT = Path('minecraft/realistic-dirt')


class FernTests(unittest.TestCase):
    def test_source_and_texture(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'dd2f12bef9687514cb7dd4cacf34cb08e326d5014ff6dbc9f84f2542369027e6')
        with Image.open(OUTPUT) as image:
            self.assertEqual((image.mode, image.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(image.tobytes(), prepare().tobytes())
            a = image.getchannel('A')
            self.assertEqual(a.getpixel((0, 0)), 0)
            self.assertGreater(sum(a.histogram()[128:]), 20000)
            self.assertGreater(a.histogram()[0], SIZE*SIZE*.5)

    def test_base_packs(self):
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        self.assertEqual(terrain['fern']['textures'], 'textures/blocks/fern')
        self.assertNotIn('large_fern_top', terrain)
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        self.assertNotIn('fern', blocks)
        self.assertFalse((ROOT / 'textures/blocks/double_plant_fern_top.png').exists())
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as z:
                self.assertIsNone(z.testzip())
                manifest = json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'], [1, 82, 0])
                self.assertEqual(manifest['header']['version'], manifest['modules'][0]['version'])
                self.assertEqual(z.read('textures/blocks/fern.png'), OUTPUT.read_bytes())
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json'))['texture_data']['fern'], terrain['fern'])
                self.assertNotIn('textures/blocks/double_plant_fern_top.png', z.namelist())
                self.assertNotIn('textures/blocks/fern_carried.png', z.namelist())

    def test_addon_files_geometry_and_references(self):
        ids = (RHEADER, RMODULE, BHEADER, BMODULE)
        self.assertEqual(len(set(ids)), len(ids))
        for identifier in ids:
            UUID(identifier)
        with zipfile.ZipFile(TARGET) as addon:
            self.assertIsNone(addon.testzip())
            self.assertEqual(set(addon.namelist()), {'fern-fan-resources.mcpack', 'fern-fan-behavior.mcpack'})
            for name, folder in (('fern-fan-resources.mcpack', RP), ('fern-fan-behavior.mcpack', BP)):
                with zipfile.ZipFile(io.BytesIO(addon.read(name))) as pack:
                    self.assertIsNone(pack.testzip())
                    files = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
                    self.assertEqual(set(pack.namelist()), files)
                    for file in files:
                        self.assertEqual(pack.read(file), (folder / file).read_bytes())
            with zipfile.ZipFile(io.BytesIO(addon.read('fern-fan-resources.mcpack'))) as rp, \
                 zipfile.ZipFile(io.BytesIO(addon.read('fern-fan-behavior.mcpack'))) as bp:
                resource = json.loads(rp.read('manifest.json'))
                behavior = json.loads(bp.read('manifest.json'))
                self.assertEqual(resource['header']['uuid'], RHEADER)
                self.assertEqual(resource['modules'][0]['uuid'], RMODULE)
                self.assertEqual(behavior['header']['uuid'], BHEADER)
                self.assertEqual(behavior['modules'][0]['uuid'], BMODULE)
                self.assertEqual(behavior['dependencies'], [{'uuid': RHEADER, 'version': [1, 0, 0]}])
                self.assertEqual(behavior['header']['min_engine_version'], [1, 26, 30])
                block = json.loads(bp.read('blocks/fan_fern.json'))['minecraft:block']
                self.assertEqual(block['description']['identifier'], IDENTIFIER)
                c = block['components']
                self.assertEqual(c['minecraft:geometry'], GEOMETRY)
                self.assertFalse(c['minecraft:collision_box'])
                self.assertEqual(c['minecraft:material_instances']['*']['render_method'], 'alpha_test')
                self.assertEqual(c['minecraft:material_instances']['*']['texture'], TEXTURE)
                self.assertTrue(all(not name.endswith('.js') for name in bp.namelist()))
                geom = json.loads(rp.read('models/blocks/fern.geo.json'))
                self.assertEqual(geom, geometry())
                shape = geom['minecraft:geometry'][0]
                self.assertEqual(shape['description']['identifier'], GEOMETRY)
                self.assertEqual([bone['rotation'][1] for bone in shape['bones']], [0, 45, 90, 135])
                self.assertEqual(len(shape['bones']), 4)
                for bone in shape['bones']:
                    self.assertEqual(bone['cubes'][0]['size'], [16, 16, 0])
                atlas = json.loads(rp.read('textures/terrain_texture.json'))['texture_data']
                self.assertEqual(atlas[TEXTURE]['textures'], f'textures/blocks/{TEXTURE}')
                with Image.open(io.BytesIO(rp.read(f'textures/blocks/{TEXTURE}.png'))) as texture:
                    self.assertEqual((texture.mode, texture.size), ('RGBA', (1024, 1024)))
                    self.assertEqual(texture.tobytes(), make_atlas().tobytes())
                    self.assertEqual(len({hashlib.sha256(texture.crop((x*SIZE, y*SIZE, (x+1)*SIZE, (y+1)*SIZE)).tobytes()).hexdigest() for y in range(2) for x in range(2)}), 4)


if __name__ == '__main__':
    unittest.main()
