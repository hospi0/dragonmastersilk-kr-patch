# -*- coding: utf-8 -*-
r"""SAF 묶음(2026-10-26) — BE u32 개수 · 항목 20 B {이름 12(공백 채움) · u32 BE 시작(2048 섹터 단위, 묶음 머리 기준) · u32 BE 크기}
  python tools/saf.py list <묶음>   ·   python tools/saf.py dump → work/saf/<묶음>/<이름> (work/disc0/*.SAF 전부)"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def entries(d):
    n = struct.unpack_from('>I', d, 0)[0]
    out = []
    for i in range(n):
        nm, sec, size = struct.unpack_from('>12sII', d, 4 + 20 * i)
        out.append((nm.decode('ascii', 'replace').strip(), sec * 2048, size))
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'list':
        d = open(sys.argv[2], 'rb').read()
        for nm, o, s in entries(d): print('%-14s %9X %8d' % (nm, o, s))
    else:
        tot = 0
        for f in sorted(os.listdir(os.path.join(ROOT, 'work', 'disc0'))):
            if not f.endswith('.SAF'): continue
            d = open(os.path.join(ROOT, 'work', 'disc0', f), 'rb').read()
            od = os.path.join(ROOT, 'work', 'saf', f[:-4]); os.makedirs(od, exist_ok=True)
            for nm, o, s in entries(d):
                assert o + s <= len(d), (f, nm)
                open(os.path.join(od, nm), 'wb').write(d[o:o + s]); tot += 1
        print(tot, '개')
