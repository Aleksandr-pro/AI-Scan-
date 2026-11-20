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


def mean_diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


class GrassTopTests(unittest.TestCase):
    def test_images_preserve_distinct_sources_and_common_edges(self):
        images = []
        for i, source in enumerate(FILES):
            with Image.open(BLOCKS / f'grass_top_variant_{i}.png') as image:
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
        self.assertEqual((BLOCKS / 'grass_top.png').read_bytes(), (BLOCKS / 'grass_top_variant_0.png').read_bytes())
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

    def test_atlas_and_both_packs(self):
        atlas = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        tops = atlas['grass_top']['textures']
        self.assertEqual(len(tops), 17)
        expected = ['textures/blocks/grass_top'] + [f'textures/blocks/grass_top_variant_{i}' for i in range(1, 4)]
        for slot in tops:
            self.assertEqual([v['path'] for v in slot['variations']], expected)
            self.assertTrue(all(v['weight'] == 1 for v in slot['variations']))
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(z.read('textures/blocks/grass_top.png'), (BLOCKS / 'grass_top.png').read_bytes())
                for i in range(1, 4):
                    path = f'textures/blocks/grass_top_variant_{i}.png'
                    self.assertEqual(z.read(path), (ROOT / path).read_bytes())
                self.assertEqual(json.loads(z.read('textures/terrain_texture.json'))['texture_data']['grass_top'], atlas['grass_top'])


if __name__ == '__main__':
    unittest.main()
