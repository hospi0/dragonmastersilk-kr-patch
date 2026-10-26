# -*- coding: utf-8 -*-
r"""자막·대사 줄 폭 검사(2026-10-26 실기: OP_A «나타나, 이 세계를 멸망시키려 했다」» 넘침 → 첫 줄이 밀려 사라짐)
  폭 단위 = 반각 1 · 전각/한글/새 칸(쉼표·작은따옴표) 2 · 짝 «!!»·«!?» 2. 파일 종류별 원문 최대 폭 = 한계.
  python tools/linewidth.py → work/check/linewidth.tsv(넘치는 줄)"""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import extract, insert

SPLIT = re.compile(r'\\n|\{07\}|\{0B\}')
FMT = re.compile(r'%[-0-9]*[dsxu]|\{[0-9A-F]{2}\}')


def units(line):
    line = insert.ank(FMT.sub('', line)); u = 0; i = 0
    while i < len(line):
        if line[i:i + 2] in ('!!', '!?'): u += 2; i += 2; continue
        ch = line[i]; i += 1
        u += 1 if ord(ch) < 0x80 and ch not in insert.CUSTOM else 2
    return u


def kind(r):
    f = r['file']
    return f if f.endswith('.SCR') else ('HLP' if f.endswith('.HLP') else f.split('/')[-1])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = extract.all_rows(); tr = insert.final_tr(False, rows)
    cap = collections.defaultdict(int)
    for r in rows:
        if r['kind'] in ('문자', '자막', '설명') or r['file'].endswith(('.SCR', '.HLP')):
            for ln in SPLIT.split(r['text']): cap[kind(r)] = max(cap[kind(r)], units(ln))
    for k in list(cap):
        if k.endswith('.SCR'): cap[k] = 36          # 이벤트 자막 창 = 18칸(원문 줄 거의 전부 ≤ 36, 실기 OP_A 38 은 넘쳐 첫 줄이 밀림)
    out = []; seen = set()
    for r in rows:
        k = kind(r)
        if k not in cap or r['text'] not in tr or (k, r['text']) in seen: continue
        seen.add((k, r['text']))
        for ln in SPLIT.split(tr[r['text']]):
            u = units(ln)
            if u > cap[k]: out.append((k, cap[k], u, r['text'], tr[r['text']], ln))
    with open(os.path.join(ROOT, 'work', 'check', 'linewidth.tsv'), 'w', encoding='utf-8-sig') as f:
        f.write('종류\t한계\t폭\t원문\t번역\t넘친 줄\n')
        for x in out: f.write('\t'.join(str(v) for v in x) + '\n')
    print('한계', dict(cap)); print('넘침', collections.Counter(x[0] for x in out))


if __name__ == '__main__':
    main()
