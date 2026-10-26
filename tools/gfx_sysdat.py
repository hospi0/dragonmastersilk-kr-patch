# -*- coding: utf-8 -*-
r"""SYSTEM.DAT 그림판(폭 256 8bpp, 팔레트 = 화면 CRAM) 의 얼굴 옆 이름표·상태 이상 글자 한글화 (2026-10-26)
  이름표 2벌: 행 66~73(테두리 0x11, 채움 0x12~0x16) · 74~81(테두리 0x29, 채움 0x2A~0x2E), 칸 = 8 px 단위
  상태 이상: 행 82~89 · 90~97, 칸 32 px(낱말마다 테두리 색 다름 — 원본에서 읽음), 채움 0x2A~0x2E
  글꼴 = 갈무리7(한글 7 px) + 8 방향 1 px 테두리 · 줄 색은 원본 줄 그라데이션.
  python tools/gfx_sysdat.py → work/gfx_out/SYSTEM.DAT · work/check/sysdat_preview.png(원본|새것, 실제 색 8배)"""
import collections, os, re, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BDF = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'
SRC = os.path.join(ROOT, 'work', 'saf', 'SYSTEM', 'SYSTEM.DAT')
CRAM = os.path.join(ROOT, 'work', 'mem', 'party', 'CRAM.bin')
W = 256
BDF_BOLD = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
FLOOR_FILL = [0x1C, 0x1A, 0x1A, 0x1A, 0x1A, 0x1B, 0x1C, 0x1D, 0x1C, 0x1B, 0x1A]   # 행 100~110(원본 쇠붙이 띠)

NAME_FILL_A = [0x13, 0x12, 0x12, 0x13, 0x14, 0x15, 0x16]
NAME_FILL_B = [0x2B, 0x2A, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E]
STAT_FILL = [0x2A, 0x2A, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E]
# (x0, 폭, 한글, 가운데?)
NAMES = [(0, 24, '실크', 0), (24, 16, '아카', 0), (40, 16, '아오', 0), (56, 16, '키', 1), (72, 32, '미라맨', 0), (104, 32, '관짝맨', 0)]
STATS = {82: [(0, '독'), (32, '저주'), (64, '침묵'), (96, '혼란')],
         90: [(0, '기절'), (32, '수면'), (64, '석화'), (96, '감전')]}


def load_bdf(path=BDF):
    t = open(path, encoding='utf-8').read(); g = {}
    for m in re.finditer(r'ENCODING (\d+)\n.*?BBX (-?\d+) (-?\d+) (-?\d+) (-?\d+)\nBITMAP\n(.*?)ENDCHAR', t, re.S):
        c, w, h, xo, yo = map(int, m.groups()[:5]); rows = [int(x, 16) for x in m.group(6).split()]
        nb = (w + 7) // 8 * 8
        g[chr(c)] = (w, h, xo, yo, [[(r >> (nb - 1 - i)) & 1 for i in range(w)] for r in rows])
    return g


def word_mask(s, g):
    """7 행 마스크(글자 사이 1 px) → (폭, set((x,y)))"""
    pts = set(); x = 0
    for k, ch in enumerate(s):
        w, h, xo, yo, rows = g[ch]
        for i, r in enumerate(rows):
            y = 6 - (yo + h - 1 - i)
            for j, b in enumerate(r):
                if b: pts.add((x + j, y))
        x += w + 1
    return x - 1, pts


def paint(d, x0, top, width, pts, wpx, fill, outline, center):
    for y in range(top, top + 8):
        for x in range(x0, x0 + width): d[y * W + x] = 0
    ox = x0 + ((width - wpx) // 2 if center else (1 if wpx + 2 <= width else 0))   # 칸이 모자라면 왼쪽 테두리만 잘림
    ring = set()
    for (x, y) in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1): ring.add((x + dx, y + dy))
    for (x, y) in ring - pts:
        X, Y = ox + x, top + y
        if x0 <= X < x0 + width and top <= Y < top + 8: d[Y * W + X] = outline
    for (x, y) in pts:
        X, Y = ox + x, top + y
        assert x0 <= X < x0 + width and top <= Y < top + 8, ('넘침', X, Y)
        d[Y * W + X] = fill[y]


