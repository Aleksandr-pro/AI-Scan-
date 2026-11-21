#!/usr/bin/env python3
"""Static preparation, face mapping, and distributable checks (not in-game)."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_crafting_table import REFERENCE, BLOCKS, FACES, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class CraftingTableTests(unittest.TestCase):
    def test_source_images_and_preparation(self):
        hashes = {
            'north': 'ceddf2f2e51d719d88fca5ab3380d002b32b93d0df01097166b71172c4c7a90e',
            'east': 'f0ef2761e9757d4884f76569c52bae7c7de08d1f0c67f8efcf3058b9f7a914cc',
            'south': '36fdd68c6d5320bb9953232c1b056c916e07034025e4e00a252cf62a58897dd1',
            'west': 'd6c8f1f0228c91dad081ae02842827054b10cdad94441f45b9ab2b54760f107a',
            'top': 'fc874aec359f11eb9973a64faf81c96983cd0e4ff178635cc4d8460867d84d54',
        }
        prepared = []
        for face in FACES:
            self.assertEqual(hashlib.sha256((REFERENCE / f'{face}.jpg').read_bytes()).hexdigest(), hashes[face])
            with Image.open(BLOCKS / f'photo_crafting_table_{face}.png') as image:
                self.assertEqual((image.mode, image.size), ('RGB', (SIZE, SIZE)))
                self.assertEqual(image.tobytes(), prepare(face).tobytes())
                prepared.append(image.tobytes())
        self.assertEqual(len(set(hashlib.sha256(b).digest() for b in prepared)), 5)

    def test_mapping_and_archives(self):
        blocks = json.loads((ROOT / 'blocks.json').read_text())
        table = blocks['crafting_table']
        self.assertEqual(table['sound'], 'wood')
        self.assertEqual(table['textures']['down'], 'crafting_table_bottom')
        for direction in ('north', 'east', 'south', 'west'):
            self.assertEqual(table['textures'][direction], 'photo_crafting_table_' + direction)
        self.assertEqual(table['textures']['up'], 'photo_crafting_table_top')
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        for face in FACES:
            key = 'photo_crafting_table_' + face
            self.assertEqual(terrain[key]['textures'], 'textures/blocks/' + key)
        # The vanilla bottom entry falls back to Bedrock's oak plank texture.
        self.assertNotIn('crafting_table_bottom', terrain)
        for name in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / name) as pack:
                self.assertIsNone(pack.testzip())
                self.assertEqual(json.loads(pack.read('manifest.json'))['header']['version'], [1, 91, 0])
                for path in ['blocks.json', 'textures/terrain_texture.json'] + [
                    f'textures/blocks/photo_crafting_table_{face}.png' for face in FACES
                ]:
                    self.assertEqual(pack.read(path), (ROOT / path).read_bytes())
                for name in ('crafting_table_top', 'crafting_table_side', 'crafting_table_front'):
                    self.assertNotIn(f'textures/blocks/{name}.png', pack.namelist())


if __name__ == '__main__':
    unittest.main()
