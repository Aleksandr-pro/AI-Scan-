#!/usr/bin/env python3
"""Static UI and archive checks against Bedrock samples; not a game test."""
import hashlib
import json
import re
import unittest
import uuid
import zipfile
from pathlib import Path
from PIL import Image
from prepare_interface import REFERENCE, MASKS, PACK, UI, ARCHIVE

VANILLA=Path('minecraft/ui-reference/vanilla-ui')
MAIN=Path('minecraft/realistic-dirt')
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
    **{f'photo_{name}_panel':([16,16],4) for name in ('crafting','chest','furnace','enchanting')},
}
NO_META={f'hotbar_{i}':(80,88) for i in range(9)} | {'selected_hotbar_slot':(96,96)}
PATCHES={'inventory_screen.json':'crafting','inventory_screen_pocket.json':'crafting_pocket',
         'chest_screen.json':'chest','pocket_containers.json':'pocket_containers',
         'furnace_screen.json':'furnace','furnace_screen_pocket.json':'furnace_pocket',
         'enchanting_screen.json':'enchanting','enchanting_screen_pocket.json':'enchanting_pocket'}


def read_sample(path):
    text=path.read_text(encoding='utf-8')
    return json.loads(re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S))


def control(doc, name):
    for key,value in doc.items():
        if key.split('@')[0]==name:return key,value
    raise AssertionError(f'No root control {name}')


def children(doc, key, value, seen=None):
    seen=set() if seen is None else seen
    # For the two pocket chests, bg comes from their local @panel parent.
    result=[]
    if '@' in key:
        parent=key.split('@',1)[1]
        if '.' not in parent and not parent.startswith('$') and parent not in seen:
            seen.add(parent)
            try: pk,pv=control(doc,parent)
            except AssertionError: pass
            else: result.extend(children(doc,pk,pv,seen))
    result.extend(value.get('controls',[]))
    return result


