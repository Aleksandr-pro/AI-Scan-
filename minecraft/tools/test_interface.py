#!/usr/bin/env python3
"""Validate the separate UI resource pack, without claiming in-game rendering."""
import hashlib
import json
import unittest
import uuid
import zipfile
from pathlib import Path
from PIL import Image
from prepare_interface import REFERENCE, MASKS, PACK, UI, ARCHIVE

SIDECARS={
    'dialog_background_opaque':([16,16],4),
    'dialog_background_opaque_overlap_bottom':([16,16],4),
    'background_panel':([16,16],4),
    'cell_image':([5,5],1), 'cell_image_normal':([5,5],1),
    'cell_image_darkgrey':([5,5],1), 'recipe_book_touch_cell_selected':([4,4],1),
    'button_borderless_light':([4,4],1), 'button_borderless_lighthover':([4,4],1),
    'button_borderless_lightpressed':([4,4],1), 'button_borderless_lightpressednohover':([4,4],1),
    'classic-button':([5,5],2), 'classic-button-hover':([5,5],2),
    'classic-button-pressed':([5,5],2), 'effect_background':([120,32],4),
}
NO_META={f'hotbar_{i}':(160,176) for i in range(9)} | {'selected_hotbar_slot':(192,192)}


class InterfaceTests(unittest.TestCase):
    def test_sources(self):
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                         '046f726674714b12db051fdf40f03a4eae8adf41e160d16023f64c88099d13af')
        with Image.open(REFERENCE) as im:self.assertEqual(im.size,(1672,941))
        for n in ('dialog_background_opaque','dialog_background_opaque_overlap_bottom','background_panel'):
            with Image.open(MASKS/(n+'.png')) as im:self.assertEqual(im.size,(16,16))

    def test_nineslice_and_states(self):
        for name,(base,nine) in SIDECARS.items():
            with self.subTest(name=name):
                self.assertEqual(json.loads((UI/(name+'.json')).read_text()),{'base_size':base,'nineslice_size':nine})
                with Image.open(UI/(name+'.png')) as im:
                    self.assertEqual((im.mode,im.size),('RGBA',tuple(i*8 for i in base)))
        for name,size in NO_META.items():
            with Image.open(UI/(name+'.png')) as im:self.assertEqual((im.mode,im.size),('RGBA',size))
            self.assertFalse((UI/(name+'.json')).exists())
        with Image.open(UI/'selected_hotbar_slot.png') as im:
            self.assertEqual(im.getpixel((96,96))[3],0)
            self.assertGreater(im.getpixel((96,15))[3],200)
        with Image.open(UI/'hotbar_0.png') as im:self.assertGreater(im.getpixel((80,88))[3],0)
        samples={}
        for name in ('button_borderless_light','button_borderless_lighthover','button_borderless_lightpressed'):
            with Image.open(UI/(name+'.png')) as im:samples[name]=sum(im.getpixel((16,16))[:3])/3
        self.assertGreater(samples['button_borderless_light'],samples['button_borderless_lighthover'])
        self.assertGreater(samples['button_borderless_lighthover'],samples['button_borderless_lightpressed'])
        with Image.open(UI/'cell_image.png') as im:
            self.assertLess(sum(im.getpixel((20,20))[:3])/3,160)

    def test_archive_and_scope(self):
        manifest=json.loads((PACK/'manifest.json').read_text())
        uuid.UUID(manifest['header']['uuid']);uuid.UUID(manifest['modules'][0]['uuid'])
        self.assertNotEqual(manifest['header']['uuid'],json.loads(Path('minecraft/realistic-dirt/manifest.json').read_text())['header']['uuid'])
        self.assertEqual(manifest['header']['version'],[1,0,0])
        expected={'manifest.json'} | {f'textures/ui/{name}.png' for name in SIDECARS | NO_META} | {f'textures/ui/{name}.json' for name in SIDECARS}
        with zipfile.ZipFile(ARCHIVE) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(set(z.namelist()),expected)
            for name in expected:self.assertEqual(z.read(name),(PACK/name).read_bytes())
            self.assertFalse(any(n.startswith('ui/') for n in z.namelist()))
            self.assertNotIn('textures/ui/heart.png',z.namelist())
            self.assertNotIn('textures/ui/cell_image_red.png',z.namelist())


if __name__=='__main__':unittest.main()
