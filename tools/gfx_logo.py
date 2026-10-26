# -*- coding: utf-8 -*-
r"""타이틀 로고(SYSTEM/SILKLOGO.SEB = 팔레트 256색 512 B + 320×224 8비트) 읽기 줄 «ドラゴンマスターシルク» → «드래곤 마스터 실크»(2026-10-26)
  원본 줄: 행 128~141 · x 132~296 · 글자 = 팔레트 137(연회색 148,148,131) · 그림자 = 158(짙은 색) 오른쪽 아래 1px · 바탕 0(검정).
  새것: 그 칸(행 127~142, x 126~302)을 0 으로 지우고 나눔고딕을 8배로 그려 줄인 덮임 정도를 «이 그림 팔레트의 가까운 색»으로
        (글자 137 · 그림자 158 섞음, 원본처럼 가장자리 중간색) — 실제 칠해진 행 14(128~141) · 오른쪽 끝 296 맞춤.
        (처음 갈무리14 비트맵 → 하스피 «고해상도로» 2026-10-26)
  → work/gfx_out/SILKLOGO.SEB · 미리보기 work/check/preview_logo.png(원본|새것 3배) — ⛔하스피 승인 전엔 빌드에 안 넣음"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import bdf, seb
from PIL import Image

W, H = 320, 224; INK, SHADOW = 137, 158
Y0, Y1, X0, X1 = 127, 142, 126, 302
TEXT = '드래곤 마스터 실크'
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = bytearray(open(os.path.join(ROOT, 'work', 'saf', 'SYSTEM', 'SILKLOGO.SEB'), 'rb').read()); orig = bytes(d)
    px = 512
    for y in range(Y0, Y1 + 1):
        for x in range(X0, X1 + 1):
            d[px + y * W + x] = 0
    # 하스피 «고해상도로»(2026-10-26): 갈무리 비트맵 대신 나눔고딕을 8배로 그려 줄이고, 덮임 정도를 이 그림 팔레트의 가까운 색으로(원본도 가장자리 중간색)
    from PIL import ImageDraw, ImageFont
    S = 8; INK_H = 14                                    # 원본 줄 칸 14행(128~141) 꽉 — 13 으로는 가타카나보다 작아 보임
    size = 10
    while True:                                          # «실제로 칠해진» 행이 13행이 되는 크기(글꼴 상자 높이는 잉크보다 큼)
        font = ImageFont.truetype(FONT, size * S); l, t, r, bt = font.getbbox(TEXT)
        big = Image.new('L', (r - l + 2 * S, bt - t + 2 * S), 0)
        ImageDraw.Draw(big).text((S - l, S - t), TEXT, font=font, fill=255)
        cov = big.resize((big.width // S, big.height // S), Image.BOX)
        cw, ch = cov.size
        ink_rows = [y for y in range(ch) if max(cov.getpixel((x, y)) for x in range(cw)) > 100]   # 흐린 가장자리 행은 안 셈
        if ink_rows[-1] - ink_rows[0] + 1 >= INK_H: break
        size += 0.5
    print('글자 크기 %.1f · 잉크 행 %d~%d · 폭 %d' % (size, ink_rows[0], ink_rows[-1], cw))
    ox = 296 + 1 - cw                                    # 원본처럼 오른쪽 끝(Silk 오른쪽 아래)에 맞춤
    oy = 128 + (14 - (ink_rows[-1] - ink_rows[0] + 1)) // 2 - ink_rows[0]   # 원본 줄(128~141) 가운데
    pal = [seb.rgb(struct.unpack_from('>H', d, 2 * i)[0]) for i in range(256)]
    ink = pal[INK]; sh = pal[SHADOW]
    near = lambda c: min(range(1, 256), key=lambda i: sum((a - b) ** 2 for a, b in zip(pal[i], c)))
    cache = {}
    for y in range(ch + 1):
        for x in range(cw + 1):
            ai = cov.getpixel((x, y)) / 255 if x < cw and y < ch else 0
            as_ = cov.getpixel((x - 1, y - 1)) / 255 if 0 < x <= cw and 0 < y <= ch else 0
            if ai < 0.12 and as_ < 0.5: continue
            c = tuple(ai * i_ + (1 - ai) * as_ * s_ for i_, s_ in zip(ink, sh))
            X, Y = ox + x, oy + y
            assert X0 <= X <= X1 and Y0 <= Y <= Y1, ('칸 밖', X, Y)
            key = tuple(round(v) for v in c)
            if key not in cache: cache[key] = near(c) if max(key) > 6 else 0
            d[px + Y * W + X] = cache[key]
    w = cw
    os.makedirs(os.path.join(ROOT, 'work', 'gfx_out'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'gfx_out', 'SILKLOGO.SEB'), 'wb').write(d)
    a = seb.render(orig, W, 256); b = seb.render(bytes(d), W, 256)
    out = Image.new('RGB', (W * 2 + 8, H), (80, 0, 80)); out.paste(a, (0, 0)); out.paste(b, (W + 8, 0))
    out = out.resize((out.width * 3, out.height * 3), Image.NEAREST)
    p = os.path.join(ROOT, 'work', 'check', 'preview_logo.png'); out.save(p)
    out.crop((0, 100 * 3, out.width, 160 * 3)).save(os.path.join(ROOT, 'work', 'check', 'preview_logo_zoom.png'))
    print(p, '글자 폭', w)


if __name__ == '__main__':
    main()
