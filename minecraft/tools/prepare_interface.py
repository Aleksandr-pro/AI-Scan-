#!/usr/bin/env python3
"""Build the photo-inspired Bedrock interface overlay (Pillow only).

The supplied image is a mock-up, not a set of ready-to-use interface assets.
Extract clean, label-free material samples and redraw scalable borders. We do
not put screenshot text, icons, grids or controls into panel backgrounds.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

ROOT = Path('minecraft')
REFERENCE = ROOT / 'ui-reference/interface-reference.png'
MASKS = ROOT / 'ui-reference/vanilla'
PACK = ROOT / 'realistic-interface'
UI = PACK / 'textures/ui'
ARCHIVE = ROOT / 'realistic-interface.mcpack'
SCALE = 8


def sample(box, size, brightness=1.0):
    # Coordinates refer to this consistently scaled copy of the supplied mockup.
    with Image.open(REFERENCE) as im:
        ref = im.convert('RGB').resize((1536, 865), Image.Resampling.LANCZOS)
        texture = ref.crop(box).resize(size, Image.Resampling.LANCZOS)
    return ImageEnhance.Brightness(texture).enhance(brightness).convert('RGBA')


def slab(size, light=1.0):
    return sample((248, 145, 311, 168), size, light)


def rim(image, light, dark, width=3, inset=0):
    """Bevel edges while leaving the contents text-free and unobscured."""
    draw = ImageDraw.Draw(image)
    w, h = image.size
    for i in range(width):
        x, y = inset + i, inset + i
        draw.line([(x, h-1-y), (x, y), (w-1-x, y)], fill=light)
        draw.line([(x, h-1-y), (w-1-x, h-1-y), (w-1-x, y)], fill=dark)


def write(name, image, base=None, nine=None):
    image.save(UI / (name + '.png'), optimize=True)
    if base is not None:
        (UI / (name + '.json')).write_text(json.dumps({'nineslice_size': nine, 'base_size': base}, indent=2) + '\n')


def panel(name):
    # Nine-slicing stretches the middle 64x64 pixels across a whole panel.
    # Fit existing photo-stone into that region rather than blowing up a
    # tiny screenshot crop. Keep it light enough for dark in-game labels.
    with Image.open(ROOT / 'realistic-dirt/textures/blocks/stone.png') as source:
        gray = ImageOps.autocontrast(ImageOps.grayscale(source.convert('RGB')))
        stone = ImageOps.colorize(gray, (184, 178, 171), (232, 227, 219))
        stone = stone.resize((64, 64), Image.Resampling.LANCZOS).convert('RGBA')
    # Extend its edge pixels to the nine-slice borders so no seams appear.
    im = Image.new('RGBA', (128,128))
    im.paste(stone, (32,32))
    im.paste(stone.crop((0,0,64,1)).resize((64,32)), (32,0))
    im.paste(stone.crop((0,63,64,64)).resize((64,32)), (32,96))
    im.paste(stone.crop((0,0,1,64)).resize((32,64)), (0,32))
    im.paste(stone.crop((63,0,64,64)).resize((32,64)), (96,32))
    for x, y, sx, sy in ((0,0,0,0),(96,0,63,0),(0,96,0,63),(96,96,63,63)):
        im.paste(stone.getpixel((sx,sy)), (x,y,x+32,y+32))
    rim(im, (72, 65, 61, 255), (30, 28, 27, 255), 5)
    rim(im, (230, 222, 209, 255), (94, 87, 80, 255), 6, 5)
    rim(im, (172, 163, 150, 255), (117, 109, 101, 255), 2, 11)
    # Preserve each panel's vanilla outer silhouette, especially overlap_bottom.
    with Image.open(MASKS / (name + '.png')) as vanilla:
        alpha = vanilla.convert('RGBA').getchannel('A').resize((128, 128), Image.Resampling.NEAREST)
    im.putalpha(alpha)
    write(name, im, [16,16], 4)


def cell(name, brightness):
    size = 40
    im = sample((134, 66, 153, 87), (size,size), brightness)
    rim(im, (55, 49, 46, 255), (215, 206, 191, 255), 3)
    rim(im, (84, 76, 70, 255), (153, 145, 133, 255), 2, 3)
    write(name, im, [5,5], 1)


def selected_cell():
    im = sample((134,66,153,87), (32,32), 1.12)
    rim(im, (253,246,222,255), (192,176,133,255), 4)
    write('recipe_book_touch_cell_selected', im, [4,4], 1)


def button(name, base, nine, brightness, light, dark):
    size=(base[0]*SCALE,base[1]*SCALE)
    im=slab(size,brightness)
    rim(im, light, dark, 3)
    rim(im, (178,168,155,255), (65,60,56,255), 1, 3)
    write(name,im,base,nine)


def hotbar():
    im=sample((134,66,153,87),(160,176),0.45)
    # Semi-transparent dark centre leaves the world faintly visible.
    im.putalpha(Image.new('L',im.size,220))
    rim(im, (26,24,22,255), (16,15,14,255), 8)
    rim(im, (172,163,148,255), (77,72,66,255), 6, 8)
    rim(im, (55,50,46,255), (115,107,95,255), 3, 14)
    for i in range(9):
        write(f'hotbar_{i}',im)
    selection=Image.new('RGBA',(192,192),(0,0,0,0))
    rim(selection,(24,25,23,255),(24,25,23,255),8)
    rim(selection,(246,248,230,255),(158,173,155,255),10,8)
    rim(selection,(196,213,188,255),(93,108,94,255),5,18)
    write('selected_hotbar_slot',selection)


def effect():
    im=sample((134,66,153,87),(960,256),0.55)
    rim(im,(194,184,171,255),(37,34,32,255),8)
    rim(im,(80,75,70,255),(16,15,14,255),8,8)
    write('effect_background',im,[120,32],4)


def prepare_assets():
    UI.mkdir(parents=True,exist_ok=True)
    for name in ('dialog_background_opaque','dialog_background_opaque_overlap_bottom','background_panel'):
        panel(name)
    cell('cell_image',1.0)
    cell('cell_image_normal',1.18)
    cell('cell_image_darkgrey',0.85)
    selected_cell()
    # Light buttons use dark labels at rest, white labels on hover and press.
    for name, brightness, light, dark in (
        ('button_borderless_light',1.08,(232,226,216,255),(97,91,86,255)),
        ('button_borderless_lighthover',0.52,(218,207,188,255),(57,53,50,255)),
        ('button_borderless_lightpressed',0.42,(75,68,62,255),(198,185,167,255)),
        ('button_borderless_lightpressednohover',0.42,(75,68,62,255),(198,185,167,255)),
    ):
        button(name,[4,4],1,brightness,light,dark)
    for name, brightness, light, dark in (
        ('classic-button',0.62,(222,213,198,255),(67,61,56,255)),
        ('classic-button-hover',0.80,(246,238,218,255),(96,85,76,255)),
        ('classic-button-pressed',0.46,(93,84,76,255),(217,207,190,255)),
    ):
        button(name,[5,5],2,brightness,light,dark)
    hotbar()
    effect()


def main():
    # The current full build also creates the four screen-specific styles.
    from prepare_four_interfaces import main as build_four
    build_four()


if __name__=='__main__': main()
