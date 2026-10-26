# -*- coding: utf-8 -*-
r"""낱말 단위 줄바꿈(2026-10-26 실기: 게임은 창 끝에서 «글자 단위» 자동 줄바꿈 → «찼습니|다.», 넘친 줄 + \n = 빈 줄·첫 줄 밀림)
  창 폭은 문자열마다 «원문 줄 가운데 가장 긴 폭»(원문은 창에 맞게 접혀 있음 — 창 폭의 하한) · 이벤트 자막(SCR) = 36.
  번역 줄이 그보다 길면 띄어쓰기에서 다시 접음(이어지는 줄은 원래 줄의 앞 들여쓰기 «　» 를 이어받음).
  쪽(창 지움 {0B} 사이) 줄 수가 원문 쪽 최대 줄 수를 넘으면 보고만(문구를 줄여야 함).
  wrap(src, dst, scr) → 새 번역 · python tools/wrap.py → 몇 줄 바뀌는지·줄 수 넘침 보고 work/check/wrap.tsv"""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import insert

NL = '\\n'
TOK = re.compile(r'(\\n|\{07\}|\{0B\})')
FMT = re.compile(r'%[-0-9]*[dsxu]|\{[0-9A-F]{2}\}')
SCR_W = 36                   # 216 px
NL_W = 8 / 6                 # 줄바꿈 코드(0x0A)도 반각 8 px 로 폭 검사됨 → 뒤에 줄바꿈 오는 줄은 창 폭 − 8 px 까지


def units(s):
    u = 96 * len(re.findall(r'%[-0-9]*s', s)) + 32 * len(re.findall(r'%[-0-9]*[dxu]', s))   # %s = 가장 긴 이름(한글 8자 96 px) · %d = 숫자 4자리
    s = insert.ank(FMT.sub('', s)); i = 0
    while i < len(s):
        if s[i:i + 2] in ('!!', '!?'): u += 12; i += 2; continue          # 짝 글자 = 전각 한 칸(12 px)
        ch = s[i]; i += 1
        u += 8 if ord(ch) < 0x80 and ch not in insert.CUSTOM else 12      # 픽셀: 반각(공백 포함) 8 · 전각/한글 12 (0x060150F8 공백 폭 8)
    return u / 6                                             # «단위» = 6 px(전각 = 2)


def lines_of(t):
    return [x for x in re.split(r'\\n|\{07\}|\{0B\}', t)]


def fold(line, cap):
    """한 줄을 cap 안으로 띄어쓰기에서 접음 → [줄…] (낱말 하나가 cap 넘으면 그대로)"""
    if units(line) <= cap: return [line]
    ind = re.match(r'^[\u3000 ]*', line).group()
    out = []; cur = ''
    for w in re.split(r'(?<= )', line):                     # 띄어쓰기 뒤에서 자름(공백은 앞 낱말에 붙음)
        if cur and units((cur + w).rstrip(' ')) > cap:
            out.append(cur.rstrip(' ')); cur = (ind if out else '') + w
        else:
            cur += w
    out.append(cur.rstrip(' '))
    if len(out) > 1:                                         # 이어지는 줄 들여쓰기: 화자 이름표 「 뒤 줄은 «　»
        lead = '\u3000' if re.match(r'^[^「]{1,8}「', line) or ind else ''
        out = [out[0]] + [(lead + x.lstrip('\u3000 ')) if lead else x.lstrip(' ') for x in out[1:]]
    return out


TAG = re.compile(r'^[^「『　 ]{1,8}[「『]')


def reflow(page, cap, nlw=NL_W):
    """한 쪽 안 문단(화자 이름표로 시작하는 줄에서 새 문단)마다 이어 붙여 cap 안으로 낱말 단위로 다시 나눔"""
    ls = page.split(NL)
    if fits(page, cap, nlw): return page
    paras = []
    for k, x in enumerate(ls):
        if k == 0 or TAG.match(x): paras.append([x])
        else: paras[-1].append(x)
    if len(paras) > 1: return NL.join(reflow1(p, cap, nlw) for p in paras)
    return reflow1(ls, cap, nlw)


