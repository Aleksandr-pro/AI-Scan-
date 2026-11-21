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
    **{f'photo_{name}_panel':([16,16],4) for name in ('crafting','chest','furnace','enchanting','brewing','cartography','loom')},
    **{f'photo_menu_{name}':([4,4],1) for name in ('default','selected','hover','pressed','locked')},
}
EQUIPMENT=('helmet','chestplate','leggings','boots','shield')
NO_META=({f'hotbar_{i}':(80,88) for i in range(9)} | {'selected_hotbar_slot':(96,96)}
         | {f'empty_armor_slot_{n}':(64,64) for n in EQUIPMENT})
PATCHES={'inventory_screen.json':'crafting','inventory_screen_pocket.json':'crafting_pocket',
         'chest_screen.json':'chest','pocket_containers.json':'pocket_containers',
         'furnace_screen.json':'furnace','furnace_screen_pocket.json':'furnace_pocket',
         'enchanting_screen.json':'enchanting','enchanting_screen_pocket.json':'enchanting_pocket',
         'brewing_stand_screen.json':'brewing_stand','brewing_stand_screen_pocket.json':'brewing_stand_pocket',
         'cartography_screen.json':'cartography','cartography_screen_pocket.json':'cartography_pocket',
         'loom_screen.json':'loom','loom_screen_pocket.json':'loom_pocket'}

