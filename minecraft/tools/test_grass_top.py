#!/usr/bin/env python3
"""Check the four supplied, edge-matched grass-block tops and atlas."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from prepare_cobblestone import prepare
from prepare_grass_top import FILES, SIZE, SOURCES

ROOT = Path('minecraft/realistic-dirt')
BLOCKS = ROOT / 'textures/blocks'
# Prior grass-top and four rotated assets, from the previous released version.
OLD_HASHES = {
    '6e52ffdbcf43c4fed1a2a0cb3ac7c0ae9af82c832b59a7d0152d2ac356169469',
    '2d2a6bd9ba9163f22e8624b14c974b7263a60509c447df5c8b7e2668c45f7282',
    '1635677d566dbac31d6ff7389bcf4f33b488c7d9e51dc548102a03786fe2c0da',
    'e38e3ff1bcd139363b400551afe1c275a3452ae36f9ba1aebec98a317e27b415',
    'f4226c0f9b0796df791638e9c2a1186e11544e251e77e68cd54872d524202b8e',
}
OLD_SIZES = {486012, 117818, 117660, 117869, 117874}


def mean_diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


class GrassTopTests(unittest.TestCase):
    def test_images_preserve_distinct_sources_and_common_edges(self):
        images = []
        for i, source in enumerate(FILES):
            name = 'grass_top.png' if i == 0 else f'grass_top_variant_{i}.png'
            with Image.open(BLOCKS / name) as image:
                self.assertEqual((image.mode, image.size), ('RGB', (512, 512)))
                images.append(image.copy())
            # Entire interior outside the taper must match that source, not a
            # rotation, a greyscale conversion, or a different reference.
            prepared = prepare(SOURCES / source)
            self.assertEqual(images[-1].crop((48, 48, 464, 464)).tobytes(),
                             prepared.crop((48, 48, 464, 464)).tobytes())
        self.assertEqual(len({hashlib.sha256(im.tobytes()).hexdigest() for im in images}), 4)
        green_excess = []
        for image in images:
            r, g, _ = ImageStat.Stat(image.crop((48, 48, 464, 464))).mean
            green_excess.append(g - r)
        self.assertEqual(green_excess, sorted(green_excess), 'Variants should retain the supplied sparse-to-dense progression')
        self.assertFalse((BLOCKS / 'grass_top_variant_0.png').exists(), 'First variant must not be duplicated')
        self.assertFalse((BLOCKS / 'grass_carried.png').exists(), 'The old held-top image must not remain')
        for image in images:
            # Each corresponding edge is identical across all variants.
            for rect in ((0, 0, 1, SIZE), (SIZE - 1, 0, SIZE, SIZE),
                         (0, 0, SIZE, 1), (0, SIZE - 1, SIZE, SIZE)):
                self.assertEqual(image.crop(rect).tobytes(), images[0].crop(rect).tobytes())
            x_seam = mean_diff(image.crop((0, 0, 1, SIZE)), image.crop((SIZE-1, 0, SIZE, SIZE)))
            y_seam = mean_diff(image.crop((0, 0, SIZE, 1)), image.crop((0, SIZE-1, SIZE, SIZE)))
            x_detail = mean_diff(image.crop((0, 0, SIZE-1, SIZE)), image.crop((1, 0, SIZE, SIZE)))
            y_detail = mean_diff(image.crop((0, 0, SIZE, SIZE-1)), image.crop((0, 1, SIZE, SIZE)))
            self.assertLess(x_seam, x_detail * 1.3)
            self.assertLess(y_seam, y_detail * 1.3)

    def test_old_assets_not_in_source_or_archives(self):
        for path in ROOT.rglob('*'):
            if path.is_file() and path.stat().st_size in OLD_SIZES:
                self.assertNotIn(hashlib.sha256(path.read_bytes()).hexdigest(), OLD_HASHES, str(path))
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as archive:
                for entry in archive.infolist():
                    if entry.file_size in OLD_SIZES:
                        self.assertNotIn(hashlib.sha256(archive.read(entry)).hexdigest(), OLD_HASHES, entry.filename)

    def test_atlas_and_both_packs(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        tops = atlas['grass_top']['textures']
        self.assertEqual(len(tops), 17)
        expected = ['textures/blocks/grass_top'] + [f'textures/blocks/grass_top_variant_{i}' for i in range(1, 4)]
        self.assertEqual(atlas['grass_carried_top']['textures'], 'textures/blocks/grass_top')
        for slot in tops:
            self.assertEqual([v['path'] for v in slot['variations']], expected)
            self.assertTrue(all(v['weight'] == 1 for v in slot['variations']))
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as z:
                self.assertIsNone(z.testzip())
                self.assertNotIn('textures/blocks/grass_carried.png', z.namelist())
                self.assertNotIn('textures/blocks/grass_top_variant_0.png', z.namelist())
                self.assertEqual(z.read('textures/blocks/grass_top.png'), (BLOCKS / 'grass_top.png').read_bytes())
                for i in range(1, 4):
                    path = f'textures/blocks/grass_top_variant_{i}.png'
                    self.assertEqual(z.read(path), (ROOT / path).read_bytes())
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json'))['texture_data']['grass_top'], atlas['grass_top'])


if __name__ == '__main__':
    unittest.main()
