"""PWA 아이콘 만들기: 분홍(#B8326A) 바탕 위 흰 하트. 실행: python3 scripts/make_icons.py"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROSE = (0xB8, 0x32, 0x6A, 255)
OUT = Path(__file__).resolve().parent.parent / "public" / "icons"


def heart(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float) -> None:
    # 원 두 개 + 아래로 모이는 삼각형으로 하트를 그린다.
    r = w * 0.27
    lx, rx, top = cx - w * 0.22, cx + w * 0.22, cy - w * 0.12
    draw.ellipse([lx - r, top - r, lx + r, top + r], fill="white")
    draw.ellipse([rx - r, top - r, rx + r, top + r], fill="white")
    tip = (cx, cy + w * 0.42)

    def tangent(ox: float, side: int) -> tuple[float, float]:
        # 아래 꼭짓점에서 원에 닿는 접선 → 이음매에 오목한 홈이 생기지 않는다
        dx, dy = tip[0] - ox, tip[1] - top
        base, alpha = math.atan2(dy, dx), math.acos(r / math.hypot(dx, dy))
        a = base + side * alpha
        return (ox + r * math.cos(a), top + r * math.sin(a))

    draw.polygon([tangent(lx, 1), (cx, top), tangent(rx, -1), tip], fill="white")


def make(size: int, name: str, maskable: bool = False, rounded: bool = True) -> None:
    s = size * 4  # 크게 그려서 줄이면 가장자리가 매끄럽다
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if maskable or not rounded:
        d.rectangle([0, 0, s, s], fill=ROSE)
    else:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=ROSE)
    # maskable은 가운데 80% 안전 영역 안에 그린다
    heart(d, s / 2, s / 2 + s * 0.03, s * (0.42 if maskable else 0.56))
    img.resize((size, size), Image.LANCZOS).save(OUT / name)


OUT.mkdir(parents=True, exist_ok=True)
make(192, "icon-192.png")
make(512, "icon-512.png")
make(192, "maskable-192.png", maskable=True)
make(512, "maskable-512.png", maskable=True)
make(180, "apple-touch-icon.png", rounded=False)
print(sorted(p.name for p in OUT.iterdir()))