MENU_PATCHES={'pause_screen.json':'pause','settings_sections/settings_common.json':'settings_common',
              'mob_effect_screen.json':'mob_effect'}


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
        for name in ('crafting','chest','furnace','enchanting','brewing','cartography','loom'):
            with Image.open(UI/f'photo_{name}_panel.png') as im, Image.open(MASKS/'dialog_background_opaque.png') as vanilla:
                actual=im.convert('RGBA').getchannel('A')
                expected=vanilla.convert('RGBA').getchannel('A').resize((128,128),Image.Resampling.NEAREST)
                self.assertEqual(actual.tobytes(),expected.tobytes(),f'{name}: panel silhouette changed')
        with Image.open(UI/'photo_chest_panel.png') as im:
            red,green,blue,_=im.convert('RGBA').getpixel((64,64));self.assertGreater(red,green);self.assertGreater(green,blue)
        with Image.open(UI/'photo_enchanting_panel.png') as im:
            red,green,blue,_=im.convert('RGBA').getpixel((64,6));self.assertGreater(blue,green)
        for name in EQUIPMENT:
            with Image.open(UI/f'empty_armor_slot_{name}.png') as im:
                alpha=im.convert('RGBA').getchannel('A')
                self.assertEqual(alpha.getpixel((0,0)),0)
                bbox=alpha.point(lambda value:255 if value>127 else 0).getbbox()
                self.assertGreater(bbox[2]-bbox[0],20)
                self.assertLess(bbox[2]-bbox[0],64)
                self.assertGreater(len(im.convert('RGBA').getcolors(maxcolors=4096)),4)
        # They remain bound to empty slots; no player/real item is replaced.
        inv=read_sample(VANILLA/'inventory_screen.json')
        for name in EQUIPMENT:
            self.assertIn('textures/ui/empty_armor_slot_'+name,(VANILLA/'inventory_screen.json').read_text())
        self.assertEqual(inv['armor_overlay']['bindings'][0]['binding_name'],'#empty_armor_image_visible')
        self.assertEqual(inv['offhand_overlay']['bindings'][0]['binding_name'],'#empty_offhand_image_visible')

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
            ('brewing_stand_screen.json','brewing_stand_panel/root_panel/common_panel'):'brewing_stand.photo_brewing_bg',
            ('cartography_screen.json','cartography_panel/root_panel/common_panel'):'cartography.photo_cartography_bg',
            ('cartography_screen_pocket.json','left_panel/content/bg'):'cartography_pocket.photo_cartography_bg',
            ('cartography_screen_pocket.json','right_panel/content/bg'):'cartography_pocket.photo_cartography_bg',
            ('loom_screen.json','right_panel/common_panel'):'loom.photo_loom_bg',
            ('loom_screen.json','pattern_book_panel/bg'):'loom.photo_loom_bg',
            ('loom_screen_pocket.json','left_panel/content/bg'):'loom_pocket.photo_loom_bg',
            ('loom_screen_pocket.json','right_panel/content/bg'):'loom_pocket.photo_loom_bg',
        }
        for (file,target),value in expected_targets.items():
            self.assertEqual(json.loads((PACK/'ui'/file).read_text())[target]['$dialog_background'],value)
        for file,panel in [('pocket_containers.json','photo_chest_panel'),
                           ('furnace_screen_pocket.json','photo_furnace_panel'),
                           ('enchanting_screen_pocket.json','photo_enchanting_panel'),
                           ('brewing_stand_screen_pocket.json','photo_brewing_panel')]:
            patch=json.loads((PACK/'ui'/file).read_text())
            self.assertIn({'texture':'textures/ui/'+panel},patch.values())
        # Sample routing selects both classic and pocket layouts for these screens.
        for file,screen in [('chest_screen.json','small_chest_screen'),('chest_screen.json','large_chest_screen'),
                            ('furnace_screen.json','furnace_screen'),('enchanting_screen.json','enchanting_screen'),
                            ('brewing_stand_screen.json','brewing_stand_screen'),('cartography_screen.json','cartography_screen'),
                            ('loom_screen.json','loom_screen')]:
            doc=read_sample(VANILLA/file);_,node=control(doc,screen)
            routes=[v.get('requires') for v in node.get('variables',[])]
            self.assertIn('$desktop_screen',routes);self.assertIn('$pocket_screen',routes)

    def test_menu_patch_targets_and_bindings(self):
        patches={}
        for filename,namespace in MENU_PATCHES.items():
            vanilla=read_sample(VANILLA/filename)
            patch=json.loads((PACK/'ui'/filename).read_text())
            self.assertEqual(vanilla['namespace'],namespace)
            self.assertEqual(patch['namespace'],namespace)
            for target,change in patch.items():
                if target=='namespace':continue
                resolve_path(vanilla,target)
                # Only visual fields are touched; no control trees or bindings.
                self.assertTrue(all(k in ('texture','color') or k.startswith('$') for k in change))
                for value in change.values():
                    if isinstance(value,str) and value.startswith('textures/ui/'):
                        self.assertTrue((PACK/(value+'.png')).is_file())
            patches[filename]=patch
        pause=patches['pause_screen.json']
        for target in ('pause_button_template','grid_button_template'):
            self.assertEqual(pause[target]['$default_button_texture'],'textures/ui/photo_menu_default')
            self.assertEqual(pause[target]['$hover_button_texture'],'textures/ui/photo_menu_hover')
            self.assertEqual(pause[target]['$pressed_button_texture'],'textures/ui/photo_menu_pressed')
            self.assertEqual(pause[target]['$default_text_color'],[1,1,1])
        settings=patches['settings_sections/settings_common.json']
        toggle=settings['section_toggle_base']
        for key,state in [('$default_texture','default'),('$hover_texture','selected'),
                          ('$pressed_texture','hover'),('$pressed_no_hover_texture','pressed')]:
            self.assertEqual(toggle[key],f'textures/ui/photo_menu_{state}')
        self.assertEqual(settings['settings_content/background']['color'],[0.32]*3)
        effects=read_sample(VANILLA/'mob_effect_screen.json')
        for child,expr in [('default_background','(not #mob_effect_is_ambient)'),
                           ('ambient_background','#mob_effect_is_ambient')]:
            self.assertEqual(resolve_path(effects,'effect_background/'+child)['bindings'][0]['binding_name'],expr)
        self.assertEqual(effects['effect_icon']['texture'],'#texture')
        self.assertEqual(effects['effect_name']['text'],'#mob_effect_name')
        self.assertEqual(effects['effect_timer']['text'],'#mob_effect_timer')
        self.assertEqual(set(patches['mob_effect_screen.json']),{'namespace','main_background',
                         'effect_background/default_background','effect_background/ambient_background'})
        samples=[]
        for name in ('default','selected','hover','pressed','locked'):
            with Image.open(UI/f'photo_menu_{name}.png') as im:
                self.assertEqual(im.size,(32,32))
                samples.append(im.convert('RGBA').getpixel((16,16)))
                self.assertLess(max(samples[-1][:3]),160)
        self.assertEqual(len(set(samples)),5)

    def test_archive_and_scope(self):
        manifest=json.loads((PACK/'manifest.json').read_text())
        uuid.UUID(manifest['header']['uuid']);uuid.UUID(manifest['modules'][0]['uuid'])
        self.assertNotEqual(manifest['header']['uuid'],json.loads((MAIN/'manifest.json').read_text())['header']['uuid'])
        self.assertEqual(manifest['header']['version'],[1,3,0])
        expected={'manifest.json'} | {f'textures/ui/{name}.png' for name in SIDECARS | NO_META} | {f'textures/ui/{name}.json' for name in SIDECARS} | {f'ui/{p}' for p in PATCHES | MENU_PATCHES}
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
                self.assertEqual(json.loads(z.read('manifest.json'))['header']['version'],[2, 3, 0])
                for name in expected-{'manifest.json'}:
                    self.assertEqual(z.read(name),(PACK/name).read_bytes())
                    self.assertEqual((MAIN/name).read_bytes(),(PACK/name).read_bytes())


if __name__=='__main__':unittest.main()
