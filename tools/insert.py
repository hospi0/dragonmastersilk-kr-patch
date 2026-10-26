# -*- coding: utf-8 -*-
r"""Dragon Master Silk 번역 넣기(2026-10-26) — data/번역/텍스트_*.tsv → work/build/(디스크 경로: 0 · *.SAF)
  ★쓰는 순간 막음: 제어 코드(\n {07} {0B} %s %d …) 개수·차례 · «기록» 최대바이트 · cp932 못 쓰는 글자. 문장부호 뒤 공백은 지움.
  글꼴: KANJI.FNT 의 칸 번호는 본체 표가 정함(tools/fontmap.py) → 표는 그대로 두고, 최종 문자열에 «안 쓰이는» 한자 코드
        (한자 표 1,128) → 모자라면 안 쓰이는 히라가나·가타카나 코드 순으로 한글을 배정하고 그 칸 그림만 갈무리11 한글로.
  SCR: 차례대로 다시 씀(포인터 없음) · HLP: 앞 표(u16 BE 번호, u16 LE 오프셋) 째 다시 씀
  PRG·본체: 포인터 문자열 «덩어리»(사이가 NUL 3바이트 이하뿐인 연속 문자열)를 차례대로 4정렬로 다시 이음 → 안 들어가는 건
        같은 파일 다른 덩어리 끝 남는 칸 → BE 포인터(4정렬) 새로. 파일은 안 늘림(오버레이 뒤 BSS·다음 오버레이 자리).
        꼬리 포인터는 부모 안 같은 차례 제어 코드 자리 · «기록»(아이템·마법·적 이름) 은 칸 안 제자리.
  SAF: 바뀐 항목만 갈아 끼우고 2048 정렬로 다시 묶음(머리 표 시작 섹터·크기).
  python tools/insert.py [--test]  (--test = work/build_test 로, 번역 대신 가나를 한글로 바꾼 시험 번역)"""
import collections, glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import extract, fontmap, saf

OUT = os.path.join(ROOT, 'work', 'build')
TOK = re.compile(r'\\n|\{[0-9A-F]{2}\}|%[-0-9]*[dsx]')
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・～〜'
HANGUL = re.compile('[가-힣]')
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
# 파일 끝 뒤에 덧붙여도 되는 오버레이(이름 앞 5자 → 넘으면 안 되는 램 주소): 필드 이벤트 EVENTxxF 는 자기 BSS 참조 없음,
# 본체가 0x06098000·0x0609D000 을 버퍼로 씀. BATTLE·CMDMENU·SHOP·PROFILE 은 파일 끝 바로 뒤를 변수로 써서 못 늘림.
GROW = {'EVENT': 0x06098000}
HOLES = {}
MAIN = {}   # 본체(/0, 늘 램에 있음) 남는 빈칸 — 오버레이에서 넘친 글을 여기 두고 절대 주소로 가리킴(2026-10-26 BATTLE 넘침)
PACK = bool(os.environ.get('PACK'))
# 못 늘리는데 넘치는 오버레이(2026-10-26 하스피 «123 전부 ㄱ»): 덩어리 1 B 촘촘히 담기 + 한글 뒤 전각 ！？。 → 반각 !?. 를 기본으로
TIGHT = ('BATTLE.PRG', 'CMDMENU.PRG', 'PROFILE.PRG', 'SHOP.PRG')
BUDGET = None        # --budget 이면 넘치는 줄 목록(파일, 오프셋, 원래 B, 새 B, 원문, 번역) — 출력 파일은 안 씀


def squeeze(s):
    return re.sub('([' + re.escape(PUNCT) + ']) +', r'\1', s)


def load_tr(test=False):
    tr = {}
    if test:
        kana = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん'
        ko = '가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호구누두루무부수우주추쿠투푸후그느드르므브스으즈츠크트프흐기니디리미비시이지치키티피히'
        for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역할것', '텍스트_*.tsv'))):
            for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
                c = l.split('\t')
                if len(c) < 7: continue
                t = ''.join(ko[kana.index(ch) % len(ko)] if ch in kana else ('카' if '\u30a1' <= ch <= '\u30f6' else ch) for ch in c[3])
                if c[1] != '기록' and int(c[0]) % 20 == 0 and all(x.startswith(('EVENT/', 'OVERLAY/EVENT', 'SYSTEM/')) for x in c[6].split()):
                    t += '시험'          # 넘침 경로 시험 — 늘릴 수 있는 곳(자막·도움말·필드 이벤트)만. 본체·BATTLE·CMDMENU·SHOP 은 남는 칸이 거의 없음
                tr[c[3]] = t
        return tr
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역', '텍스트_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 4 and c[4].strip():
                tr[c[3]] = c[4].rstrip('\r').replace('·', '・')     # 앞뒤 공백은 정렬일 수 있어 보존
    return tr


