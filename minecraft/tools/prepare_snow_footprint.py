#!/usr/bin/env python3
"""Create an alpha-feathered print from the user's reference image (Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / 'snow-footprints'
source = Image.open(ROOT / 'reference/footprints.png').convert('RGB')
# The left print, including its rough rim. The source is the user-provided image.
image = source.crop((365, 395, 632, 850)).resize((256, 512), Image.Resampling.LANCZOS).convert('RGBA')
# Fade only the surrounding snow, leaving the crater and granular rim intact.
mask = Image.new('L', image.size, 0)
draw = ImageDraw.Draw(mask)
draw.rounded_rectangle((17, 16, 238, 495), radius=42, fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(14))
image.putalpha(mask)
output = ROOT / 'resources/textures/particle/aegis_snow_footprint.png'
output.parent.mkdir(parents=True, exist_ok=True)
image.save(output, optimize=True)
print('Wrote', output)
