# -*- coding: utf-8 -*-
r"""Dragon Master Silk 문자열 추출(2026-10-26) → work/strings.tsv(곳마다) + data/번역할것/텍스트_NN.tsv(고유, 20KB 단위)
  글 표기: 0x0A → \n · 다른 제어 바이트 → {07}{0B} 꼴(07 = 키 대기, 0B = 창 지움) — 번역에도 같은 수·차례로.
  ① EVENT/*.SCR(동영상 자막 대본): 차례대로 `ff 01`+u32(시각) · `ff 02`·`ff 03` · 글\0 · 끝 `ff ff` — 포인터 없음(길이 자유). 종류 «자막».
  ② OVERLAY/*.PRG(BATTLE·CMDMENU = 램 0x06080000 · EVENTxxF·SHOP = 0x06090000 · PROFILE = 0x060A0000) · 본체 /0(0x06010000):
     4바이트 정렬 BE 절대 포인터가 가리키는 곳에서 NUL 까지(SJIS·반각·제어 07/0A/0B) — 일본어 1자 이상. 다른 문자열 끝과 같은 NUL 로 끝나면 «꼬리».
  ③ SYSTEM/ITEM.HLP·MAGIC.HLP: 앞 표 (u16 BE 번호, u16 LE 오프셋) → 문자열(\0). 표째 다시 씀(길이 자유). 종류 «설명».
  ④ ENEMY/E*.DAT: 이름 칸(고정 길이 — NUL 뒤 0 이 이어지는 만큼) → 종류 «기록»(최대바이트).
  python tools/extract.py"""
import collections, glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SAF = os.path.join(ROOT, 'work', 'saf')
JP = re.compile(r'[ぁ-んァ-ヶ一-龯ー々]')
PRG_BASE = {'BATTLE.PRG': 0x06080000, 'CMDMENU.PRG': 0x06080000, 'PROFILE.PRG': 0x060A0000}
MAIN_BASE = 0x06010000
OK_CTL = {0x07, 0x0A, 0x0B}


def walk(d, o, ok_ctl=OK_CTL):
    """o 부터 NUL 까지 → (표기 글, NUL 자리) / 아니면 None"""
    out = []; i = o
    while i < len(d):
        c = d[i]
        if c == 0:
            return ''.join(out), i
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            try:
                out.append(d[i:i + 2].decode('cp932')); i += 2; continue
            except UnicodeDecodeError:
                return None
        if c == 0x0A and c in ok_ctl:
            out.append('\\n'); i += 1; continue
        if c in ok_ctl:
            out.append('{%02X}' % c); i += 1; continue
        if 0x20 <= c < 0x7F or 0xA1 <= c <= 0xDF:
            out.append(d[i:i + 1].decode('cp932')); i += 1; continue
        return None
    return None


def enc(t):
    """표기 글 → 바이트(한글 제외 — 넣기 도구가 따로)"""
    out = bytearray()
    for tok in re.split(r'(\\n|\{[0-9A-F]{2}\})', t):
        if tok == '\\n': out.append(0x0A)
        elif re.fullmatch(r'\{[0-9A-F]{2}\}', tok or ''): out.append(int(tok[1:3], 16))
        elif tok: out += tok.encode('cp932')
    return bytes(out)


def scr_rows():
    rows = []
    for p in sorted(glob.glob(os.path.join(SAF, 'EVENT', '*.SCR'))):
        d = open(p, 'rb').read(); i = 0; k = 0
        while i < len(d):
            if d[i] == 0xFF:
                i += 6 if d[i + 1] in (1, 5) else 2          # ff01 = 시각 u32 · ff05 = 인자 4 B(EV43_4 끝) · ff02/ff03/ffff
                continue
            r = walk(d, i, {0x0A})
            assert r, (p, i)
            t, e = r
            rows.append(dict(file='EVENT/' + os.path.basename(p), at='#%d' % k, kind='자막', size=e - i, text=t)); k += 1
            i = e + 1
    return rows


def ptr_rows(rel, d, base, data_from=0):
    ptr = collections.Counter()
    for k in range(0, len(d) - 3, 4):
        v = struct.unpack_from('>I', d, k)[0] - base
        if data_from <= v < len(d): ptr[v] += 1
    cand = []
    for o in sorted(ptr):
        r = walk(d, o)
        if r and JP.search(r[0]) and r[1] > o:
            cand.append((o, r[1], r[0]))
    rows = []; ends = set()
    for o, e, t in cand:
        kind = '꼬리' if e in ends else '문자'
        ends.add(e)
        rows.append(dict(file=rel, at='%X' % o, kind=kind, size=e - o, text=t))
    return rows


def hlp_table(d):
    first = struct.unpack_from('<H', d, 2)[0]; ent = []
    for k in range(0, first, 4):
        no, off = struct.unpack_from('>H', d, k)[0], struct.unpack_from('<H', d, k + 2)[0]
        if off < first or off >= len(d): break
        ent.append((no, off))
    return ent


