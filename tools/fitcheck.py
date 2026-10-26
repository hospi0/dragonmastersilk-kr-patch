# -*- coding: utf-8 -*-
r"""대사 넘침 전수 판정(2026-10-26 밤 — 화면마다 짐작해 고치던 것을 한 번에)
  안전 기준: 번역 줄 ≤ «그 문자열 원문의 가장 긴 줄 폭»(원문은 그 창에 맞게 접혀 있으니 창 폭 이하) · 이벤트 자막 = 216 px.
  wrap 으로 다시 나눈 뒤에도 ① 기준보다 긴 줄이 남거나 ② 쪽 줄 수가 원문(자막은 3)보다 많으면 = «위험»(줄이 밀려 사라질 수 있음).
  python tools/fitcheck.py → work/check/fitcheck.tsv (위험 목록 전부) · 숫자 요약"""
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import extract, insert, wrap


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = extract.all_rows(); tr = insert.final_tr(False, rows)
    files = collections.defaultdict(set)
    for r in rows: files[r['text']].add(r['file'])
    out = []; n = 0
    for s, t in tr.items():
        fs = files[s]
        if any(f.endswith('.HLP') or f.startswith('ENEMY') for f in fs): continue
        scr = any(f.endswith('.SCR') for f in fs)
        cap = wrap.SCR_W if scr else max(wrap.units(x) for x in wrap.lines_of(s))
        lim = 3 if scr else max(wrap.page_rows(s))
        n += 1
        wide = [x for x in wrap.lines_of(t) if wrap.units(x) > cap + 1e-9]
        rows_n = max(wrap.page_rows(t))
        if wide or rows_n > lim:
            out.append((sorted(fs)[0], '%.1f' % cap, lim, rows_n, '넓음' if wide else '줄 수', s, t))
    with open(os.path.join(ROOT, 'work', 'check', 'fitcheck.tsv'), 'w', encoding='utf-8-sig') as f:
        f.write('파일\t폭 한계\t줄 한계\t번역 줄\t이유\t원문\t번역\n')
        for x in out: f.write('\t'.join(str(v) for v in x) + '\n')
    c = collections.Counter(x[0].split('/')[-1] for x in out)
    print('검사 %d · 위험 %d' % (n, len(out))); print(dict(c.most_common()))


if __name__ == '__main__':
    main()