def build():
    d = bytearray(open(SRC, 'rb').read()); g = load_bdf()
    for x0, wd, s, c in NAMES:
        wpx, pts = word_mask(s, g)
        assert wpx <= wd, (s, wpx, wd)
        paint(d, x0, 66, wd, pts, wpx, NAME_FILL_A, 0x11, c)
        paint(d, x0, 74, wd, pts, wpx, NAME_FILL_B, 0x29, c)
    for top, ws in STATS.items():
        for x0, s in ws:
            cnt = collections.Counter(d[y * W + x] for y in range(top, top + 8) for x in range(x0, x0 + 32)
                                      if d[y * W + x] and not 0x2A <= d[y * W + x] <= 0x2F)
            outline = cnt.most_common(1)[0][0]
            wpx, pts = word_mask(s, g)
            paint(d, x0, top, 32, pts, wpx, STAT_FILL, outline, 1)
    # 던전 층수 «地下 n 階» → «지하 n 층»: 행 98~111, 地下 = x0~23 · 階 = x24~35(화면에서 따로 잘라 붙임), 그림자 0x19(오른쪽·아래), 채움 0x1A(흰)~0x1F(어두운 회색)
    gb = load_bdf(BDF_BOLD)
    for x0, wd, s in ((0, 24, '지하'), (24, 12, '층')):
        for y in range(98, 112):
            for x in range(x0, x0 + wd): d[y * W + x] = 0
        for k, ch in enumerate(s):
            w, h, xo, yo, rows = gb[ch]; gx = x0 + 12 * k; top = 110 - (yo + h - 1)
            pts = {(gx + j, top + i) for i, r in enumerate(rows) for j, b in enumerate(r) if b}
            for (x, y) in pts:
                for dx, dy in ((1, 0), (0, 1), (1, 1)):
                    if (x + dx, y + dy) not in pts and x + dx < x0 + wd and y + dy < 112: d[(y + dy) * W + x + dx] = 0x19
            for (x, y) in pts:
                assert x0 <= x < x0 + wd and 98 <= y < 112, ('층수 넘침', ch)
                d[y * W + x] = FLOOR_FILL[y - 100]
    return bytes(d)


def main():
    new = build(); old = open(SRC, 'rb').read()
    out = os.path.join(ROOT, 'work', 'gfx_out'); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'SYSTEM.DAT'), 'wb').write(new)
    diff = [i for i in range(len(old)) if old[i] != new[i]]
    print('바뀐 바이트', len(diff), '행 범위', min(diff) // W, max(diff) // W)
    C = open(CRAM, 'rb').read()
    pal = [(lambda v: ((v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8))(int.from_bytes(C[i * 2:i * 2 + 2], 'big')) for i in range(256)]
    try:                                                     # 화면 렌더(던전 스테이트 NBG1)에서 색 번호 → 실제 색
        rim = Image.open(os.path.join(ROOT, 'work', 'v2_floor_nbg1.png')).convert('RGB')
        V = open(os.path.join(ROOT, 'work', 'mem', 'floor', 'VDP2_VRAM.bin'), 'rb').read()
        for y in range(256):
            for x in range(512):
                b = V[0x60000 + y * 512 + x]
                if b: pal[b] = rim.getpixel((x, y))
    except OSError:
        pass
    def img(d):
        im = Image.new('RGB', (136, 46)); im.putdata([pal[d[y * W + x]] if d[y * W + x] else (0, 0, 80) for y in range(66, 112) for x in range(136)])
        return im.resize((136 * 8, 46 * 8), Image.NEAREST)
    a, b = img(old), img(new)
    pv = Image.new('RGB', (a.width, a.height * 2 + 16), (255, 255, 255)); pv.paste(a, (0, 0)); pv.paste(b, (0, a.height + 16))
    pv.save(os.path.join(ROOT, 'work', 'check', 'sysdat_preview.png'))


if __name__ == '__main__':
    main()
