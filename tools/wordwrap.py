# -*- coding: utf-8 -*-
r"""게임 글자 찍기 낱말 단위 줄바꿈 훅(2026-10-26 밤 — 실기: 창 끝 글자 단위 자동 줄바꿈 → «찼습니|다.», 빈 줄, 첫 줄 밀림)
  0x06014424 = 글자 하나 찍기(r4 창, r5 글 포인터 → r0 다음 포인터) · 0x06014270 = putchar(r4 창, r5 코드)
  창 구조체: +42 = 현재 x(word) · +12 = 창 폭(word, 넘으면 0x060142EC 에서 글자 단위 줄바꿈).
  훅: 지금 글자가 공백(0x20)이면 다음 낱말 폭(반각 8, 2바이트 12)을 재서 x + 8 + 폭 > 창 폭 이고 x ≠ 0 이면
      putchar(0x0A) 로 줄을 바꾸고 공백은 건너뜀(포인터 + 1 반환). 아니면 원래 0x06014424 로.
  호출 리터럴: 본체 0x06014544(문자열 찍기 0x06014518 안) · 이벤트 오버레이 7개 각 2곳 → 훅 주소로.
  code(base) → 바이트"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sh2asm import A

ORIG, PUTC = 0x06014424, 0x06014270


def code(base):
    a = A(base)
    a.w(0x6050)                    # mov.b @r5,r0
    a.w(0x8820)                    # cmp/eq #32,r0
    a.br('bt', 'sp')
    a.L('go'); a.ld(0, ORIG); a.w(0x402B, 0x0009)          # jmp @r0 ; nop
    a.L('sp')
    a.w(0x6153, 0x7101, 0xE200)    # mov r5,r1 ; add #1,r1 ; mov #0,r2
    a.L('lp')
    a.w(0x6014, 0x600C, 0xE320, 0x3036)   # mov.b @r1+,r0 ; extu.b r0,r0 ; mov #32,r3 ; cmp/hi r3,r0
    a.br('bf', 'done')
    a.w(0xE37F, 0x3036)            # mov #127,r3 ; cmp/hi r3,r0
    a.br('bt', 'wide')
    a.br('bra', 'lp'); a.w(0x7208)                          # add #8,r2 (지연)
    a.L('wide'); a.w(0x7101); a.br('bra', 'lp'); a.w(0x720C)   # add #1,r1 ; bra lp ; add #12,r2
    a.L('done')
    a.w(0x6143, 0x712A, 0x6111, 0x2118)   # mov r4,r1 ; add #42,r1 ; mov.w @r1,r1 ; tst r1,r1
    a.br('bt', 'go')                       # 줄 맨 앞이면 그대로
    a.w(0x7108, 0x8546, 0x3107)           # add #8,r1 ; mov.w @(12,r4),r0 ; cmp/gt r0,r1  (공백만으로 넘으면 게임이 원래대로)
    a.br('bt', 'go')
    a.w(0x312C, 0x3107)                   # add r2,r1 ; cmp/gt r0,r1
    a.br('bf', 'go')
    a.w(0x4F22, 0x2F56, 0x2F46)            # sts.l pr,@-r15 ; mov.l r5,@-r15 ; mov.l r4,@-r15
    a.ld(0, PUTC); a.w(0x400B, 0xE50A)     # jsr @r0 ; mov #10,r5
    a.w(0x64F6, 0x65F6, 0x4F26, 0x6053, 0x000B, 0x7001)   # 되돌리고 r0 = r5 + 1 ; rts
    return a.build()


if __name__ == '__main__':
    b = code(0x06070000); print(len(b), b.hex())
