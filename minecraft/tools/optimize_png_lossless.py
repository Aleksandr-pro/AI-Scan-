#!/usr/bin/env python3
"""Recompress selected PNG IDAT streams without changing pixels or metadata.

Run after regenerating these source assets and before packaging if needed to
keep distributions under GitHub's 100 MiB limit. Requires Python zopfli.
"""
from pathlib import Path
import struct
import zlib
import zopfli.zlib

ROOT=Path('minecraft/realistic-dirt')
FILES=('textures/blocks/sea_lantern.png', 'textures/entity/chest/double_normal.png',
       'textures/entity/chest/normal.png', 'textures/blocks/farmland_dry.png',
       'textures/blocks/diamond_block.png', 'textures/blocks/sand.png',
       'textures/blocks/cobblestone.png', 'textures/blocks/log_acacia_top.png',
       'textures/blocks/log_birch_top.png', 'textures/blocks/hay_block_top.png')


def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)


def optimize(path):
    source=path.read_bytes()
    if source[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError(f'Not PNG: {path}')
    pos=8; parts=[]; ids=[]
    while pos<len(source):
        length=int.from_bytes(source[pos:pos+4],'big'); kind=source[pos+4:pos+8]
        content=source[pos+8:pos+8+length]; crc=source[pos+8+length:pos+12+length]
        if len(crc)!=4 or int.from_bytes(crc,'big') != zlib.crc32(kind+content)&0xffffffff:
            raise ValueError(f'Bad PNG chunk in {path}')
        parts.append((kind,content));pos+=12+length
        if kind==b'IDAT':ids.append(content)
    raw=zlib.decompress(b''.join(ids))
    compressed=zopfli.zlib.compress(raw,numiterations=8)
    if len(compressed)>=sum(map(len,ids)):
        print(f'{path}: unchanged');return
    result=bytearray(source[:8]);inserted=False
    for kind,content in parts:
        if kind==b'IDAT':
            if not inserted:result.extend(chunk(b'IDAT',compressed));inserted=True
        else:result.extend(chunk(kind,content))
    if zlib.decompress(compressed)!=raw:raise ValueError('Decompression mismatch')
    path.write_bytes(result)
    print(f'{path}: saved {len(source)-len(result)} bytes')


if __name__=='__main__':
    for filename in FILES:optimize(ROOT/filename)
