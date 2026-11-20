#!/usr/bin/env python3
"""Validate the supplied sand, shared face mapping, and removal of old assets."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from prepare_cobblestone import prepare
from prepare_sand import SOURCE

ROOT = Path('minecraft/realistic-dirt')
BLOCKS = ROOT / 'textures/blocks'
OLD_HASHES = {
    '5317e0000b93c046dd48aa29f58c645062dd9fef2572fa4fb59a13dacf69e0d8',
    'ed47bfa4f5b493a41b481147d658bf49e8a3d758f939f0acfdee904f9cac6be2',
    '50241fc2bf99dc3c3708877b66fcb12014706f86dec9ff06876dd42a8b5993a5',
    '51cdb4ac3c0e516cd9ee8cb8a57310bf0c0d15cb197120f52d6a7b1db172370a',
    'c5de2db2bc6a6e027ab12797ad14587b0ed1d98eac4b60caca7e00818b81eb1a',
    '1b2706431487badb11f9c8415ade79bdee5eb4d10a1989748c08ab9f6fb2650c',
    'f7aeaee2fb8714118036ff28da8a6ef299addf87ec6f550a3e5f51e9661ae604',
    '7fa61a67502a5ba4d5c5947f42541f85dd756cd2461a9a0defed842f71429e0b',
}


def mean_diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


class SandTests(unittest.TestCase):
    def test_image_and_seams(self):
        with Image.open(BLOCKS / 'sand.png') as tile:
            self.assertEqual((tile.mode, tile.size), ('RGB', (512, 512)))
            self.assertEqual(tile.tobytes(), prepare(SOURCE).tobytes())
            for edge1, edge2, adjacent1, adjacent2 in (
                ((0, 0, 1, 512), (511, 0, 512, 512), (0, 0, 511, 512), (1, 0, 512, 512)),
                ((0, 0, 512, 1), (0, 511, 512, 512), (0, 0, 512, 511), (0, 1, 512, 512)),
            ):
                self.assertLess(mean_diff(tile.crop(edge1), tile.crop(edge2)),
                                1.3 * mean_diff(tile.crop(adjacent1), tile.crop(adjacent2)))

    def test_mapping_and_archive_contents(self):
        blocks = json.loads((ROOT / 'blocks.json').read_text(encoding='utf-8'))
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        self.assertEqual(blocks['sand']['textures'], dict.fromkeys(('up', 'down', 'side'), 'flattened_sand'))
        self.assertEqual(terrain['flattened_sand']['textures'], 'textures/blocks/sand')
        self.assertNotIn('realistic_sand_top', terrain)
        self.assertNotIn('red_sand', blocks)
        self.assertNotIn('red_sand', terrain)
        self.assertFalse(list(BLOCKS.glob('realistic_sand_top*.png')))
        self.assertFalse(list(BLOCKS.glob('sand_variant_*.png')))
        for path in ROOT.rglob('*'):
            if path.is_file():
                self.assertNotIn(hashlib.sha256(path.read_bytes()).hexdigest(), OLD_HASHES, str(path))
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read('textures/blocks/sand.png'), (BLOCKS / 'sand.png').read_bytes())
                self.assertEqual(json.loads(archive.read('blocks.json'))['sand']['textures'], blocks['sand']['textures'])
                self.assertEqual(json.loads(archive.read('textures/terrain_texture.json'))['texture_data']['flattened_sand'], terrain['flattened_sand'])
                for entry in archive.infolist():
                    self.assertNotIn(hashlib.sha256(archive.read(entry)).hexdigest(), OLD_HASHES, entry.filename)
                    self.assertFalse(entry.filename.startswith('textures/blocks/realistic_sand_top'))
                    self.assertFalse(entry.filename.startswith('textures/blocks/sand_variant_'))


if __name__ == '__main__':
    unittest.main()
