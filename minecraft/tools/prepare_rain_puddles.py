#!/usr/bin/env python3
"""Generate original, lightweight puddle and ripple particle sprites (Pillow)."""
import math
from pathlib import Path
from PIL import Image

OUT = Path('minecraft/realistic-atmosphere/textures/particle')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    size = 128
    puddle = Image.new('RGBA', (size, size))
    ripple = Image.new('RGBA', (size, size))
    for y in range(size):
        for x in range(size):
            dx = (x + 0.5 - size / 2) / (size / 2)
            dy = (y + 0.5 - size / 2) / (size / 2)
            angle = math.atan2(dy, dx)
            radius = math.hypot(dx, dy)
            edge = 0.76 + 0.065 * math.sin(3 * angle + 0.4) + 0.045 * math.sin(7 * angle - 0.8) + 0.025 * math.sin(11 * angle)
            fade = max(0.0, min(1.0, (edge - radius) / 0.09))
            # A translucent cool patch with a modest sky glint, never opaque ground paint.
            glint = math.exp(-(((dx + 0.22) / 0.30) ** 2 + ((dy + 0.20) / 0.13) ** 2))
            puddle.putpixel((x, y), (142 + int(35 * glint), 177 + int(30 * glint), 196 + int(25 * glint), int(fade * (74 + 55 * glint))))
            # Two soft concentric lines. The particle itself grows and fades.
            ring = math.exp(-((radius - 0.69) / 0.026) ** 2) + 0.45 * math.exp(-((radius - 0.46) / 0.025) ** 2)
            ripple.putpixel((x, y), (205, 226, 237, min(180, int(145 * ring))))
    puddle.save(OUT / 'rain_puddle.png', optimize=True)
    ripple.save(OUT / 'rain_ripple.png', optimize=True)


if __name__ == '__main__':
    main()