def check(src, dst):
    """\\n 은 번역 때 다시 접을 수 있음(하스피 번역 2026-10-26) — {07}{0B}%s 등만 개수·차례 같게"""
    a = [x for x in TOK.findall(src) if x != '\\n']; b = [x for x in TOK.findall(dst) if x != '\\n']
    assert a == b, ('제어 코드 다름', src, dst, a, b)


# 홑 반각 글자: 게임(0x060150F8)이 찍을 수 있는 건 공백·숫자·영문·. - / = : 뿐(+ 짝 «!!»·«!?»). 나머지는 네모(2026-10-26 실기 «응?» «소년이여!»).
ANK_OK = set(' 0123456789.-/=:') | {chr(c) for c in range(0x41, 0x5B)} | {chr(c) for c in range(0x61, 0x7B)}
WIDE = {'!': '！', '?': '？', '~': '～', '(': '（', ')': '）', '+': '＋', '&': '＆', '*': '※',
        '―': 'ー', '—': 'ー', '─': 'ー'}      # 줄표는 기호표에 없음 → 장음(2026-10-26 실기 «아―» 네모)
CUSTOM = set(",'")                                            # 전각도 글꼴에 없음 → 한글처럼 빈 칸 배정해 Galmuri 로 그림


def ank(t):
    """짝 «!!»·«!?» 는 두고, 찍을 수 없는 홑 반각을 전각으로(제어 코드·%s 는 건드리지 않음)"""
    out = []
    for tok in re.split(r'(\n|\{[0-9A-F]{2}\}|%[-0-9]*[dsx])', t):
        if not tok or re.fullmatch(r'\n|\{[0-9A-F]{2}\}|%[-0-9]*[dsx]', tok): out.append(tok or ''); continue
        i = 0; r = ''
        while i < len(tok):
            if tok[i:i + 2] in ('!!', '!?'): r += tok[i:i + 2]; i += 2; continue
            ch = tok[i]
            if ch == '"': ch = '“' if r.count('“') <= r.count('”') else '”'   # 반각 큰따옴표 → 글꼴에 있는 “ ”
            r += WIDE.get(ch, ch); i += 1
        out.append(r)
    return ''.join(out)


_B0 = fontmap.main_bin()
_ORIG = {ch for r in extract.all_rows() for ch in r['text']}   # 원문에 쓰인 글자


class Enc:
    def __init__(self, texts):
        texts = [ank(t) for t in texts]
        used = set()
        for t in texts:
            for ch in re.sub(r'\\n|\{[0-9A-F]{2}\}|%[-0-9]*[dsxu]|!!|!\?', '', t):     # 짝 «!!»·«!?»·서식은 검사 밖
                if HANGUL.match(ch) or ch in CUSTOM: continue
                try:
                    b = ch.encode('cp932')
                except UnicodeEncodeError:
                    raise SystemExit('⛔ cp932 로 못 쓰는 글자 %r in %r' % (ch, t))
                if len(b) == 2:
                    used.add(b[0] << 8 | b[1])
                    if ch not in _ORIG and fontmap.glyph_of(b[0] << 8 | b[1], _B0) is None:   # 글꼴에 없는 글자 = 실기 네모 → 막음(원문에 원래 있던 글자는 둠)
                        raise SystemExit('⛔ 글꼴에 없는 글자 %r(U+%04X) in %r' % (ch, ord(ch), t))
                elif ch not in ANK_OK and ch not in _ORIG:
                    raise SystemExit('⛔ 찍을 수 없는 홑 반각 %r in %r' % (ch, t))
        b0 = fontmap.main_bin()
        slots = [(fontmap.sjis(j), n) for j, n in fontmap.kanji_table(b0)]
        slots += [(fontmap.sjis(j), j - 0x23F9) for j in range(0x2421, 0x2474)]
        slots += [(fontmap.sjis(j), j - 0x2481) for j in range(0x2521, 0x2577)]
        free = []; seen = set()
        for c, n in slots:
            if c not in used and n not in seen: free.append((c, n)); seen.add(n)
        hs = sorted({ch for t in texts for ch in re.sub(r'\n|\{[0-9A-F]{2}\}|%[-0-9]*[dsx]', '', t) if HANGUL.match(ch) or ch in CUSTOM})
        if len(hs) > len(free):
            raise SystemExit('⛔ 한글 %d자 > 쓸 수 있는 칸 %d' % (len(hs), len(free)))
        self.map = dict(zip(hs, free))        # 한글 → (SJIS 코드, 칸 번호)
        self.used = used; self.free = len(free)

    def enc(self, t):
        t = ank(t)
        out = bytearray()
        for tok in re.split(r'(\\n|\{[0-9A-F]{2}\})', t):
            if tok == '\\n': out.append(0x0A)
            elif re.fullmatch(r'\{[0-9A-F]{2}\}', tok or ''): out.append(int(tok[1:3], 16))
            else:
                for ch in tok or '':
                    if ch in self.map:
                        c = self.map[ch][0]; out += bytes([c >> 8, c & 255])
                    else:
                        out += ch.encode('cp932')
        return bytes(out)


