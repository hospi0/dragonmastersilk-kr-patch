# -*- coding: utf-8 -*-
r"""번역의 작은따옴표 '…' 를 원문 괄호(『』·「」·“”)로 되돌림(2026-10-26 하스피 «원문으로 되돌려줘»)
  번역 파일에서 원문 안쪽 인용을 ' 로 바꿔 둔 곳(73문장) — 원문 괄호 쌍을 순서대로 맞춤(화자 「 도 순서에 포함).
  restore(src, dst) → (새 번역, 문제 문자열 또는 None) · python tools/quotes.py [--write] → data/번역 고침"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PAIR = {'『': '』', '「': '」', '“': '”'}
OPEN = re.compile('[『「“]')


def restore(src, dst):
    if "'" not in dst and '"' not in dst: return dst, None
    want = OPEN.findall(src)                              # 원문 여는 괄호 차례
    out = []; k = 0; stack = []; i = 0
    while i < len(dst):
        ch = dst[i]
        if ch in PAIR:
            if k < len(want) and want[k] == ch: k += 1
            elif ch in want[k:]: k = want.index(ch, k) + 1
            out.append(ch)
        elif ch in "'\"":                                  # 작은·큰따옴표(반각) 둘 다
            if stack:                                     # 닫는 쪽
                out.append(PAIR[stack.pop()])
            else:
                if k >= len(want): return dst, '원문 괄호 모자람'
                o = want[k]; k += 1; stack.append(o); out.append(o)
        else:
            out.append(ch)
        i += 1
    if stack: return dst, '짝 안 맞음'
    return ''.join(out), None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv; n = 0; bad = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '번역', '*.tsv'))):
        lines = open(f, encoding='utf-8').read().split('\n'); ch = False
        for j, l in enumerate(lines):
            p = l.split('\t')
            if len(p) < 5 or ("'" not in p[4] and '"' not in p[4]): continue
            new, err = restore(p[3], p[4])
            if err: bad.append((os.path.basename(f), p[0], err, p[3], p[4])); continue
            print(p[0], p[4], '→', new); p[4] = new; lines[j] = '\t'.join(p); n += 1; ch = True
        if ch and write: open(f, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('바꿈', n, '· 문제', len(bad))
    for b in bad: print('  ⚠', *b)


if __name__ == '__main__':
    main()
