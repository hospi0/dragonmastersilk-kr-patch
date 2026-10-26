# -*- coding: utf-8 -*-
r"""넣은 결과 검산(2026-10-26) — 원본의 «참조 자리»를 새 파일에서 따라가 기대 바이트(insert.Enc 로 인코딩한 번역)와 같은지.
  포인터 파일(본체·PRG): 원본 포인터 자리(4정렬)마다 새 값이 가리키는 NUL 까지 · 기록: 같은 오프셋 · SCR: 차례 · HLP: 표 번호 · 적 이름: 같은 오프셋.
  + SAF 머리 표 = 실제 자리·크기 · 코드 영역(포인터 자리·문자열 덩어리 밖) 바이트 그대로.
  python tools/verify.py [--test]"""
import collections, glob, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import extract, insert, saf


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    test = '--test' in sys.argv
    B = os.path.join(ROOT, 'work', 'build_test' if test else 'build')
    rows = extract.all_rows()
    tr = insert.final_tr(test, rows)
    enc = insert.Enc([tr.get(r['text'], r['text']) for r in rows if r['kind'] != '꼬리'])
    want = lambda t: enc.enc(tr.get(t, t))
    new = {}
    for f in ('EVENT', 'OVERLAY', 'SYSTEM', 'ENEMY'):
        d = open(os.path.join(B, f + '.SAF'), 'rb').read()
        for nm, o, s in saf.entries(d):
            assert o + s <= len(d), (f, nm)
            new[f + '/' + nm] = d[o:o + s]
    new['0'] = open(os.path.join(B, '0'), 'rb').read()
    old = lambda rel: open(os.path.join(ROOT, 'work', 'disc0', '0') if rel == '0' else os.path.join(extract.SAF, rel), 'rb').read()
    ok = 0; bad = collections.Counter()

    def cmp(tag, got, exp):
        nonlocal ok
        if got == exp: ok += 1
        else:
            bad[tag] += 1
            if bad[tag] <= 3: print('✗', tag, got[:24], exp[:24])

    byfile = collections.defaultdict(list)
    for r in rows: byfile[r['file']].append(r)
    for rel, rs in byfile.items():
        o_d = old(rel); n_d = new[rel]
        if rel.endswith('.SCR'):
            seq = [r for r in rs]; i = 0; k = 0
            while i < len(n_d):
                if n_d[i] == 0xFF:
                    i += 6 if n_d[i + 1] in (1, 5) else 2; continue
                e = n_d.find(b'\0', i); cmp('자막', n_d[i:e], want(seq[k]['text'])); k += 1; i = e + 1
            if k != len(seq): bad['자막 수'] += 1
        elif rel.endswith('.HLP'):
            te = extract.hlp_table(n_d)
            for r, (no, off) in zip(rs, te):
                cmp('설명', n_d[off:n_d.find(b'\0', off)], want(r['text']))
        elif rel.startswith('ENEMY/'):
            for r in rs:
                o = int(r['at'], 16); cmp('적', n_d[o:n_d.find(b'\0', o)], want(r['text']))
        else:
            base = extract.MAIN_BASE if rel == '0' else extract.PRG_BASE.get(rel.split('/')[1], 0x06090000)
            for r in rs:
                o = int(r['at'], 16)
                if r['kind'] == '기록':
                    cmp('기록', n_d[o:n_d.find(b'\0', o)], want(r['text'])); continue
                if r['kind'] == '꼬리': continue
                for k in range(0, len(o_d) - 3, 4):
                    if struct.unpack_from('>I', o_d, k)[0] == base + o:
                        v = struct.unpack_from('>I', n_d, k)[0] - base
                        if not 0 <= v < len(n_d):                  # 오버레이 글을 본체 남는 빈칸에 둔 것(insert.MAIN)
                            m0 = new['0']; v = struct.unpack_from('>I', n_d, k)[0] - extract.MAIN_BASE
                            cmp('문자', m0[v:m0.find(b'\0', v)], want(r['text'])); continue
                        cmp('문자', n_d[v:n_d.find(b'\0', v)], want(r['text']))
    print('맞음 %d · 틀림 %s' % (ok, dict(bad)))
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
