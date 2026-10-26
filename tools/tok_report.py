# -*- coding: utf-8 -*-
r"""번역 검사 보고(2026-10-26) — data/번역/텍스트_*.tsv 의 원문↔번역
  ① \n 개수만 다름(줄 다시 접음) ② {07}{0B}%s 등 «줄바꿈 말고» 제어 코드 다름 ③ cp932 로 못 쓰는 글자(한글 빼고)
  python tools/tok_report.py → work/check/tok_report.tsv"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TOK = re.compile(r'\\n|\{[0-9A-F]{2}\}|%[-0-9]*[dsx]')
HANGUL = re.compile('[가-힣]')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rep = []; cnt = {'줄바꿈만': 0, '제어코드': 0, '글자': 0}
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역', '텍스트_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) < 5 or not c[4].strip(): continue
            src, dst = c[3], c[4].replace('·', '・')
            a, b = TOK.findall(src), TOK.findall(dst)
            if a != b:
                k = '줄바꿈만' if [x for x in a if x != '\\n'] == [x for x in b if x != '\\n'] else '제어코드'
                cnt[k] += 1; rep.append((k, os.path.basename(p), c[0], c[2], src, dst))
            bad = sorted({ch for ch in re.sub(r'\\n|\{[0-9A-F]{2}\}', '', dst) if not HANGUL.match(ch) and not _ok(ch)})
            if bad:
                cnt['글자'] += 1; rep.append(('글자 ' + ' '.join('%s(U+%04X)' % (x, ord(x)) for x in bad), os.path.basename(p), c[0], c[2], src, dst))
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    q = os.path.join(ROOT, 'work', 'check', 'tok_report.tsv')
    with open(q, 'w', encoding='utf-8-sig', newline='\n') as fo:
        fo.write('문제\t파일\t번호\t최대바이트\t원문\t번역\n')
        for r in rep: fo.write('\t'.join(r) + '\n')
    print(cnt, q)
    for r in rep:
        if not r[0].startswith('줄바꿈'): print(r[0], r[1], r[2], '|', r[4][:50], '||', r[5][:50])


def _ok(ch):
    try:
        ch.encode('cp932'); return True
    except UnicodeEncodeError:
        return False


if __name__ == '__main__':
    main()
