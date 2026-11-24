#!/usr/bin/env python3
"""Match the reference footprint to the ordinary-snow texture (Pillow).

Preserve the original footprint and baked-in shading; subtly match colours
and mix a little grain from the main pack's v2.7.6 snow. This is a fixed
photographic decal, not a dynamic deformation or a guarantee of matching
other packs, lighting, snow rotations, or game renderers.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'snow-footprints/reference/footprints.png'
SNOW = ROOT / 'realistic-dirt/textures/blocks/realistic_snow_top.png'
OUTPUT = ROOT / 'snow-footprints/resources/textures/particle/aegis_snow_footprint.png'


def prepare(reference=REFERENCE, snow_path=SNOW):
    with Image.open(reference) as source:
        original = source.convert('RGB').crop((365, 395, 632, 850)).resize((256, 512), Image.Resampling.LANCZOS)
    with Image.open(snow_path) as source_snow:
        snow = source_snow.convert('RGB')
    if snow.size != (512, 512):
        raise ValueError('Expected the main-pack 512×512 snow texture')
    # Estimate background snow from the two side strips, not from the dark
    # depression. Keep the shadows: only a small brightness-dependent offset
    # is applied to the photograph before adding a little matching snow grain.
    left = original.crop((0, 0, 35, 512))
    right = original.crop((221, 0, 256, 512))
    target = ImageStat.Stat(snow).mean
    source_mean = [(a + b) / 2 for a, b in zip(ImageStat.Stat(left).mean, ImageStat.Stat(right).mean)]
    channels = []
    for channel, desired, before in zip(original.split(), target, source_mean):
        shift = desired - before
        lookup = [max(0, min(255, round(value + shift * (0.35 + 0.65 * value / 255)))) for value in range(256)]
        channels.append(channel.point(lookup))
    calibrated = Image.merge('RGB', channels)
    calibrated = Image.blend(calibrated, snow.crop((128, 0, 384, 512)), 0.10).convert('RGBA')
    # The old shape and faded edges are preserved; no rectangular photo border.
    mask = Image.new('L', calibrated.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((17, 16, 238, 495), radius=42, fill=255)
    calibrated.putalpha(mask.filter(ImageFilter.GaussianBlur(14)))
    return calibrated


def main():
    image = prepare()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print('Wrote', OUTPUT)

if __name__ == '__main__':
    main()
