#!/usr/bin/env python3
"""Build the isolated Bedrock sound overlay from checked-in CC0 source clips.
Requires numpy, scipy, pillow, soundfile (with libvorbis), and ffmpeg on PATH or imageio-ffmpeg.
"""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sound-reference/source'
PACK = ROOT / 'realistic-sounds'
RATE = 22050
BASE = 'sounds/realistic_audio/'


def ffmpeg():
    binary = shutil.which('ffmpeg')
    if binary:
        return binary
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def decode(path):
    data = subprocess.run([ffmpeg(), '-v', 'error', '-i', str(path), '-f', 'f32le',
                           '-ac', '1', '-ar', str(RATE), '-'], check=True, capture_output=True).stdout
    return np.frombuffer(data, dtype='<f4').astype(np.float64)


def shape(audio, rms, hp=65, fade_in=0.008, fade_out=0.040):
    """Remove infrasonic rumble, balance RMS with headroom, and de-click edges."""
    audio = sosfiltfilt(butter(2, hp, btype='highpass', fs=RATE, output='sos'), audio)
    a, b = int(fade_in * RATE), int(fade_out * RATE)
    assert len(audio) > a + b
    audio[:a] *= np.linspace(0, 1, a)
    audio[-b:] *= np.linspace(1, 0, b)
    current = np.sqrt(np.mean(audio ** 2))
    if current < 1e-6:
        raise ValueError('silent source')
    audio *= min(rms / current, 0.78 / max(np.max(np.abs(audio)), 1e-6))
    return audio


def main():
    metadata = json.loads((ROOT / 'sound-reference/source-manifest.json').read_text())['files']
    for name, meta in metadata.items():
        if hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() != meta['sha256']:
            raise ValueError(f'Source checksum mismatch: {name}')
    shutil.rmtree(PACK, ignore_errors=True)
    (PACK / 'sounds').mkdir(parents=True)
    manifest = {'format_version': 2,
                'header': {'name': 'Живой мир — реалистичные звуки',
                           'description': 'Шаги, дождь, гром, пещеры и костёр',
                           'uuid': '97d0a519-1d35-431b-859d-1c82bdc81ce3',
                           'version': [1, 0, 0], 'min_engine_version': [1, 21, 0]},
                'modules': [{'type': 'resources', 'uuid': '06751380-5460-41dc-9157-4523efebe142',
                             'version': [1, 0, 0]}]}
    (PACK / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    vanilla = json.loads((ROOT / 'sound-reference/vanilla-sound-definitions.json').read_text())
    defs = copy.deepcopy(vanilla['sound_definitions'])
    demo = []

    def save(name, audio):
        path = PACK / (BASE + name + '.ogg')
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, audio, RATE, format='OGG', subtype='VORBIS')
        return BASE + name

    def source(prefix):
        matches = list(SOURCE.glob(prefix + '.*.mp3'))
        if len(matches) != 1:
            raise ValueError(f'Expected one {prefix}, got {matches}')
        return decode(matches[0])

    for material, count in [('grass', 6), ('gravel', 6), ('stone', 6), ('wood', 6),
                            ('sand', 6), ('snow', 4), ('mud', 6)]:
        entries = []
        for index in range(1, count + 1):
            audio = shape(source(f'step-{material}-{index}'), 0.085, hp=85)
            name = save(f'steps/{material}{index}', audio)
            entries.append({'name': name, 'load_on_low_memory': index == 1})
            if index <= 3:
                demo.extend([audio, np.zeros(int(RATE * 0.15))])
        key = 'block.mud.step' if material == 'mud' else 'step.' + material
        defs[key]['sounds'] = entries
        demo.append(np.zeros(int(RATE * 0.7)))

    # Short, independent rain grains, like vanilla's short weather samples; no assumption
    # that Bedrock loops a long track. The weather engine determines when to play them.
    rain = source('rain-loop-1')
    rain_entries = []
    for i, start in enumerate([2, 9, 17, 25], 1):
        audio = shape(rain[int(start * RATE):int((start + 1.48) * RATE)], 0.16, hp=120, fade_out=0.015)
        rain_entries.append({'name': save(f'weather/rain{i}', audio), 'volume': 0.02,
                             'load_on_low_memory': i == 1})
    defs['ambient.weather.rain']['sounds'] = rain_entries
    demo.extend([np.zeros(RATE), audio * 0.7, np.zeros(RATE // 2)])

    thunder_entries = []
    for i in range(1, 4):
        audio = shape(source(f'thunder-{i}'), 0.09, hp=55, fade_in=0.020, fade_out=0.120)
        thunder_entries.append({'name': save(f'weather/thunder{i}', audio), 'load_on_low_memory': i == 1})
        if i == 3:
            demo.extend([audio * 0.55, np.zeros(RATE // 2)])
    defs['ambient.weather.thunder']['sounds'] = thunder_entries

    # Campfire event fires as a one-shot with randomized pitch/volume, not a bed.
    fire = source('campfire-loop-1')
    fire_entries = []
    for i, start in enumerate([2, 6, 10, 15, 20, 25], 1):
        audio = shape(fire[int(start * RATE):int((start + 1.2) * RATE)], 0.075, hp=100, fade_out=0.080)
        fire_entries.append({'name': save(f'fire/crackle{i}', audio), 'load_on_low_memory': i == 1})
    defs['block.campfire.crackle']['sounds'] = fire_entries
    demo.extend([audio, np.zeros(RATE // 2)])

    # Keep all vanilla cave moods, and add four real drippy one-shots alongside them.
    cave = source('cave-drips-1')
    for i, start in enumerate([2, 9, 16, 23], 1):
        audio = shape(cave[int(start * RATE):int((start + 5) * RATE)], 0.08, hp=90, fade_in=0.060, fade_out=0.350)
        defs['ambient.cave']['sounds'].append({'name': save(f'cave/drips{i}', audio), 'weight': 3})
    demo.append(audio * 0.8)

    (PACK / 'sounds/sound_definitions.json').write_text(json.dumps(
        {'format_version': vanilla['format_version'], 'sound_definitions': defs}, indent=2) + '\n')
    # A distinct pack icon helps the audio overlay stand out in Bedrock's pack list.
    icon = Image.new('RGB', (256, 256), '#142c2b')
    draw = ImageDraw.Draw(icon)
    draw.polygon([(0, 172), (65, 94), (112, 150), (160, 77), (256, 168), (256, 256), (0, 256)], fill='#36584a')
    draw.polygon([(0, 200), (65, 149), (114, 191), (170, 136), (256, 196), (256, 256), (0, 256)], fill='#213f37')
    draw.rounded_rectangle((24, 176, 232, 226), radius=24, fill='#0d2927')
    heights = [7, 12, 8, 17, 11, 20, 13, 23, 15, 10, 18, 11, 16, 7, 12, 8]
    for i, height in enumerate(heights):
        x = 42 + i * 11
        draw.line((x, 201-height, x, 201+height), fill='#b4d6a8', width=4)
    icon.save(PACK / 'pack_icon.png')
    output = ROOT / 'realistic-sounds.mcpack'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(PACK).as_posix())
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / 'demo.wav'
        sf.write(wav, np.concatenate(demo), RATE)
        subprocess.run([ffmpeg(), '-v', 'error', '-y', '-i', str(wav), '-codec:a', 'libmp3lame',
                        '-b:a', '96k', str(ROOT / 'realistic-sounds-demo.mp3')], check=True)
    print(f'Built {output}, {len(list(PACK.rglob("*.ogg")))} OGGs')


if __name__ == '__main__':
    main()
