#!/usr/bin/env python3
"""Check the photo-derived transparent frame and isolated block mapping."""
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from prepare_glass import OUTPUT, SIZE, prepare

ROOT = Path('minecraft/realistic-dirt')


class GlassTests(unittest.TestCase):
    def test_center_is_transparent_frame_is_retained(self):
        with Image.open(OUTPUT) as img:
            self.assertEqual((img.mode, img.size), ('RGBA', (SIZE, SIZE)))
            self.assertEqual(img.tobytes(), prepare().tobytes())
            alpha = img.getchannel('A')
            # No checkerboard pixels survive in the centre, even though the
            # input is opaque RGB; preserve a visible frame on all four sides.
            self.assertEqual(alpha.crop((25, 25, 487, 487)).getextrema(), (0, 0))
            for x, y in ((256, 5), (256, 506), (5, 256), (506, 256)):
                self.assertGreater(alpha.getpixel((x, y)), 240)
                rgb = img.getpixel((x, y))[:3]
                self.assertLess(max(rgb), 160)

    def test_isolated_mapping_and_both_distributions(self):
        blocks = json.loads((ROOT / 'blocks.json').read_text(encoding='utf-8'))
        terrain = json.loads((ROOT / 'textures/terrain_texture.json').read_text())['texture_data']
        self.assertEqual(blocks['glass'], {'sound': 'glass', 'textures': 'realistic_clear_glass'})
        self.assertNotIn('glass_pane', blocks)
        self.assertNotIn('glass', terrain)  # keep vanilla shared pane texture
        self.assertEqual(terrain['realistic_clear_glass']['textures'], 'textures/blocks/realistic_clear_glass')
        self.assertFalse((ROOT / 'textures/blocks/glass.png').exists())
        for pack in ('realistic-dirt.mcpack', 'realistic-dirt-vibrant.mcpack'):
            with zipfile.ZipFile(Path('minecraft') / pack) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read('textures/blocks/realistic_clear_glass.png'), OUTPUT.read_bytes())
                self.assertEqual(json.loads(archive.read('blocks.json'))['glass'], blocks['glass'])
                self.assertEqual(json.loads(archive.read('textures/terrain_texture.json'))['texture_data']['realistic_clear_glass'], terrain['realistic_clear_glass'])
                self.assertNotIn('textures/blocks/glass.png', archive.namelist())
                self.assertNotIn('glass-reference/frame.png', archive.namelist())


if __name__ == '__main__':
    unittest.main()
