"""
Generates the app icon (app_icon.ico) - a teal rounded square with a white
medical cross. Run this only when the icon needs changing; the finished .ico
is committed alongside the code, so the built .exe never needs Pillow.

    python make_icon.py
"""

import os
from PIL import Image, ImageDraw

TEAL = (15, 118, 110, 255)
TEAL_DEEP = (11, 79, 74, 255)
WHITE = (255, 255, 255, 255)

SIZES = [256, 128, 64, 48, 32, 16]


def draw_icon(size):
    # Draw large then downscale, so edges stay smooth at small sizes.
    scale = 8
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    radius = int(s * 0.22)

    # Soft top-to-bottom gradient, clipped to a rounded square.
    gradient = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(gradient)
    for y in range(s):
        t = y / max(s - 1, 1)
        gd.line(
            [(0, y), (s, y)],
            fill=tuple(int(TEAL[i] + (TEAL_DEEP[i] - TEAL[i]) * t) for i in range(4)),
        )
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=255)
    img.paste(gradient, (0, 0), mask)

    # White medical cross.
    arm = int(s * 0.155)
    length = int(s * 0.52)
    cx = cy = s // 2
    d.rounded_rectangle(
        [cx - arm // 2, cy - length // 2, cx + arm // 2, cy + length // 2],
        radius=arm // 4, fill=WHITE,
    )
    d.rounded_rectangle(
        [cx - length // 2, cy - arm // 2, cx + length // 2, cy + arm // 2],
        radius=arm // 4, fill=WHITE,
    )

    return img.resize((size, size), Image.LANCZOS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "app_icon.ico")
    images = [draw_icon(s) for s in SIZES]
    images[0].save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    print("Wrote", out)


if __name__ == "__main__":
    main()