def reflow1(ls, cap, nlw=NL_W):  # noqa
    m = re.match(r'^([^「『]{1,10})([「『])', ls[0]) if ls else None      # 화자 이름표(«샘의 정령「») 안에서는 안 끊음
    if m and ' ' in m.group(1):
        ls = [m.group(1).replace(' ', ' ') + ls[0][m.end(1):]] + ls[1:]
        return reflow1(ls, cap, nlw).replace(' ', ' ')
    if isinstance(ls, str): ls = ls.split(NL)
    if fits(NL.join(ls), cap, nlw): return NL.join(ls)
    tag = re.match(r'^[^「『]{1,8}[「『]', ls[0]) is not None or any(x.startswith('　') for x in ls[1:])
    words = []
    for k, x in enumerate(ls):
        x = x.lstrip('　') if k else x
        x = x[:len(x) - len(x.lstrip('　'))] + re.sub('[　]+', ' ', x.lstrip('　')).rstrip(' ') if k == 0 else re.sub('[　]+', ' ', x).strip(' ')   # 문장 가운데 전각 공백 → 반각
        for w in re.split(r'(?<=[ 　])', x): words.append(w)
        if words and not words[-1].endswith(' ') and k < len(ls) - 1:
            words[-1] = words[-1] + ' '                      # 줄 끝 = 낱말 경계
    out = []; cur = ''
    for w in words:
        if cur and units((cur + w).rstrip(' ')) > cap - nlw:
            out.append(cur.rstrip(' ')); cur = ('　' if tag else '') + w
        else:
            cur += w
    out.append(cur.rstrip(' '))
    return NL.join(out)


def wrap(src, dst, scr, filecap=None, fixed=None):
    """scr = 이벤트 자막(216 px 3줄) · 그 밖은 «그 문자열 원문 폭» 으로 먼저, 줄이 늘면 filecap(같은 파일 원문 최장 줄 = 창 폭 하한)으로 다시.
       그래도 원문보다 줄이 늘면 손대지 않음(창 높이 모름)"""
    def go(cap, nlw=NL_W):
        parts = re.split(r'(\{07\}|\{0B\})', dst); out = []
        for p in parts:
            if re.fullmatch(r'\{07\}|\{0B\}', p or '') or not p: out.append(p); continue
            out.append(reflow(p, cap, nlw))
        return ''.join(out)
    if scr: return (dst if fits(dst, SCR_W, 0) else go(SCR_W, 0)), SCR_W   # 자막은 216 px 꽉 찬 줄 + 줄바꿈이 원문에 88번(정상)
    if fixed:                                                # 얼굴 말풍선(12칸 144 px, tools/bubble_scan.py) — 원문 폭과 상관없이 창 폭 고정
        return (dst if fits(dst, fixed) else go(fixed)), fixed
    if '\\n' not in src: return dst, None                    # 원문 한 줄짜리(고정 칸)는 줄바꿈 안 넣음
    own = max(units(x) for x in lines_of(src))
    cap = max(own, filecap or 0)                             # 창 폭 = 파일 원문 90번째 백분위(이 문장 원문 줄보다 좁게는 안 함)
    if fits(dst, cap): return dst, cap                       # 이미 들어감 — 번역자 줄바꿈 그대로
    return go(cap), cap


def fits(t, cap, nlw=NL_W):
    """뒤에 줄바꿈(\n)이 오는 줄 ≤ cap − 8 px · 그 밖(쪽 끝·{07} 앞) ≤ cap"""
    parts = re.split(r'(\\n|\{07\}|\{0B\})', t)
    for k in range(0, len(parts), 2):
        nxt = parts[k + 1] if k + 1 < len(parts) else ''
        if units(parts[k]) > cap - (nlw if nxt == NL else 0) + 1e-9: return False
    return True


def page_rows(t):
    return [len(re.split(r'\\n|\{07\}', pg)) for pg in t.split('{0B}')]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import extract
    rows = extract.all_rows(); tr = insert.final_tr(False, rows)
    kind = {}
    for r in rows: kind.setdefault(r['text'], r['file'])
    n = 0; bad = []
    with open(os.path.join(ROOT, 'work', 'check', 'wrap.tsv'), 'w', encoding='utf-8-sig') as f:
        f.write('파일\t폭\t원문\t전\t후\t줄수넘침\n')
        for s, t in tr.items():
            fn = kind.get(s, ''); scr = fn.endswith('.SCR')
            if fn.endswith(('.HLP',)) or fn.startswith('ENEMY'): continue
            w, cap = wrap(s, t, scr)
            if w == t: continue
            n += 1
            over = max(page_rows(w)) > max(max(page_rows(s)), 3 if scr else max(page_rows(s)))
            if over: bad.append(s)
            f.write('%s\t%d\t%s\t%s\t%s\t%s\n' % (fn, cap, s, t, w, '넘침' if over else ''))
    print('다시 접는 줄', n, '· 쪽 줄 수 넘침', len(bad))


if __name__ == '__main__':
    main()
