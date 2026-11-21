#!/usr/bin/env python3
"""Static neutral grass and water-compat checks; not a Minecraft render test."""
import copy
import json
import unittest
import uuid
import zipfile
from pathlib import Path
from PIL import Image
from prepare_neutral_grass import VANILLA, MAIN, WATER, COMPAT, ARCHIVE, needs_override, neutralize

EXPECTED={'cherry_grove','mesa','mesa_bryce','mesa_plateau_mutated',
          'mesa_plateau_stone','mesa_plateau_stone_mutated','pale_garden',
          'roofed_forest','sulfur_caves'}

class NeutralGrassTests(unittest.TestCase):
    def test_colormaps_and_side_mask(self):
        for name in ('grass','swamp_grass'):
            with Image.open(MAIN/'textures/colormap'/f'{name}.png') as im:
                self.assertEqual((im.mode,im.size),('RGB',(256,256)))
                self.assertEqual(im.getextrema(),((255,255),(255,255),(255,255)))
        atlas=json.loads((MAIN/'textures/terrain_texture.json').read_text())['texture_data']
        side=atlas['grass_side']['textures'][0]
        self.assertEqual(side['overlay_color'],'#75b04a')
        self.assertEqual(len(side['variations']),16)
        for i,variant in enumerate(side['variations']):
            self.assertEqual(variant['path'],f'textures/blocks/grass_side_variant_{i:02}')
        self.assertEqual(len(atlas['grass_top']['textures']),17)
        self.assertFalse((MAIN/'textures/colormap/foliage.png').exists())

    def test_biome_scope_and_water_compatibility(self):
        originals=sorted(VANILLA.glob('*.client_biome.json'))
        self.assertEqual(len(originals),88)
        selected=[p for p in originals if needs_override(json.loads(p.read_text()))]
        self.assertEqual({p.name.removesuffix('.client_biome.json') for p in selected},EXPECTED)
        self.assertEqual({p.name for p in (MAIN/'biomes').glob('*.json')},{p.name for p in selected})
        expected={'manifest.json'}|{'biomes/'+p.name for p in selected}
        with zipfile.ZipFile(ARCHIVE) as compat:
            self.assertIsNone(compat.testzip());self.assertEqual(set(compat.namelist()),expected)
            manifest=json.loads(compat.read('manifest.json'))
            uuid.UUID(manifest['header']['uuid']);uuid.UUID(manifest['modules'][0]['uuid'])
            for src in originals:
                original=json.loads(src.read_text());water=json.loads((WATER/'biomes'/src.name).read_text())
                old_grass=original['minecraft:client_biome']['components'].get('minecraft:grass_appearance',{})
                if src not in selected:
                    # Defaults and swamp map are covered by the two white maps.
                    self.assertFalse(isinstance(old_grass.get('color'),str))
                    self.assertFalse(old_grass.get('grass_is_shaded',False))
                    continue
                expected_main=neutralize(copy.deepcopy(original));expected_water=neutralize(copy.deepcopy(water))
                main=json.loads((MAIN/'biomes'/src.name).read_text())
                overlay=json.loads(compat.read('biomes/'+src.name))
                self.assertEqual(main,expected_main);self.assertEqual(overlay,expected_water)
                self.assertEqual(overlay,json.loads((COMPAT/'biomes'/src.name).read_text()))
                # Water values remain those of the earlier three-photo pack.
                self.assertEqual(overlay['minecraft:client_biome']['components']['minecraft:water_appearance'],
                                 water['minecraft:client_biome']['components']['minecraft:water_appearance'])
                newgrass=main['minecraft:client_biome']['components']['minecraft:grass_appearance']
                self.assertEqual(newgrass['color'],'#FFFFFF')
                self.assertFalse(newgrass.get('grass_is_shaded',False))
        for pack in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/pack
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['header']['version'],[2,6,0])
                self.assertEqual(manifest['modules'][0]['version'],[2,6,0])
                for name in ('grass','swamp_grass'):
                    fn=f'textures/colormap/{name}.png'
                    self.assertEqual(z.read(fn),(MAIN/fn).read_bytes())
                for src in selected:
                    name='biomes/'+src.name
                    self.assertEqual(z.read(name),(MAIN/name).read_bytes())

if __name__=='__main__':unittest.main()
