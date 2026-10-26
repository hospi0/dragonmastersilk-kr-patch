# -*- coding: utf-8 -*-
r"""SEB 그림 펼치기(2026-10-26, 판독 중) — 앞 팔레트(RGB555 BE, 16색 = 32 B 또는 256색 = 512 B) + 화소(4/8비트).
  python tools/seb.py <파일> <폭> <팔레트 색 수> [화소 비트] → work/check/<이름>.png(2배)"""
import os, struct, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rgb(v):
    return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31)


def render(d, w, ncol, bits=8):
    pal = [rgb(struct.unpack_from('>H', d, 2 * i)[0]) for i in range(ncol)]
    px = d[2 * ncol:]
    n = len(px) * 8 // bits; h = n // w
    im = Image.new('RGB', (w, h))
    for i in range(w * h):
        v = px[i] if bits == 8 else (px[i // 2] >> (4 if i % 2 == 0 else 0)) & 15
        im.putpixel((i % w, i // w), pal[v % ncol])
    return im


if __name__ == '__main__':
    p, w, nc = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); bits = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    im = render(open(p, 'rb').read(), w, nc, bits)
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    q = os.path.join(ROOT, 'work', 'check', os.path.basename(p) + '.png'); im.resize((im.width * 2, im.height * 2)).save(q); print(q, im.size)
