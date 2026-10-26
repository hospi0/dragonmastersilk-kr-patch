import sys, re
sys.path.insert(0, r'C:\claude\project\dragonmastersilk-kr-patch\tools')
import consist
sys.stdout.reconfigure(encoding='utf-8')
R = consist.load(); N = consist.NOSP
BS = chr(92) + 'n'
hd = [r for r in R if r['src'].startswith('（') and ('）' + BS) in r['src'] and int(r['no']) >= 3800]
rec = [r for r in R if r['kind'].startswith('기록') and 3574 <= int(r['no']) < 3832]
print(len(hd), hd[0]['no'], hd[-1]['no'], len(rec), rec[0]['no'], rec[-1]['no'])
for a in rec[:3] + rec[-3:]: print(a['no'], a['src'], a['kind'])
for a in hd[:3] + hd[-3:]: print(a['no'], a['src'][:12])
kata = lambda s: ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in s)
hdn = [(r, r['src'][1:r['src'].index('）')]) for r in hd]
recs = [r for r in rec if r['src'] != '欠番']
ok = sum(kata(h) == kata(a['src']) for a, (r, h) in zip(recs, hdn))
print('kana match', ok)
for a, (r, h) in list(zip(recs, hdn))[:200:20]: print(a['no'], a['src'], r['no'], h)
import difflib
A = [kata(a['src']) for a in recs]; B = [kata(h) for _, h in hdn]
sim = lambda x, y: difflib.SequenceMatcher(None, x, y).ratio()
n, m = len(A), len(B)
D = [[0.0] * (m + 1) for _ in range(n + 1)]; P = [[None] * (m + 1) for _ in range(n + 1)]
for i in range(n + 1):
    for j in range(m + 1):
        if i == 0 and j == 0: continue
        c = []
        if i and j: c.append((D[i-1][j-1] + sim(A[i-1], B[j-1]) + 0.05, "d"))
        if i: c.append((D[i-1][j], 'u'))
        if j: c.append((D[i][j-1], 'l'))
        D[i][j], P[i][j] = max(c)
i, j = n, m; pairs = []
while i or j:
    p = P[i][j]
    if p == 'd': pairs.append((recs[i-1], hdn[j-1])); i -= 1; j -= 1
    elif p == 'u': i -= 1
    else: j -= 1
pairs.reverse()
print('pairs', len(pairs))
bad = 0
for a, (r, h) in pairs:
    k1 = N(a['dst']); k2 = N(r['dst'][1:r['dst'].index('）')])
    if k1 != k2:
        bad += 1; print('%s\t%s\t%s\t%s\t%s\t%.2f' % (a['no'], a['src'], a['dst'], r['no'], r['dst'][1:r['dst'].index('）')], sim(kata(a['src']), kata(h))))
print('bad', bad)
