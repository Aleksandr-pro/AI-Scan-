#!/usr/bin/env python3
"""Generate the root Bedrock catalog from pinned registries and the main pack.

Run from repository root: python3 minecraft/tools/build_texture_catalog.py
Manual status corrections live in minecraft/catalog-source/status-overrides.json.
No network or external Python packages required.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'minecraft/catalog-source/bedrock-1.26.30.5'
OVERRIDES=ROOT/'minecraft/catalog-source/status-overrides.json'
PACK=ROOT/'minecraft/realistic-dirt.mcpack'
OUTPUT=ROOT/'КАТАЛОГ-МАЙНКРАФТ.md'
ICONS={'done':'✅','partial':'🟨','missing':'❌','review':'❔'}


def load_json(name):
    text=(SOURCE/name).read_text(encoding='utf-8-sig')
    # Mojang terrain/item atlases have a leading comment line, not strict JSON.
    return json.loads('\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('//')))


def lang(name):
    result={}
    for raw in (SOURCE/name).read_text(encoding='utf-8-sig').splitlines():
        if not raw or raw.lstrip().startswith('#') or '=' not in raw:continue
        key,val=raw.split('=',1)
        result[key.strip()]=val.split('##',1)[0].strip()
    return result


def texture_paths(value):
    if isinstance(value,str):
        if value.startswith('textures/'):yield value
    elif isinstance(value,list):
        for child in value:yield from texture_paths(child)
    elif isinstance(value,dict):
        for k,child in value.items():
            if k=='path' and isinstance(child,str):yield child
            elif k not in ('tint_color','weight','overlay_color','color'):yield from texture_paths(child)


def texture_keys(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for child in value.values():yield from texture_keys(child)
    elif isinstance(value,list):
        for child in value:yield from texture_keys(child)


def clean(s):
    return s.replace('|','\\|').replace('\n',' ').replace('\r',' ').strip()


def plant_name(n):
    # Classification only affects navigation, never which IDs are included.
    # Keep crafted wood components out of the plant section.
    crafted=('_planks','_stairs','_slab','_fence','_button','_pressure_plate',
             '_door','_trapdoor','_sign','_shelf','_log','_wood')
    if any(part in n for part in crafted):return False
    words=('leaves','leaf','sapling','propagule','flower','azalea','bush','grass',
           'fern','vine','mushroom','fungus','roots','root','moss','cactus',
           'bamboo','sugar_cane','reeds','kelp','seagrass','seagrass','coral',
           'carrot','potato','beetroot','wheat','melon_stem','pumpkin_stem',
           'nether_wart','crop','tallgrass','lily','dripleaf','spore_blossom',
           'petals','wildflowers','sunflower','rose_bush','peony','poppy',
           'dandelion','allium','orchid','tulip','oxeye','cornflower','torchflower',
           'pitcher_plant','sweet_berry','cave_vines','sea_pickle','chorus_plant',
           'mangrove_roots','cocoa','crop','resin_clump','hanging_roots')
    return any(word in n for word in words)


def main():
    block_data=load_json('mojang-blocks.json')['data_items']
    item_data=load_json('mojang-items.json')['data_items']
    entity_data=load_json('mojang-entities.json')['data_items']
    vanilla_blocks=load_json('vanilla-blocks.json')
    vanilla_atlas=load_json('vanilla-terrain.json')['texture_data']
    names=load_json('prismarine-names.json')
    ru,en=lang('ru_RU.lang'),lang('en_US.lang')
    overrides=json.loads(OVERRIDES.read_text(encoding='utf-8'))
    english_to_ru=defaultdict(set)
    for key,text in en.items():
        if key.startswith(('tile.','item.')) and key.endswith('.name') and key in ru:
            english_to_ru[text.casefold()].add(ru[key])
    used_locale=set()
    blocks_by_id={b['name'].split(':',1)[-1]:b for b in block_data}

    def label(row,kind):
        ident=row['name'].split(':',1)[-1]
        serial=row.get('serialization_id','')
        keys=[serial+'.name',serial] if serial else []
        if kind=='items':
            b=blocks_by_id.get(ident)
            if b: keys += [b['serialization_id']+'.name',b['serialization_id']]
        keys += [f'tile.{ident}.name',f'item.{ident}.name',f'item.{ident}',f'entity.{ident}.name']
        for k in keys:
            val=ru.get(k,'')
            if val and not ('%' in val or '\u00a7' in val):
                used_locale.add(k)
                return val
        english=names.get(kind,{}).get(ident,'')
        opts=english_to_ru.get(english.casefold(),set())
        if len(opts)==1:return next(iter(opts))
        if english:return english+' (англ.)'
        return ident.replace('_',' ')+' (ID, перевод не найден)'

    with zipfile.ZipFile(PACK) as z:
        pack_names=set(z.namelist())
        manifest=json.loads(z.read('manifest.json'))
        pack_blocks=json.loads(z.read('blocks.json'))
        atlas=json.loads(z.read('textures/terrain_texture.json'))['texture_data']
        texture_files={str(Path(n).with_suffix('')).replace('\\','/') for n in pack_names if n.endswith(('.png','.tga'))}
        item_texture_files={n for n in texture_files if n.startswith('textures/items/')}

    def atlas_evidence(key):
        # A pack atlas override takes precedence; otherwise vanilla's atlas can
        # point at a filename the pack replaces directly (e.g. crops/stairs).
        local=key in atlas
        entry=atlas.get(key,vanilla_atlas.get(key))
        if entry is None:return ('unknown',[])
        paths=list(dict.fromkeys(texture_paths(entry.get('textures',entry)))) if isinstance(entry,dict) else list(dict.fromkeys(texture_paths(entry)))
        if not paths:return ('unknown',[])
        matches=[p for p in paths if p in texture_files]
        if not matches:return ('no',[])
        if len(matches)<len(paths):return ('partial',matches)
        # Indexed vanilla arrays can represent several materials or states:
        # exact state mapping is not inferred from the atlas alone.
        if not local and isinstance(entry,dict) and isinstance(entry.get('textures'),list) and len(entry['textures'])>1:
            return ('partial',matches)
        return ('yes',matches)

    def block_status(row):
        ident=row['name'].split(':',1)[-1]
        # Common modern identifier with a legacy resource definition.
        aliases={'grass_block':'grass'}
        definition=pack_blocks.get(ident,vanilla_blocks.get(ident))
        if definition is None and ident in aliases:definition=pack_blocks.get(aliases[ident],vanilla_blocks.get(aliases[ident]))
        if not isinstance(definition,dict) or 'textures' not in definition:
            # Some entities, Education blocks and internal states lack entries.
            return 'review','нет однозначной записи в ванильном blocks.json'
        keys=list(dict.fromkeys(texture_keys(definition['textures'])))
        if not keys:return 'review','нет однозначных ключей атласа'
        evidence=[atlas_evidence(k) for k in keys]
        hits=sorted({Path(path).name for _,paths in evidence for path in paths})
        states=[state for state,_ in evidence]
        if not hits:
            if 'unknown' in states:return 'review','не удалось сопоставить всю текстуру с атласом'
            return 'missing','нет замены в основном паке'
        status='done' if all(s=='yes' for s in states) else 'partial'
        # Bedrock can render these via block entities instead of just an atlas.
        if any(w in ident for w in ('chest','shulker','bed','sign','banner','decorated_pot')):
            status='partial'
        return status, 'найдено: '+', '.join(hits[:3])+('…' if len(hits)>3 else '')

    def apply_override(kind,ident,status,note):
        explicit=overrides.get(kind,{}).get(ident)
        if explicit:
            status=explicit['status']
            if status not in ICONS:raise ValueError(f'Invalid status for {kind}:{ident}')
            note=explicit.get('note','ручная отметка')
        return status,note

    block_rows=[]; block_statuses={}
    for record in block_data:
        ident=record['name'].split(':',1)[-1]
        status,note=apply_override('blocks',ident,*block_status(record))
        block_statuses[ident]=status
        block_rows.append((label(record,'blocks'),ident,status,note))

    item_rows=[]
    for record in item_data:
        ident=record['name'].split(':',1)[-1]
        # This pack currently carries no textures/items, but detect future ones
        # only if the vanilla item atlas unambiguously names that exact icon.
        item_atlas=load_item_atlas.get(ident)
        icon_paths=set(texture_paths(item_atlas)) if item_atlas else set()
        if icon_paths & item_texture_files:
            status,note='done','найден файл значка в основном паке'
        elif ident in block_statuses and block_statuses[ident] in ('done','partial'):
            status,note='partial','связан с изменённым блоком; значок отдельно не проверен'
        elif block_statuses.get(ident)=='review':
            status,note='review','связан с блоком, для которого требуется ручная проверка'
        else:
            status,note='missing','отдельный значок в основном паке не найден'
        status,note=apply_override('items',ident,status,note)
        item_rows.append((label(record,'items'),ident,status,note))

    entity_rows=[]
    for record in entity_data:
        ident=record['name'].split(':',1)[-1]
        status,note=apply_override('entities',ident,'review','текстуры модели требуют отдельной проверки')
        entity_rows.append((label(record,'entities'),ident,status,note))

    def sort(rows):return sorted(rows,key=lambda r:(r[0].casefold(),r[1]))
    # Localization keys are an additional index, not a verified second registry:
    # variants like potion effects can share one ID or be legacy-only.
    extras=[]
    for key,value in ru.items():
        if key in used_locale or not value or '%' in value or '\u00a7' in value:continue
        if ((key.startswith(('tile.','item.')) and key.endswith('.name')) or
            (key.startswith('potion.') and key.endswith('.name'))):
            extras.append((value,key))
    extras.sort(key=lambda r:(r[0].casefold(),r[1]))
    known={r['name'].split(':',1)[-1] for r in block_data+item_data}
    other_ids={**names.get('blocks',{}),**names.get('items',{})}
    # Additional older, educational, technical or version-ambiguous aliases:
    # preserve them separately, never count them as confirmed current IDs.
    aliases=sort([(name+' (англ.)' if name else ident,ident,'review',
                   'дополнительный ID стороннего источника, версия не подтверждена')
                  for ident,name in other_ids.items() if ident not in known])

    def counts(rows):
        c=Counter(r[2] for r in rows)
        return ' · '.join(f'{ICONS[s]} {c[s]}' for s in ICONS)
    def render(rows):
        return [f'- {ICONS[status]} **{clean(name)}** — `{ident}` · {clean(note)}' for name,ident,status,note in sort(rows)]

    plants=[r for r in block_rows if plant_name(r[1])]
    chemicals=[r for r in block_rows if r[1].startswith('element_')]
    ordinary=[r for r in block_rows if not plant_name(r[1]) and not r[1].startswith('element_')]
    version='.'.join(map(str,manifest['header']['version']))
    sha=hashlib.sha256(PACK.read_bytes()).hexdigest()
    lines=[
        '# Каталог Minecraft Bedrock — что уже заменено',
        '',
        '> **Для поиска нажми Ctrl+F** (на телефоне — «Найти на странице») и введи название или ID. Растения вынесены отдельно.',
        '',
        f'Проверяем **только основной ресурс-пак `minecraft/realistic-dirt.mcpack` v{version}**. SHA-256: `{sha}`. Дополнительная вода, звуки, VV и автоматическая трава в отметки не включены.',
        '',
        '## Как читать отметки',
        '',
        '- ✅ — в основном паке найдена замена для всех однозначно сопоставленных текстур блока. Это проверка файлов, **не проверка в игре**.',
        '- 🟨 — изменена только часть, сопоставление неоднозначно или предмет связан с изменённым блоком; результат нужно проверить вручную.',
        '- ❌ — замена в основном паке автоматически не обнаружена. Это рабочая отметка, не гарантия, что движок никогда не переиспользует другую текстуру.',
        '- ❔ — определить по ресурсам надёжно не получилось / требуется ручная проверка; сюда же вынесены варианты имён и сущности.',
        '',
        'В списке предметов оценивается **значок предмета**, а не только поставленный блок. Поэтому предмет-блок может иметь 🟨 при ✅ у самого блока: его 3D-значок и отдельные 2D-текстуры нужно проверять отдельно. Одно и то же имя может встречаться в обоих разделах — это разные формы.',
        '',
        '## Версия и пределы полноты',
        '',
        'Пользовательская версия: **Bedrock 1.26.32.2**. Точного тега Mojang `1.26.32.2` в опубликованных bedrock-samples нет; основа — ближайшая доступная стабильная ветка **v1.26.30.5**. Поэтому это полный перечень ID именно опубликованного реестра 1.26.30.5, а не доказательство полного совпадения с установленной сборкой. Экспериментальные, Education и технические ID тоже включены; некоторые недоступны в обычном выживании.',
        '',
        'Один ID может иметь много состояний/компонентов (цвета, зелья, узоры, NBT, ориентация, возраст, варианты спавна). Все сочетания отдельно не перечислены: в конце есть дополнительный индекс локализованных вариантов, но он тоже не гарантирует исчерпывающий перечень комбинаций. Названия без надёжной русской строки оставлены на английском или как ID.',
        '',
        f'Блоков: **{len(block_rows)}** ({counts(block_rows)}). Предметов: **{len(item_rows)}** ({counts(item_rows)}). Сущностей дополнительно: **{len(entity_rows)}** ({counts(entity_rows)}).',
        '',
        '## Навигация',
        '',
        '- [Растения и растительные блоки](#растения-и-растительные-блоки)',
        '- [Блоки и прочие блоковые ID](#блоки-и-прочие-блоковые-id)',
        '- [Химические элементы Education](#химические-элементы-education)',
        '- [Предметы](#предметы)',
        '- [Сущности дополнительно](#сущности-дополнительно)',
        '- [Дополнительные названия вариантов](#дополнительные-названия-вариантов)',
        '- [Возможные старые и технические ID](#возможные-старые-и-технические-id)',
        '- [Источники и обновление](#источники-и-обновление)',
        '',
        '## Растения и растительные блоки',
        '',
        'Разделение сделано по названиям ID для удобства; остальные растительные объекты могут находиться в общем списке.',
        '',*render(plants),'',
        '## Блоки и прочие блоковые ID','',*render(ordinary),'',
        '## Химические элементы Education','',*render(chemicals),'',
        '## Предметы','',*render(item_rows),'',
        '## Сущности дополнительно','',
        'Мобы и технические сущности добавлены дополнительно; их модели и скины не проверялись автоматически.',
        '',*render(entity_rows),'',
        '## Дополнительные названия вариантов','',
        'Это строки локализации без отдельного подтверждённого ID в списке выше, включая некоторые старые названия и варианты зелий/баннеров. ❔ здесь не означает, что вариант присутствует или заменён. Указан ключ перевода, не команда.',
        '',*[f'- ❔ **{clean(value)}** — `{key}`' for value,key in extras],'',
        '## Возможные старые и технические ID','',
        'Дополнительные имена из PrismarineJS, отсутствующие в основных реестрах Mojang выше. Они могут быть устаревшими, экспериментальными или относиться к другой сборке; доступность и отметки не подтверждены.',
        '',*render(aliases),'',
        '## Источники и обновление','',
        '- Реестры блоков, предметов, сущностей, русская и английская локализации, `blocks.json` и атласы: [Mojang bedrock-samples v1.26.30.5](https://github.com/Mojang/bedrock-samples/tree/v1.26.30.5), commit `921fafb05c93abeae56c2f2868cd8f942bdbcc0f`.',
        '- Резервные английские имена ID: [PrismarineJS minecraft-data / Bedrock 1.26.30](https://github.com/PrismarineJS/minecraft-data/tree/b43925ca90babfd63745de4bbcd84feb35c1b40c/data/bedrock/1.26.30), commit `b43925ca90babfd63745de4bbcd84feb35c1b40c`. Реестры ID берутся только из Mojang.',
        '- Копии исходных данных — `minecraft/catalog-source/bedrock-1.26.30.5/`; генератор — `minecraft/tools/build_texture_catalog.py`. После обновления основного пака запусти генератор и тест. Если появится достоверный реестр именно 1.26.32.2, обнови источники и перепроверь отличия.',
        '- Ручные исправления записывай в `minecraft/catalog-source/status-overrides.json`, а не только в этот файл: генератор иначе перезапишет изменения. Ручные отметки имеют приоритет; укажи причину и повторно собери каталог.',
        '- Автоматическая проверка не понимает все UV, состояния, процедурные модели и переиспользование текстур. ❔/🟨 требуют ревизии и проверки в игре; ✅ не гарантирует качества, совместимости или отсутствия швов.',
        ''
    ]
    OUTPUT.write_text('\n'.join(lines),encoding='utf-8')
    print(f'Wrote {OUTPUT.name}: {len(block_rows)} blocks, {len(item_rows)} items, {len(entity_rows)} entities, {len(extras)} localized variants.')
    print('Blocks',counts(block_rows));print('Items',counts(item_rows));print('Entities',counts(entity_rows))


load_item_atlas=load_json('vanilla-item-texture.json')['texture_data']
if __name__=='__main__':main()
