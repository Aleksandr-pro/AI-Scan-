#!/usr/bin/env python3
"""Draw an antialiased, translucent raindrop sprite for the VV pack (Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path('minecraft/realistic-atmosphere/textures/particle/realistic_rain_drop.png')
SCALE = 4
image = Image.new('RGBA', (64 * SCALE, 64 * SCALE), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
# Small translucent splash droplet, not a black square or solid white dot.
draw.ellipse((23*SCALE, 8*SCALE, 41*SCALE, 56*SCALE), fill=(205, 225, 232, 105))
draw.ellipse((26*SCALE, 10*SCALE, 33*SCALE, 48*SCALE), fill=(242, 250, 255, 170))
draw.ellipse((27*SCALE, 13*SCALE, 30*SCALE, 35*SCALE), fill=(255, 255, 255, 205))
image = image.filter(ImageFilter.GaussianBlur(1.5 * SCALE))
image = image.resize((64, 64), Image.Resampling.LANCZOS)
OUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUT, optimize=True)
print(f'Saved {OUT}')
