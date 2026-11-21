#!/usr/bin/env python3
"""Build four screen-specific Bedrock interface styles and integrate them.

Starts with the original photo-inspired assets, adds targeted JSON UI overrides
for classic and pocket layouts, and copies the overlay into the main pack.
The patches modify backgrounds only; the game's slots and controls remain live.
Run this before build_variations.py and build_vibrant_packs.py --textures-only.
"""
from pathlib import Path
import json
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageEnhance, ImageOps
import prepare_interface as base

MAIN=Path('minecraft/realistic-dirt')


def nine_patch_body(source, palette):
    """Build a 16x16 logical panel with a detailed 64x64 centre and edges."""
    with Image.open(source) as image:
        gray=ImageOps.autocontrast(ImageOps.grayscale(image.convert('RGB')))
        tile=ImageOps.colorize(gray, palette[0], palette[1]).resize((64,64),Image.Resampling.LANCZOS).convert('RGBA')
    im=Image.new('RGBA',(128,128))
    im.paste(tile,(32,32))
    im.paste(tile.crop((0,0,64,1)).resize((64,32)),(32,0))
    im.paste(tile.crop((0,63,64,64)).resize((64,32)),(32,96))
    im.paste(tile.crop((0,0,1,64)).resize((32,64)),(0,32))
    im.paste(tile.crop((63,0,64,64)).resize((32,64)),(96,32))
    for x,y,sx,sy in ((0,0,0,0),(96,0,63,0),(0,96,0,63),(96,96,63,63)):
        im.paste(tile.getpixel((sx,sy)),(x,y,x+32,y+32))
    return im


def make_panel(name, source, palette, border):
    im=nine_patch_body(source,palette)
    base.rim(im,border[0],border[1],4)
    base.rim(im,border[2],border[3],6,4)
    base.rim(im,border[4],border[5],2,10)
    with Image.open(base.MASKS/'dialog_background_opaque.png') as mask:
        im.putalpha(mask.convert('RGBA').getchannel('A').resize((128,128),Image.Resampling.NEAREST))
    base.write(name,im,[16,16],4)


def write_patch(filename, doc):
    path=base.PACK/'ui'/filename
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def patch_files():
    def background(texture):
        return {'type':'image','texture':'textures/ui/'+texture}
    # Slash paths target existing children without replacing controls or bindings.
    write_patch('inventory_screen.json', {
        'namespace':'crafting',
        'photo_crafting_bg':background('photo_crafting_panel'),
        'player_inventory/common_panel':{'$dialog_background':'crafting.photo_crafting_bg'},
    })
    write_patch('inventory_screen_pocket.json', {
        'namespace':'crafting_pocket',
        'photo_crafting_bg':background('photo_crafting_panel'),
        'left_panel/left_background':{'$dialog_background':'crafting_pocket.photo_crafting_bg'},
        'right_panel/right_background':{'$dialog_background':'crafting_pocket.photo_crafting_bg'},
    })
    write_patch('chest_screen.json', {
        'namespace':'chest',
        'photo_chest_bg':background('photo_chest_panel'),
        'small_chest_panel/root_panel/common_panel':{'$dialog_background':'chest.photo_chest_bg'},
        'large_chest_panel/root_panel/common_panel':{'$dialog_background':'chest.photo_chest_bg'},
    })
    write_patch('pocket_containers.json', {
        'namespace':'pocket_containers',
        # Pocket chest screens inherit the same panel control as other
        # pocket containers; overriding its root avoids a brittle inherited
        # child selector, but intentionally affects those containers too.
        'background_panel':{'texture':'textures/ui/photo_chest_panel'},
    })
    write_patch('furnace_screen.json', {
        'namespace':'furnace',
        'photo_furnace_bg':background('photo_furnace_panel'),
        'right_panel/common_panel':{'$dialog_background':'furnace.photo_furnace_bg'},
    })
    write_patch('furnace_screen_pocket.json', {
        'namespace':'furnace_pocket',
        'background_image':{'texture':'textures/ui/photo_furnace_panel'},
    })
    write_patch('enchanting_screen.json', {
        'namespace':'enchanting',
        'photo_enchanting_bg':background('photo_enchanting_panel'),
        'enchanting_panel/root_panel/common_panel':{'$dialog_background':'enchanting.photo_enchanting_bg'},
    })
    write_patch('enchanting_screen_pocket.json', {
        'namespace':'enchanting_pocket',
        'background_image':{'texture':'textures/ui/photo_enchanting_panel'},
    })


def main():
    # Use the original reference-derived shapes, states and vanilla metadata.
    base.prepare_assets()
    # Keep an integer 4x resolution: smaller atlas footprint and archive, while
    # retaining vanilla logical base sizes and nine-slice borders unchanged.
    for path in base.UI.glob('*.png'):
        with Image.open(path) as im:
            im.resize((im.width//2, im.height//2),Image.Resampling.LANCZOS).save(path,optimize=True)
    stone=MAIN/'textures/blocks/stone.png'
    wood=MAIN/'textures/blocks/planks_oak.png'
    stone_border=((65,60,56,255),(27,25,24,255),(235,227,215,255),(88,81,76,255),(163,154,142,255),(113,104,95,255))
    wood_border=((49,30,19,255),(30,18,12,255),(231,185,128,255),(101,62,34,255),(170,119,74,255),(81,47,28,255))
    purple_border=((48,36,49,255),(25,20,29,255),(197,175,204,255),(88,67,104,255),(149,129,162,255),(78,59,89,255))
    make_panel('photo_crafting_panel',stone,((183,178,172),(235,229,219)),stone_border)
    make_panel('photo_furnace_panel',stone,((165,163,158),(229,224,215)),stone_border)
    make_panel('photo_chest_panel',wood,((165,126,92),(243,219,186)),wood_border)
    make_panel('photo_enchanting_panel',stone,((177,170,178),(229,225,226)),purple_border)
    # Palette encoding of these low-colour HUD sprites reduces 9 duplicate
    # hotbar files and the effect panel without removing any runtime paths.
    for name in [*(f'hotbar_{i}' for i in range(9)), 'effect_background']:
        path = base.UI/(name+'.png')
        with Image.open(path) as im:
            im.convert('RGBA').quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                                        dither=Image.Dither.NONE).save(path, optimize=True)
    patch_files()
    # Both separate and combined distribution use exactly the same UI files.
    for folder in ('textures/ui','ui'):
        shutil.copytree(base.PACK/folder,MAIN/folder,dirs_exist_ok=True)
    with zipfile.ZipFile(base.ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(base.PACK.rglob('*')):
            if path.is_file(): z.write(path,path.relative_to(base.PACK).as_posix())
    print(f'Built {base.ARCHIVE}; copied UI into main pack source')


if __name__=='__main__':main()