def hlp_rows():
    rows = []
    for f in ('ITEM.HLP', 'MAGIC.HLP'):
        d = open(os.path.join(SAF, 'SYSTEM', f), 'rb').read()
        for no, off in hlp_table(d):
            r = walk(d, off)
            assert r, (f, no)
            rows.append(dict(file='SYSTEM/' + f, at='#%d' % no, kind='설명', size=r[1] - off, text=r[0]))
    return rows


def enemy_rows():
    """적 이름 = 파일마다 앞 0x800 안 첫 «가나 2자 이상» 문자열(0x3B6·0x3D6 근처) — 칸 = NUL 뒤 0 이 이어지는 만큼(최대 16)"""
    rows = []
    for p in sorted(glob.glob(os.path.join(SAF, 'ENEMY', 'E*.DAT'))):
        d = open(p, 'rb').read()
        for m in re.finditer(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc])+\x00', d[:0x800]):
            o = m.start(); t = walk(d, o)
            if not t or len(re.findall(r'[ぁ-んァ-ヶー]', t[0])) < 2: continue
            z = t[1]
            while z < len(d) and d[z] == 0 and z - o < 16: z += 1
            rows.append(dict(file='ENEMY/' + os.path.basename(p), at='%X' % o, kind='기록', size=z - o - 1, text=t[0]))
            break
    return rows


# 본체 /0 의 고정 길이 기록 표(시작 이름 자리, 기록 간격, 이름 칸 바이트, 개수) — 포인터가 있어도 칸 안에서만 바꿈
MAIN_TABLES = [(0x635E6, 52, 18, 210),       # 아이템(번호 u16 + 이름 18 B + 수치)
               (0x6608E, 32, 14, 88)]        # 마법(번호 u16 + 이름 14 B + 수치)


def table_rows(d):
    rows = []
    for a, step, cap, n in MAIN_TABLES:
        for k in range(n):
            o = a + step * k; r = walk(d, o)
            if r and r[1] > o and r[1] - o < cap:
                rows.append(dict(file='0', at='%X' % o, kind='기록', size=cap - 1, text=r[0]))
    return rows


def all_rows():
    rows = scr_rows()
    for f in sorted(os.listdir(os.path.join(SAF, 'OVERLAY'))):
        d = open(os.path.join(SAF, 'OVERLAY', f), 'rb').read()
        rows += ptr_rows('OVERLAY/' + f, d, PRG_BASE.get(f, 0x06090000))
    m = open(os.path.join(ROOT, 'work', 'disc0', '0'), 'rb').read()
    tb = table_rows(m); inside = {int(r['at'], 16) for r in tb}
    span = [(a, a + s * n) for a, s, c, n in MAIN_TABLES]
    rows += [r for r in ptr_rows('0', m, MAIN_BASE) if not any(x <= int(r['at'], 16) < y for x, y in span)] + tb
    rows += hlp_rows() + enemy_rows()
    return rows


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = all_rows()
    with open(os.path.join(ROOT, 'work', 'strings.tsv'), 'w', encoding='utf-8') as fo:
        fo.write('파일\t위치\t종류\t바이트\t원문\n')
        for r in rows: fo.write('%s\t%s\t%s\t%d\t%s\n' % (r['file'], r['at'], r['kind'], r['size'], r['text']))
    uniq = collections.OrderedDict()
    for r in rows:
        if r['kind'] == '꼬리': continue
        u = uniq.setdefault(r['text'], dict(kinds=collections.Counter(), locs=[], size=r['size']))
        u['kinds'][r['kind']] += 1; u['locs'].append('%s@%s' % (r['file'], r['at'])); u['size'] = min(u['size'], r['size'])
    clean = lambda t: re.sub(r'\\n|\{[0-9A-F]{2}\}', '', t)
    print('곳 %d %s · 고유 %d · %d 자' % (len(rows), dict(collections.Counter(r['kind'] for r in rows)), len(uniq), sum(len(clean(t)) for t in uniq)))
    out = os.path.join(ROOT, 'data', '번역할것'); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith('텍스트_'): os.remove(os.path.join(out, f))
    head = '번호\t종류\t최대바이트\t원문\t번역\t메모\t곳\n'; part, buf, no = 1, head, 0
    for t, u in uniq.items():
        no += 1
        fixed = not all(x.startswith(('EVENT/', 'OVERLAY/EVENT', 'SYSTEM/')) for x in u['locs'])   # 본체·BATTLE·CMDMENU·SHOP·PROFILE·적 = 남는 칸 거의 없음
        cap = str(u['size']) if ('기록' in u['kinds'] or fixed) else ''
        line = '%05d\t%s\t%s\t%s\t\t\t%s\n' % (no, '/'.join(u['kinds']), cap, t, ' '.join(u['locs']))
        if len((buf + line).encode('utf-8')) > 20000 and buf != head:
            open(os.path.join(out, '텍스트_%02d.tsv' % part), 'w', encoding='utf-8-sig').write(buf); part += 1; buf = head
        buf += line
    open(os.path.join(out, '텍스트_%02d.tsv' % part), 'w', encoding='utf-8-sig').write(buf)
    print('번역 TSV %d개' % part)


if __name__ == '__main__':
    main()