PUNCT_GLYPH = {',': {(2, 8), (3, 8), (2, 9), (3, 9), (3, 10), (2, 11)},     # 쉼표·작은따옴표는 직접 그림(Galmuri 쉼표는 칸 아래로 내려감)
               "'": {(2, 0), (3, 0), (2, 1), (3, 1), (3, 2), (2, 3)}}


def hangul_glyph(ch, _g={}):
    if ch in PUNCT_GLYPH:
        rows = [0] * 12
        for x, y in PUNCT_GLYPH[ch]: rows[y] |= 0x8000 >> x
        return b''.join(struct.pack('>H', r) for r in rows)
    if not _g:
        import bdf
        _g['f'] = bdf.Font(GALMURI)
        ys = [y for c in '가각힣맑앙' for x, y in _g['f'].draw(c)[0]]
        _g['top'] = min(ys)
    pts, w = _g['f'].draw(ch)
    rows = [0] * 12
    for x, y in pts:
        yy = y - _g['top'] + 1
        assert 0 <= yy < 12 and 0 <= x < 12, ('글자 칸 밖', ch, x, yy)
        rows[yy] |= 0x8000 >> x
    return b''.join(struct.pack('>H', r) for r in rows)


def do_scr(d, tr, enc):
    out = bytearray(); i = 0
    while i < len(d):
        if d[i] == 0xFF:
            n = 6 if d[i + 1] in (1, 5) else 2
            out += d[i:i + n]; i += n; continue
        t, e = extract.walk(d, i, {0x0A})
        out += (enc.enc(tr[t]) if t in tr else d[i:e]) + b'\0'; i = e + 1
    return bytes(out)


def do_hlp(d, tr, enc):
    ent = extract.hlp_table(d); first = ent[0][1]
    body = bytearray(); tab = bytearray(d[:first]); offs = {}
    for k, (no, off) in enumerate(ent):
        if off in offs:
            new_off = offs[off]
        else:
            t, e = extract.walk(d, off)
            s = enc.enc(tr[t]) if t in tr else d[off:e]
            new_off = first + len(body); offs[off] = new_off
            body += s + b'\0'
        assert new_off < 0x10000
        struct.pack_into('<H', tab, 4 * k + 2, new_off)
    tail = d[max(offs) + len(extract.walk(d, max(offs))[0]) + 1:] if False else b''
    return bytes(tab) + bytes(body)


