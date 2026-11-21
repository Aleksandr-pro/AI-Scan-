#!/usr/bin/env python3
"""Create targeted pause/settings/effect styling for the interface build.

Uses the user's UI mockup as a material reference. No screenshots of labels,
icons or interactive controls are pasted into the textures. Called by
prepare_four_interfaces.py before that script packages both distributions.
"""
import json
from pathlib import Path
from PIL import Image
import prepare_interface as base

STATES={
    # Texture brightness and raised border colours. Label/glyph colours are
    # overridden to white only for controls using these dark backgrounds.
    'default':(0.39,(177,169,156,255),(47,43,40,255)),
    'selected':(0.50,(214,203,177,255),(86,76,59,255)),
    'hover':(0.53,(239,228,209,255),(90,79,68,255)),
    'pressed':(0.30,(84,77,68,255),(182,169,150,255)),
    'locked':(0.24,(124,119,110,255),(46,42,39,255)),
}


def make_menu_textures():
    for state,(brightness,light,dark) in STATES.items():
        image=base.slab((32,32),brightness)
        base.rim(image,light,dark,2)
        base.rim(image,(130,123,112,255),(44,42,39,255),1,2)
        # Tiny, opaque decorative surfaces: a 128-colour palette keeps both
        # near-100 MiB archives below the hosting limit with room to spare.
        image=image.convert('RGB').quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
        base.write('photo_menu_'+state,image,[4,4],1)


def make_patches(write_patch):
    t=lambda state:'textures/ui/photo_menu_'+state
    white=[1.0,1.0,1.0]
    button_style={
        '$default_button_texture':t('default'),
        '$hover_button_texture':t('hover'),
        '$pressed_button_texture':t('pressed'),
        '$default_text_color':white,
        '$hover_text_color':white,
        '$pressed_text_color':white,
    }
    write_patch('pause_screen.json',{
        'namespace':'pause',
        # All descendants retain their vanilla text, bindings and button IDs.
        'pause_button_template':button_style,
        'grid_button_template':button_style,
    })
    write_patch('settings_sections/settings_common.json',{
        'namespace':'settings_common',
        # Categories and their four checked/hover states remain a live toggle.
        'section_toggle_base':{
            '$default_texture':t('default'),
            '$hover_texture':t('selected'),
            '$pressed_texture':t('hover'),
            '$pressed_no_hover_texture':t('pressed'),
            '$locked_texture':t('locked'),
            '$default_text_color':white,
            '$hover_text_color':white,
            '$default_checked_text_color':white,
            '$hover_checked_text_color':white,
            '$default_glyph_color':white,
            '$hover_glyph_color':white,
            '$default_checked_glyph_color':white,
            '$hover_checked_glyph_color':white,
            '$locked_alpha':0.65,
        },
        # Retain all original sizing, layer, bindings and controls. The tint
        # keeps white setting descriptions readable on a subdued stone photo.
        'settings_content/background':{
            'texture':'textures/ui/photo_furnace_panel',
            'color':[0.32,0.32,0.32],
        },
    })
    write_patch('mob_effect_screen.json',{
        'namespace':'mob_effect',
        'main_background':{'texture':t('pressed')},
        'effect_background/default_background':{'texture':t('default')},
        'effect_background/ambient_background':{'texture':t('selected')},
    })


def build(write_patch):
    make_menu_textures()
    make_patches(write_patch)
