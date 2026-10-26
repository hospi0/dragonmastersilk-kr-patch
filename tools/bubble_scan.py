# -*- coding: utf-8 -*-
r"""필드 이벤트(EVENTxxF.PRG) 대사 중 «얼굴 말풍선»(12칸 144 px × 3줄) 으로 나가는 문자열 가리기 (2026-10-26 밤)
  말풍선 여는 함수 = 0x060299FC · 0x0602996C(둘 다 0x0602046C(…, 12, 3)) · 0x06033348(→ 0x060299FC).
  한 함수(rts 까지) 안에서 말풍선을 연 뒤 읽히는 문자열 포인터 + 여는 호출 직전 r7 문자열 = 말풍선.
  bubble_offsets() → {파일: set(문자열 오프셋)} · python tools/bubble_scan.py → 개수"""
import glob, os, struct, sys
import capstone
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BASE = 0x06090000
OPEN = {0x060299FC, 0x0602996C, 0x06033348}
CLOSE = 0x06029AA0
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2 | capstone.CS_MODE_BIG_ENDIAN)


def scan(d):
    """→ (말풍선 쪽 문자열 오프셋, 그 밖 문자열 오프셋)"""
    bub, other = set(), set()
    regs = {}; inb = False; pend = []                     # pend = 이 함수에서 아직 판정 안 된 문자열(말풍선 열기 전)
    a = 0
    while a < len(d) - 1:
        ins = next(md.disasm(d[a:a + 2], BASE + a), None)
        if ins is None: a += 2; continue
        m, op = ins.mnemonic, ins.op_str
        if m == 'mov.l' and op.startswith('0x') and ',' in op:
            la = int(op.split(',')[0], 16) - BASE; r = op.split(',')[1].strip()
            if 0 <= la <= len(d) - 4:
                v = struct.unpack_from('>I', d, la)[0]; regs[r] = v
                if BASE <= v < BASE + len(d):
                    if inb: bub.add(v - BASE)
                    else: pend.append(v - BASE)
        elif m == 'jsr':
            r = op.strip('@ ')
            if regs.get(r) in OPEN:
                inb = True
                if pend: bub.add(pend[-1])                   # 여는 호출의 인자(r7·스택) 문자열도 말풍선
                other.update(pend[:-1]); pend = []
            elif regs.get(r) == CLOSE:                       # 0x06029AA0 = 말풍선 닫기
                inb = False
        elif m == 'rts':
            other.update(pend); pend = []; inb = False; regs = {}
        a += 2
    other.update(pend)
    return bub, other - bub


def bubble_offsets():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'saf', 'OVERLAY', 'EVENT*F.PRG'))):
        out['OVERLAY/' + os.path.basename(f)] = scan(open(f, 'rb').read())[0]
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for k, v in bubble_offsets().items():
        if v: print(k, len(v), sorted(hex(x) for x in v)[:12])