def do_ptr_file(rel, d, base, tr, enc, stat, recs):
    b = bytearray(d)
    rows = [r for r in extract.all_rows_cache if r['file'] == rel]
    ptrs = collections.defaultdict(list)
    for k in range(0, len(b) - 3, 4):
        v = struct.unpack_from('>I', b, k)[0] - base
        if 0 <= v < len(b): ptrs[v].append(k)
    # 기록(칸 안 제자리)
    for r in rows:
        if r['kind'] != '기록' or r['text'] not in tr: continue
        o = int(r['at'], 16); new = enc.enc(tr[r['text']])
        assert len(new) <= r['size'], ('⛔ 기록 넘침', rel, r['at'], r['text'], tr[r['text']])
        b[o:o + r['size'] + 1] = new + bytes(r['size'] + 1 - len(new)); stat['기록'] += 1
    parents = sorted((int(r['at'], 16), r) for r in rows if r['kind'] == '문자')
    tails = [(int(r['at'], 16), r) for r in rows if r['kind'] == '꼬리']
    clusters = []; end = None
    for o, r in parents:
        if clusters and o - end <= 3 and all(x == 0 for x in b[end:o]):
            clusters[-1][1].append((o, r))
        else:
            clusters.append([o, [(o, r)]])
        end = o + r['size'] + 1
    moved = {}; over = []; holes = []
    tight = rel.split('/')[-1] in TIGHT
    pack = PACK or tight
    if pack:                                                 # 덩어리 전체를 빈칸으로 보고 큰 문자열부터 채움(1 B 단위 — 문자열은 바이트로 읽음)
        allit = []
        for a, items in clusters:
            z = items[-1][0] + items[-1][1]['size'] + 1
            orig = bytes(b[a:z]); b[a:z] = bytes(z - a); holes.append([a, z])
            for o, r in items:
                allit.append((o, enc.enc(tr[r['text']]) if r['text'] in tr else orig[o - a:o - a + r['size']]))
        over = allit; clusters = []
        if tight:                                            # 빈칸마다 «가장 꽉 차는 조합»(배낭) — 큰 것부터 담으면 조각난 빈칸에 짧은 줄이 못 들어감
            over = knap(over, holes, moved, b)
    for a, items in clusters:
        z = items[-1][0] + items[-1][1]['size'] + 1
        al = 4 if all(o % 4 == 0 for o, _ in items) else (2 if all(o % 2 == 0 for o, _ in items) else 1)   # 원래 덩어리 정렬 그대로
        orig = bytes(b[a:z]); b[a:z] = bytes(z - a); p = a
        for o, r in items:
            new = enc.enc(tr[r['text']]) if r['text'] in tr else orig[o - a:o - a + r['size']]
            if p + len(new) + 1 <= z:
                b[p:p + len(new)] = new; moved[o] = p; p = (p + len(new) + 1 + al - 1) // al * al
            else:
                over.append((o, new))
        if z - p >= 4: holes.append([p, z])
    grow = GROW.get(rel.split('/')[-1][:5])
    if grow and over:                                        # 필드 이벤트 오버레이: 파일 끝 뒤(본체 버퍼 0x06098000 앞)에 덧붙일 수 있음
        own = [struct.unpack_from('>I', d, k)[0] - base for k in range(0, len(d) - 3, 2)]
        after = [v for v in own if len(d) <= v < grow - base]
        start = (max([len(d)] + [v + 4 for v in after]) + 15) & ~15
        b += bytes(start - len(b)); holes.append([start, grow - base])
        b += bytes(grow - base - start)                      # 뒤에서 남는 만큼 잘라냄
    for o, new in sorted(over, key=lambda x: -len(x[1])):
        h = min((h for h in holes if h[1] - h[0] >= len(new) + 1), key=lambda h: h[1] - h[0], default=None)
        if not h and rel != '0' and MAIN:                   # 오버레이 → 본체 남는 빈칸
            mh = min((h for h in MAIN['holes'] if h[1] - h[0] >= len(new) + 1), key=lambda h: h[1] - h[0], default=None)
            if mh:
                p = mh[0]; MAIN['b'][p:p + len(new)] = new; MAIN['b'][p + len(new)] = 0; moved[o] = ('M', p); mh[0] = p + len(new) + 1
                stat['본체로'] += 1; continue
        if not h and BUDGET is not None:                     # --budget: 넘치는 줄 모아 보고만
            r = next(r for x, r in parents if x == o)
            BUDGET.append((rel, o, r['size'], len(new), r['text'], tr.get(r['text'], ''))); continue
        assert h, ('⛔ 문자열 넘침 — 남는 칸 없음', rel, hex(o), len(new), sum(y - x for x, y in holes))
        p = h[0]; b[p:p + len(new)] = new; b[p + len(new)] = 0; moved[o] = p; h[0] = p + len(new) + 1 if pack else (p + len(new) + 1 + 3) & ~3
    if BUDGET is not None and any(r[0] == rel for r in BUDGET):
        HOLES[rel] = sum(max(0, y - x) for x, y in holes)     # 못 넣은 줄이 있을 때 남은 (조각난) 빈칸 합
        if os.environ.get('HOLEDBG'): print('   빈칸', rel, sorted(y - x for x, y in holes if y > x))
    if rel == '0':
        MAIN.update(b=b, base=base, holes=[h for h in holes if h[1] - h[0] >= 4])
        if os.environ.get('HOLEDBG'): print('   본체 빈칸', sorted((h[1] - h[0] for h in holes), reverse=True)[:15], sum(h[1] - h[0] for h in holes))
    addr = lambda p: MAIN['base'] + p[1] if isinstance(p, tuple) else base + p
    for o, p in moved.items():
        for k in ptrs[o]: struct.pack_into('>I', b, k, addr(p))
    BT = re.compile(rb'\x0a|[\x07\x0b]|%[-0-9]*[dsx]')
    for o, r in tails:
        par, pr = max(((p, x) for p, x in parents if p < o), key=lambda t: t[0])
        d0 = o - par; P = enc.enc(pr['text']); Q = enc.enc(tr.get(pr['text'], pr['text']))
        if P == Q: nd = d0
        else:
            tp = list(BT.finditer(P)); tq = list(BT.finditer(Q))
            i = next(i for i, m in enumerate(tp) if m.start() <= d0 < max(m.end(), m.start() + 1))
            nd = tq[i].start() + (d0 - tp[i].start())
        for k in ptrs[o]: struct.pack_into('>I', b, k, addr(moved[par]) + nd)
    stat['문자'] += len(moved); stat['다른 덩어리로'] += len(over)
    if len(b) > len(d):                                      # 덧붙인 구역의 쓰지 않은 꼬리 잘라냄(4 정렬)
        last = max([len(d)] + [p + len(enc.enc(tr.get(r['text'], r['text']))) + 1 for o, r in parents for p in [moved.get(o, 0) if not isinstance(moved.get(o, 0), tuple) else 0]])
        b = b[:(max(last, len(d)) + 3) & ~3]; stat['늘어난 B'] += len(b) - len(d)
    return bytes(b)


