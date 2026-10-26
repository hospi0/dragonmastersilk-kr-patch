# -*- coding: utf-8 -*-
r"""추출 누락 대조(2026-10-26) — 일반 SJIS 훑기(textscan)로 보이는 문자열이 work/strings.tsv 에 있는지(제어·공백 빼고 앞 8자로)"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import textscan


def norm(s):
    s = s.replace('\\n', '').replace('\n', '').replace('\u3000', '')
    return re.sub(r'\{[0-9A-F]{2}\}|[\x00-\x20]', '', s)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    got = {}
    for l in open(os.path.join(ROOT, 'work', 'strings.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) > 4: got.setdefault(c[0], []).append(norm(c[4]))
    tot = 0
    rels = ['0'] + ['OVERLAY/' + f for f in sorted(os.listdir(os.path.join(ROOT, 'work', 'saf', 'OVERLAY')))] + ['SYSTEM/ITEM.HLP', 'SYSTEM/MAGIC.HLP']
    for rel in rels:
        p = os.path.join(ROOT, 'work', 'disc0', '0') if rel == '0' else os.path.join(ROOT, 'work', 'saf', rel)
        G = '|'.join(got.get(rel, []))
        miss = []
        for o, t, _ in textscan.strings(open(p, 'rb').read()):
            n = norm(t)
            m = len(n) // 2
            if len(n) >= 6 and n[m - 3:m + 3] not in G: miss.append((o, t))
        tot += len(miss)
        if miss: print(rel, len(miss), [(hex(o), t[:30].replace('\n', '|')) for o, t in miss[:6]])
    print('빠짐 합계', tot)


if __name__ == '__main__':
    main()
