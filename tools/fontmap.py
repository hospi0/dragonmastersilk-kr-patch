# -*- coding: utf-8 -*-
r"""글꼴 판독(2026-10-26) — SYSTEM/KANJI.FNT = 16×12 1비트(24 B, 행마다 u16 BE) × 2,000칸.
  본체 /0(램 0x06010000)의 글자 → 칸 번호(0x0601D578 와 같은 셈):
    기호 JIS 0x2121~(0x2121+0xC02 안) = 표 0x0606D374 (JIS u16, 번호 u16) 41쌍 · 히라가나 0x2421~0x2473 = JIS − 0x23F9
    · 가타카나 0x2521~0x2576 = JIS − 0x2481 · 0x2000+0~6 = 표 0x0606D41A · 한자 = 표 0x0606D434 (JIS, 번호) 1,128쌍.
  jis(sjis) · glyph_of(sjis) → 칸 번호 · kanji_table() → [(JIS, 번호)] · python tools/fontmap.py → 요약"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x06010000
SYM_T, SYM_N = 0x0606D374, 41
KAN_T, KAN_N = 0x0606D434, 0x468
FNT = os.path.join(ROOT, 'work', 'saf', 'SYSTEM', 'KANJI.FNT')


def main_bin():
    return open(os.path.join(ROOT, 'work', 'disc0', '0'), 'rb').read()


def jis(sj):
    """0x06014F3C 와 같은 SJIS → JIS"""
    hi, lo = sj >> 8, sj & 0xFF
    hi = (hi - 0x70 if hi <= 0x9F else hi - 0xB0) * 2
    if lo > 0x9E:
        lo -= 0x7E
    else:
        hi -= 1; lo -= 0x1F
        if lo > 0x60: lo -= 1
    return hi << 8 | lo


def sjis(j):
    hi, lo = j >> 8, j & 0xFF
    s1 = (hi + 1) // 2 + (0x70 if hi <= 0x5E else 0xB0)
    if hi & 1:
        s2 = lo + 0x1F + (1 if lo >= 0x60 else 0)
    else:
        s2 = lo + 0x7E
    return s1 << 8 | s2


def sym_table(b=None):
    b = b or main_bin()
    return [struct.unpack_from('>HH', b, SYM_T - BASE + 4 * i) for i in range(SYM_N)]


def kanji_table(b=None):
    b = b or main_bin()
    return [struct.unpack_from('>HH', b, KAN_T - BASE + 4 * i) for i in range(KAN_N)]


def glyph_of(sj, b=None):
    j = jis(sj)
    if 0 <= j - 0x2121 <= 0xC02:
        for jj, n in sym_table(b):
            if jj == j: return n
    if 0x2421 <= j <= 0x2473: return j - 0x23F9
    if 0x2521 <= j <= 0x2576: return j - 0x2481
    for jj, n in kanji_table(b):
        if jj == j: return n
    return None


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = main_bin(); f = open(FNT, 'rb').read()
    assert all(jis(sjis(j)) == j for j in range(0x2121, 0x7427) if 0x21 <= (j & 0xFF) <= 0x7E)
    kt = kanji_table(b)
    print('한자 표', len(kt), '번호', min(n for _, n in kt), '~', max(n for _, n in kt), '겹침', len(kt) - len({n for _, n in kt}))
    print('히라가나 칸', 0x2421 - 0x23F9, '~', 0x2473 - 0x23F9, '· 가타카나 칸', 0x2521 - 0x2481, '~', 0x2576 - 0x2481)
    used = set(n for _, n in kt) | {n for _, n in sym_table(b)} | set(range(40, 123)) | set(range(160, 246))
    print('글꼴 2,000칸 중 어느 표에도 안 걸린 칸', 2000 - len(used & set(range(2000))))
    cols = [0] * 16; rows = [0] * 12
    for i in range(2000):
        for y in range(12):
            v = f[24 * i + 2 * y] << 8 | f[24 * i + 2 * y + 1]
            if v: rows[y] += 1
            for x in range(16):
                if v >> (15 - x) & 1: cols[x] += 1
    print('잉크 열', cols); print('잉크 행', rows)
    for ch in 'あア漢、':
        print(ch, glyph_of(int.from_bytes(ch.encode('cp932'), 'big'), b))