def repack_saf(name, repl):
    d = open(os.path.join(ROOT, 'work', 'disc0', name), 'rb').read()
    ent = saf.entries(d)
    head = bytearray(d[:ent[0][1]]); body = bytearray(); p = ent[0][1]
    for i, (nm, o, s) in enumerate(ent):
        data = repl.get(nm, d[o:o + s])
        struct.pack_into('>II', head, 4 + 20 * i + 12, p // 2048, len(data))
        pad = data + bytes((-len(data)) % 2048)
        body += pad; p += len(pad)
    return bytes(head) + bytes(body)


def knap(items, holes, moved, b):
    """items [(원래 오프셋, 바이트)] 를 holes [[a, z]] 에 NUL 포함 1 B 단위로 — 작은 빈칸부터 채움 합이 가장 큰 부분집합. 남는 items 반환"""
    # 같은 바이트·꼬리가 같은 줄은 긴 줄 안을 가리킴(게임은 포인터부터 NUL 까지 읽음) — 뿌리만 담음
    roots = sorted(items, key=lambda x: -len(x[1])); alias = {}; keep = []
    for o, new in roots:
        r = next(((ro, len(rn) - len(new)) for ro, rn in keep if rn.endswith(new)), None)
        if r: alias[o] = r
        else: keep.append((o, new))
    def plan(items0, hs):
        """빈칸 차례 hs 대로 «가장 꽉 차는 조합» → ([(빈칸, [항목…])], 남는 항목)"""
        left = list(items0); out = []
        for h in hs:
            C = h[1] - h[0]
            best = {0: None}                                 # 합 → (앞 합, 항목 번호)
            for i, (o, new) in enumerate(left):
                w = len(new) + 1
                for t in sorted(best, reverse=True):
                    u = t + w
                    if u <= C and u not in best: best[u] = (t, i)
                if C in best: break
            t = max(best); pick = []
            while best[t]: t, i = best[t][0], best[t][1]; pick.append(i)
            out.append((h, [left[i] for i in sorted(pick)]))
            left = [x for k, x in enumerate(left) if k not in set(pick)]
        return out, left
    import random
    rnd = random.Random(1)                                   # 여러 차례로 해 보고 남는 바이트가 가장 적은 것(늘 같은 결과)
    tries = [(sorted(holes, key=lambda h: h[1] - h[0]), keep), (sorted(holes, key=lambda h: h[1] - h[0]), sorted(keep, key=lambda x: -len(x[1]))),
             (sorted(holes), keep)]
    for _ in range(300):
        hs = sorted(holes, key=lambda h: h[1] - h[0]); its = list(keep); rnd.shuffle(its)
        if rnd.random() < 0.5: rnd.shuffle(hs)
        tries.append((hs, its))
    def bfd(items0, hs):
        """큰 것부터 «가장 꼭 맞는 빈칸»(best-fit decreasing) — 남는 칸 크기 리스트로 계산"""
        room = {id(h): h[1] - h[0] for h in hs}; got = {id(h): [] for h in hs}; lf = []
        for it in sorted(items0, key=lambda x: -len(x[1])):
            w = len(it[1]) + 1
            c = min((h for h in hs if room[id(h)] >= w), key=lambda h: room[id(h)], default=None)
            if c is None: lf.append(it); continue
            room[id(c)] -= w; got[id(c)].append(it)
        return [(h, got[id(h)]) for h in hs], lf
    if os.environ.get('HOLEDBG'): print('   knap 빈칸', sorted((h[1] - h[0] for h in holes), reverse=True), '항목', sorted((len(n) + 1 for _, n in keep), reverse=True), sum(h[1] - h[0] for h in holes), sum(len(n) + 1 for _, n in keep))
    def hybrid(items0, hs, th):
        """th 바이트 넘는 글은 best-fit 으로 먼저, 남은 자리(빈칸 뒤쪽)를 작은 글 배낭으로"""
        big = [x for x in items0 if len(x[1]) + 1 > th]; small = [x for x in items0 if len(x[1]) + 1 <= th]
        pl1, lf1 = bfd(big, hs)
        used = {id(h): sum(len(n) + 1 for _, n in g) for h, g in pl1}
        rest = [[h[0] + used[id(h)], h[1], h] for h in hs]
        pl2, lf2 = plan(small, sorted(rest, key=lambda r: r[1] - r[0]))
        got = {id(h): list(g) for h, g in pl1}
        for r, g in pl2: got[id(r[2])] += g
        return [(h, got[id(h)]) for h in hs], lf1 + lf2
    cands = [lambda: bfd(keep, sorted(holes, key=lambda h: h[1] - h[0]))]
    for th in (12, 16, 20, 24, 28, 32, 40):
        cands.append(lambda th=th: hybrid(keep, sorted(holes, key=lambda h: h[1] - h[0]), th))
    cands += [lambda hs=hs, its=its: plan(its, hs) for hs, its in tries]
    for _ in range(600):                                      # 무작위 섞은 혼합(빈칸 차례·글 차례·문턱)
        th = rnd.choice((8, 12, 16, 20, 24, 28, 32, 36, 40, 48)); its = list(keep); rnd.shuffle(its)
        hs = sorted(holes, key=lambda h: h[1] - h[0])
        if rnd.random() < 0.5: rnd.shuffle(hs)
        cands.append(lambda th=th, its=its, hs=hs: hybrid(its, hs, th))
    best_plan = None
    for f in cands:
        pl, lf = f()
        score = sum(len(n) + 1 for _, n in lf)
        if best_plan is None or score < best_plan[0]: best_plan = (score, pl, lf)
        if score == 0: break
    for _ in range(200):                                      # 고치기: 남은 글을 맨 앞에 두고(배낭은 앞 글을 먼저 고름) 빈칸 차례를 바꿔 다시
        if best_plan[0] == 0: break
        lo = {o for o, _ in best_plan[2]}
        its = [x for x in keep if x[0] in lo] + [x for x in keep if x[0] not in lo]
        rest = its[len(lo):]; rnd.shuffle(rest); its = its[:len(lo)] + rest
        hs = sorted(holes, key=lambda h: h[1] - h[0])
        if rnd.random() < 0.5: hs = hs[::-1]
        elif rnd.random() < 0.5: rnd.shuffle(hs)
        pl, lf = plan(its, hs); score = sum(len(n) + 1 for _, n in lf)
        if score < best_plan[0]: best_plan = (score, pl, lf)
    _, pl, left = best_plan
    if os.environ.get('HOLEDBG'): print('   knap 남음', best_plan[0], [len(n) for _, n in left])
    for h, picks in pl:
        p = h[0]
        for o, new in picks:
            b[p:p + len(new)] = new; b[p + len(new)] = 0; moved[o] = p; p += len(new) + 1
        h[0] = p
    for o, (ro, off) in alias.items():
        if ro in moved: moved[o] = moved[ro] + off
    lo = {o for o, _ in left}
    return left + [(o, new) for o, new in items if o in alias and alias[o][0] in lo]


def final_tr(test, rows):
    """넣을 번역(squeeze + TIGHT 오버레이 문자열은 한글 뒤 ！？。 → !?.; HALFPUNCT=1 이면 전체) — verify.py 도 같은 것을 씀"""
    tight = {r['text'] for r in rows if r['file'].split('/')[-1] in TIGHT}
    half = lambda v: squeeze(re.sub('(?<=[가-힣!?])。', '.', v).replace('：', ':'))   # ！？ 는 홑 반각이면 네모(ank 가 전각으로 되돌림) → 。 만 반각 «.»
    out = {k: half(v) if os.environ.get('HALFPUNCT') or k in tight else squeeze(v) for k, v in load_tr(test).items()}
    import wrap                                              # 낱말 단위 줄바꿈(게임은 창 끝에서 글자 단위로 자름) — verify 도 같은 것
    scr = {r['text'] for r in rows if r['file'].endswith('.SCR')}
    skip = {r['text'] for r in rows if r['file'].endswith('.HLP') or r['file'].startswith('ENEMY') or r['kind'] == '기록'}
    def fcap(f):                                             # 창 폭(단위 6 px) — 원문 줄 폭 분포·실기 스샷으로 정함(2026-10-26 밤)
        n = f.split('/')[-1]
        if n.startswith('EVENT') and n.endswith('F.PRG'): return 46
        return {'SHOP.PRG': 32, 'BATTLE.PRG': 24, 'CMDMENU.PRG': 24}.get(n, 0)   # 실기 스샷: 상점 192 px · 메시지 144 px
    cap_of = {}
    for r in rows: cap_of[r['text']] = max(cap_of.get(r['text'], 0), fcap(r['file']))
    import bubble_scan                                       # 얼굴 말풍선 = 12칸 144 px(0x0602046C(…, 12, 3)) — 필드 창 46 이 아님(2026-10-26 밤 실기 '세 걸음 분')
    bo = bubble_scan.bubble_offsets()
    def fits_bubble(s):                                      # 원문이 12칸 × 3줄(글자 단위 자동 줄바꿈)에 들어가야 말풍선으로 봄 — 아니면 판정 의심
        for pg in s.split('{0B}'):
            ls = pg.replace('{07}', '').split('\\n')
            if pg.replace('{07}', '') and sum(max(1, -(-int(wrap.units(x) + 1.33) // 24)) for x in ls) > 3: return False
        return True
    bub = {r['text'] for r in rows if r['file'] in bo and re.fullmatch(r'[0-9A-F]+', r['at']) and int(r['at'], 16) in bo[r['file']]
           and fits_bubble(r['text'])}
    return {k: v if k in skip else wrap.wrap(k, v, k in scr, cap_of.get(k), 24 if k in bub else None)[0] for k, v in out.items()}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    global OUT, BUDGET
    test = '--test' in sys.argv
    if test: OUT = os.path.join(ROOT, 'work', 'build_test')
    if '--budget' in sys.argv:
        BUDGET = []; OUT = os.path.join(ROOT, 'work', 'build_budget')
    rows = extract.all_rows(); extract.all_rows_cache = rows
    tr = final_tr(test, rows)
    bad = 0
    for s, t in tr.items():
        try:
            check(s, t)
        except AssertionError as e:
            bad += 1; print('⛔', e.args[0][1][:40], '|', e.args[0][2][:40])
    caps = collections.defaultdict(lambda: 1 << 30)
    for r in rows:
        if r['kind'] == '기록': caps[r['text']] = min(caps[r['text']], r['size'])
    enc = Enc([tr.get(r['text'], r['text']) for r in rows if r['kind'] != '꼬리'])
    for s, cap in caps.items():
        if s in tr and len(enc.enc(tr[s])) > cap:
            bad += 1; print('⛔ 기록 넘침 %d > %d: %s → %s' % (len(enc.enc(tr[s])), cap, s, tr[s]))
    if bad: raise SystemExit('⛔ %d줄 규칙 위반 — 안 넣음' % bad)
    stat = collections.Counter(); os.makedirs(OUT, exist_ok=True)
    # 본체
    m = fontmap.main_bin()
    do_ptr_file('0', m, extract.MAIN_BASE, tr, enc, stat, rows)   # 본체는 오버레이가 남는 빈칸을 쓴 뒤에 씀(MAIN)
    for o, nm in ((0x63002, '실크'), (0x63062, '아카'), (0x630C2, '아오'), (0x63122, '키')):   # 파티원 초기 자료 이름 칸(12 B, 0x60 간격 — 문자열 표 밖이라 추출에 없음)
        assert m[o:o + 12].rstrip(b'\0').decode('cp932') in ('シルク', 'アカ', 'アオ', 'キ'), hex(o)
        e = enc.enc(nm); MAIN['b'][o:o + 12] = e + bytes(12 - len(e)); stat['파티 이름'] += 1
    # EVENT.SAF: SCR
    ev = {}
    for p in glob.glob(os.path.join(extract.SAF, 'EVENT', '*.SCR')):
        nm = os.path.basename(p); ev[nm] = do_scr(open(p, 'rb').read(), tr, enc); stat['자막 파일'] += 1
    open(os.path.join(OUT, 'EVENT.SAF'), 'wb').write(repack_saf('EVENT.SAF', ev))
    # OVERLAY.SAF: PRG
    ov = {}
    for f in sorted(os.listdir(os.path.join(extract.SAF, 'OVERLAY'))):
        ov[f] = do_ptr_file('OVERLAY/' + f, open(os.path.join(extract.SAF, 'OVERLAY', f), 'rb').read(),
                            extract.PRG_BASE.get(f, 0x06090000), tr, enc, stat, rows)
    # 설정 «배틀 속도：N5 T2» — 값은 라벨과 따로 x = 80 px(원문 라벨 72 + 8)에 찍힘(0x06080E2E mov #80,r1).
    # 다른 값은 라벨 바로 뒤에 이어 찍히니 번역 라벨 폭으로 맞춤(2026-10-26 하스피 «한 칸 떨어져 거슬려»)
    import wrap
    cm = bytearray(ov['CMDMENU.PRG']); assert cm[0xE2E:0xE30] == b'\xE1\x50', cm[0xE2E:0xE30].hex()
    lab = round(wrap.units(tr.get('バトル速度：', 'バトル速度：')) * 6)
    assert 0 < lab < 128, lab
    cm[0xE2F] = lab; ov['CMDMENU.PRG'] = bytes(cm)
    open(os.path.join(OUT, 'OVERLAY.SAF'), 'wb').write(repack_saf('OVERLAY.SAF', ov))
    assert len(MAIN['b']) == len(m); open(os.path.join(OUT, '0'), 'wb').write(bytes(MAIN['b']))
    # SYSTEM.SAF: HLP + 글꼴
    sy = {}
    for f in ('ITEM.HLP', 'MAGIC.HLP'):
        d = open(os.path.join(extract.SAF, 'SYSTEM', f), 'rb').read(); sy[f] = do_hlp(d, tr, enc)
        stat['도움말 B'] += len(sy[f]) - len(d)
    fnt = bytearray(open(fontmap.FNT, 'rb').read())
    for ch, (c, n) in enc.map.items():
        fnt[24 * n:24 * n + 24] = hangul_glyph(ch)
    sy['KANJI.FNT'] = bytes(fnt)
    if not test:                                             # 타이틀 읽기 줄 «드래곤 마스터 실크»(tools/gfx_logo.py, 2026-10-26 밤 하스피 승인)
        import subprocess
        subprocess.run([sys.executable, os.path.join(HERE, 'gfx_logo.py')], check=True, capture_output=True)
        sy['SILKLOGO.SEB'] = open(os.path.join(ROOT, 'work', 'gfx_out', 'SILKLOGO.SEB'), 'rb').read()
        # 얼굴 옆 이름표·상태 이상 글자 그림판(tools/gfx_sysdat.py, 2026-10-26 밤 하스피 승인)
        subprocess.run([sys.executable, os.path.join(HERE, 'gfx_sysdat.py')], check=True, capture_output=True)
        sy['SYSTEM.DAT'] = open(os.path.join(ROOT, 'work', 'gfx_out', 'SYSTEM.DAT'), 'rb').read()
    open(os.path.join(OUT, 'SYSTEM.SAF'), 'wb').write(repack_saf('SYSTEM.SAF', sy))
    # ENEMY.SAF: 이름
    en = {}
    for r in rows:
        if r['file'].startswith('ENEMY/') and r['text'] in tr:
            nm = r['file'].split('/')[1]
            d = bytearray(en.get(nm) or open(os.path.join(extract.SAF, 'ENEMY', nm), 'rb').read())
            o = int(r['at'], 16); new = enc.enc(tr[r['text']])
            assert len(new) <= r['size'], ('⛔ 적 이름 넘침', nm, r['text'], tr[r['text']])
            d[o:o + r['size'] + 1] = new + bytes(r['size'] + 1 - len(new)); en[nm] = bytes(d); stat['적 이름'] += 1
    open(os.path.join(OUT, 'ENEMY.SAF'), 'wb').write(repack_saf('ENEMY.SAF', en))
    print('넣음 %s · 한글 %d자 / 쓸 수 있는 칸 %d' % (dict(stat), len(enc.map), enc.free))
    if BUDGET is not None:
        q = os.path.join(ROOT, 'work', 'check', 'budget_over.tsv')
        with open(q, 'w', encoding='utf-8-sig', newline='\n') as fo:
            fo.write('파일\t오프셋\t원래B\t번역B\t원문\t번역\n')
            for r in BUDGET: fo.write('%s\t%X\t%d\t%d\t%s\t%s\n' % r)
        per = collections.defaultdict(lambda: [0, 0])
        for r in BUDGET: per[r[0]][0] += 1; per[r[0]][1] += r[3] + 1
        for f, (n, s) in sorted(per.items()):
            print('  ⛔ %-22s 못 넣은 줄 %3d · %5d B · 남은 조각 빈칸 %d B → 실제 모자람 약 %d B' % (f, n, s, HOLES.get(f, 0), s - HOLES.get(f, 0)))
        print(q)


if __name__ == '__main__':
    main()