def resolve_path(doc,path):
    parts=path.split('/')
    key,node=control(doc,parts[0])
    for part in parts[1:]:
        matches=[(k,v) for c in children(doc,key,node) for k,v in c.items() if k.split('@')[0]==part]
        if not matches:raise AssertionError(f'No child {part} in {path}')
        key,node=matches[-1]
    return node


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
                    self.assertIn(im.mode,('RGBA','P'))
                    self.assertEqual(im.size,tuple(i*(8 if name.startswith('photo_') else 4) for i in base))
        for name,size in NO_META.items():
            with Image.open(UI/(name+'.png')) as im:self.assertEqual(im.size,size)
            self.assertFalse((UI/(name+'.json')).exists())
        with Image.open(UI/'selected_hotbar_slot.png') as im:
            self.assertEqual(im.convert('RGBA').getpixel((48,48))[3],0)
            self.assertGreater(im.convert('RGBA').getpixel((48,8))[3],200)
        with Image.open(UI/'hotbar_0.png') as im:self.assertGreater(im.convert('RGBA').getpixel((40,44))[3],0)
        samples={}
        for name in ('button_borderless_light','button_borderless_lighthover','button_borderless_lightpressed'):
            with Image.open(UI/(name+'.png')) as im:samples[name]=sum(im.convert('RGBA').getpixel((8,8))[:3])/3
        self.assertGreater(samples['button_borderless_light'],samples['button_borderless_lighthover'])
        self.assertGreater(samples['button_borderless_lighthover'],samples['button_borderless_lightpressed'])
        with Image.open(UI/'cell_image.png') as im:self.assertLess(sum(im.getpixel((10,10))[:3])/3,160)
        with Image.open(UI/'photo_chest_panel.png') as im:
            red,green,blue,_=im.getpixel((64,64));self.assertGreater(red,green);self.assertGreater(green,blue)
        with Image.open(UI/'photo_enchanting_panel.png') as im:
            red,green,blue,_=im.getpixel((64,6));self.assertGreater(blue,green)

    def test_patch_targets_exist_in_vanilla_samples(self):
        for file,namespace in PATCHES.items():
            with self.subTest(file=file):
                vanilla=read_sample(VANILLA/file)
                patch=json.loads((PACK/'ui'/file).read_text())
                self.assertEqual(vanilla['namespace'],namespace)
                self.assertEqual(patch['namespace'],namespace)
                for name,delta in patch.items():
                    if name=='namespace':continue
                    if name.startswith('photo_'):
                        self.assertEqual(delta['type'],'image')
                        self.assertTrue((PACK/(delta['texture']+'.png')).is_file())
                    else:
                        resolve_path(vanilla,name)
                        self.assertTrue(set(delta)<= {'texture','$dialog_background'})
                        if 'texture' in delta:self.assertTrue((PACK/(delta['texture']+'.png')).is_file())
                        if '$dialog_background' in delta:
                            ns,control_name=delta['$dialog_background'].split('.')
                            self.assertEqual(ns,namespace);self.assertIn(control_name,patch)
        expected_targets={
            ('inventory_screen.json','player_inventory/common_panel'):'crafting.photo_crafting_bg',
            ('inventory_screen_pocket.json','right_panel/right_background'):'crafting_pocket.photo_crafting_bg',
            ('chest_screen.json','small_chest_panel/root_panel/common_panel'):'chest.photo_chest_bg',
            ('chest_screen.json','large_chest_panel/root_panel/common_panel'):'chest.photo_chest_bg',
            ('furnace_screen.json','right_panel/common_panel'):'furnace.photo_furnace_bg',
            ('enchanting_screen.json','enchanting_panel/root_panel/common_panel'):'enchanting.photo_enchanting_bg',
        }
        for (file,target),value in expected_targets.items():
            self.assertEqual(json.loads((PACK/'ui'/file).read_text())[target]['$dialog_background'],value)
        for file,panel in [('pocket_containers.json','photo_chest_panel'),
                           ('furnace_screen_pocket.json','photo_furnace_panel'),
                           ('enchanting_screen_pocket.json','photo_enchanting_panel')]:
            patch=json.loads((PACK/'ui'/file).read_text())
            self.assertIn({'texture':'textures/ui/'+panel},patch.values())
        # Sample routing selects both classic and pocket layouts for these screens.
        for file,screen in [('chest_screen.json','small_chest_screen'),('chest_screen.json','large_chest_screen'),
                            ('furnace_screen.json','furnace_screen'),('enchanting_screen.json','enchanting_screen')]:
            doc=read_sample(VANILLA/file);_,node=control(doc,screen)
            routes=[v.get('requires') for v in node.get('variables',[])]
            self.assertIn('$desktop_screen',routes);self.assertIn('$pocket_screen',routes)

    def test_archive_and_scope(self):
        manifest=json.loads((PACK/'manifest.json').read_text())
        uuid.UUID(manifest['header']['uuid']);uuid.UUID(manifest['modules'][0]['uuid'])
        self.assertNotEqual(manifest['header']['uuid'],json.loads((MAIN/'manifest.json').read_text())['header']['uuid'])
        self.assertEqual(manifest['header']['version'],[1,1,0])
        expected={'manifest.json'} | {f'textures/ui/{name}.png' for name in SIDECARS | NO_META} | {f'textures/ui/{name}.json' for name in SIDECARS} | {f'ui/{p}' for p in PATCHES}
        with zipfile.ZipFile(ARCHIVE) as z:
            self.assertIsNone(z.testzip());self.assertEqual(set(z.namelist()),expected)
            for name in expected:self.assertEqual(z.read(name),(PACK/name).read_bytes())
            self.assertNotIn('textures/ui/heart.png',z.namelist())
            self.assertNotIn('textures/ui/cell_image_red.png',z.namelist())
        for package in ('realistic-dirt.mcpack','realistic-dirt-vibrant.mcpack'):
            path=Path('minecraft')/package
            self.assertLess(path.stat().st_size,100*1024*1024)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(json.loads(z.read('manifest.json'))['header']['version'],[1,99,0])
                for name in expected-{'manifest.json'}:
                    self.assertEqual(z.read(name),(PACK/name).read_bytes())
                    self.assertEqual((MAIN/name).read_bytes(),(PACK/name).read_bytes())


if __name__=='__main__':unittest.main()
