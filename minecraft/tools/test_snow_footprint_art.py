#!/usr/bin/env python3
"""Check footprint alpha and regeneration from the actual main-pack snow (Pillow)."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageChops, ImageStat
import prepare_snow_footprint as art

class ArtworkTests(unittest.TestCase):
    def test_regeneration_alpha_and_colour_match(self):
        generated = art.prepare()
        with Image.open(art.OUTPUT) as saved:
            self.assertEqual((saved.size,saved.mode),((256,512),'RGBA'))
            self.assertEqual(saved.tobytes(),generated.tobytes())
        alpha=generated.getchannel('A')
        self.assertEqual(alpha.getpixel((0,0)),0)
        self.assertEqual(alpha.getpixel((128,256)),255)
        self.assertTrue(0 < alpha.getpixel((0,256)) < 255)
        with Image.open(art.SNOW) as snow:
            target=ImageStat.Stat(snow.convert('RGB')).mean
        rgb=generated.convert('RGB')
        left=ImageStat.Stat(rgb.crop((15,50,50,462))).mean
        right=ImageStat.Stat(rgb.crop((206,50,241,462))).mean
        self.assertTrue(all(abs((l+r)/2 - s)<8 for l,r,s in zip(left,right,target)))

    def test_snow_source_changes_colour_but_not_the_footprint_mask(self):
        before=art.prepare()
        with tempfile.TemporaryDirectory() as tmp:
            other=Path(tmp)/'other.png'
            Image.new('RGB',(512,512),(130,135,150)).save(other)
            after=art.prepare(snow_path=other)
        self.assertIsNone(ImageChops.difference(before.getchannel('A'),after.getchannel('A')).getbbox())
        self.assertIsNotNone(ImageChops.difference(before.convert('RGB'),after.convert('RGB')).getbbox())

if __name__=='__main__':unittest.main()
