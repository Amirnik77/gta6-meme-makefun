#!/usr/bin/env python3
"""Builds meme.png for the make.fun bounty "Post a GTA 6 meme on X".

The joke: a queue outside "Leonida Admissions" that has not moved since 2013.
The make.fun ghost stands in line like everyone else, holding its star coin,
and its speech bubble carries the pitch: its agent earns real money on
make.fun while it waits.

The ghost is cut out of make.fun's official press mark (assets/ghost-mark.png,
the mark-1024.png file from https://make.fun/press/) so the mascot in the
picture is the real one, not a redraw. Everything else is drawn with PIL:
a Leonida sunset, palm silhouettes, a ticket booth, and the queue.

Run:  python3 make_meme.py   (writes meme.png next to this file)
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
MARK = HERE / "assets" / "ghost-mark.png"
OUT = HERE / "meme.png"

W, H = 1200, 900
CAPTION_H = 148
HORIZON = 640

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
BOLD = str(FONT_DIR / "DejaVuSans-Bold.ttf")
MONO_BOLD = str(FONT_DIR / "DejaVuSansMono-Bold.ttf")

INK = (24, 18, 38)
GHOST_DISC_MAGENTA = (199, 24, 130)


# ---------------------------------------------------------------- ghost cut-out

def extract_ghost(mark_path: Path) -> Image.Image:
    """Cuts the ghost (body, sparkle eyes, star coin and hand) out of the
    press mark, dropping the magenta disc and black ring around it.

    The disc is one flat magenta, so pixels that are transparent or disc
    magenta count as "background-like". A flood fill from the corners marks
    every background-like pixel it can reach; the ghost's black outline is a
    closed barrier, so the magenta of the coin it holds is never reached and
    stays part of the ghost. The disc itself is ringed by the badge's black
    border, which the corner fill cannot cross, so the fill is seeded again
    from points inside the disc: disc-minus-ghost is one connected region,
    and the ghost's outline still protects the coin.
    """
    im = Image.open(mark_path).convert("RGBA")
    px = np.asarray(im).astype(int)
    r, g, b, a = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
    magenta = (r > 110) & (g < 120) & (b > 70) & (r > g + 60)
    passable = (a < 128) | magenta

    mask = Image.fromarray(np.where(passable, 0, 255).astype("uint8"), "L").convert("RGB")
    seeds = [(0, 0), (512, 130), (150, 512), (874, 512), (512, 894),
             (250, 250), (774, 774), (250, 774), (774, 250)]
    for sx, sy in seeds:
        if mask.getpixel((sx, sy)) == (0, 0, 0):
            ImageDraw.floodfill(mask, (sx, sy), (1, 2, 3), thresh=0)
    m = np.asarray(mask)
    exterior = (m[..., 0] == 1) & (m[..., 1] == 2) & (m[..., 2] == 3)

    # The badge's black ring is barrier too, but it is not the ghost: in the
    # complement of the exterior it forms its own component, cut off from the
    # ghost by the filled disc. Keep only the component that holds the
    # ghost's body, seeded from the mark's centre.
    comp = Image.fromarray(np.where(exterior, 0, 255).astype("uint8"), "L").convert("RGB")
    cx, cy = im.width // 2, im.height // 2
    if comp.getpixel((cx, cy)) == (255, 255, 255):
        ImageDraw.floodfill(comp, (cx, cy), (9, 9, 9), thresh=0)
    cm = np.asarray(comp)
    is_ghost = (cm[..., 0] == 9) & (cm[..., 1] == 9) & (cm[..., 2] == 9)

    out = px.copy()
    out[..., 3] = np.where(is_ghost, px[..., 3], 0)
    ghost = Image.fromarray(out.astype("uint8"), "RGBA")
    bbox = ghost.getchannel("A").getbbox()
    ghost = ghost.crop(bbox)
    # Soften the cut edge by a hair so it sits naturally in the scene.
    alpha = ghost.getchannel("A").filter(ImageFilter.GaussianBlur(0.7))
    ghost.putalpha(alpha)
    return ghost


# ---------------------------------------------------------------- helpers

def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def fit_font(path: str, text: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    """Largest size, from `start` down, at which `text` fits `max_width`."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    size = start
    while size > 8:
        f = font(path, size)
        if probe.textlength(text, font=f) <= max_width:
            return f
        size -= 2
    return font(path, size)


def centered(draw: ImageDraw.ImageDraw, cx: int, y: int, text: str,
             f: ImageFont.FreeTypeFont, fill) -> None:
    draw.text((cx - draw.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


def lerp(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def sky_gradient(w: int, h: int) -> Image.Image:
    stops = [(0.0, (46, 22, 96)), (0.45, (112, 44, 128)),
             (0.78, (205, 92, 118)), (1.0, (255, 168, 110))]
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                d.line([(0, y), (w, y)], fill=lerp(c0, c1, (t - t0) / (t1 - t0)))
                break
    return img


def outrun_sun(size: int) -> Image.Image:
    """A striped retro sun: solid at the top, sliced by gaps toward the base."""
    sun = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(sun)
    top, bottom = (255, 205, 110), (255, 110, 130)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=lerp(top, bottom, y / size) + (255,))
    disc = Image.new("L", (size, size), 0)
    ImageDraw.Draw(disc).ellipse([0, 0, size, size], fill=255)
    # Cut horizontal gaps, thin at the middle and thicker toward the bottom.
    gap = Image.new("L", (size, size), 255)
    gd = ImageDraw.Draw(gap)
    y, thick = int(size * 0.52), 3
    while y < size:
        gd.rectangle([0, y, size, y + thick], fill=0)
        y += int(size * 0.11)
        thick += 3
    disc = Image.composite(disc, Image.new("L", (size, size), 0), gap)
    sun.putalpha(disc)
    return sun


def palm(draw: ImageDraw.ImageDraw, x: int, base: int, h: int, lean: int, color) -> None:
    """A flat palm silhouette: a leaning trunk and drooping fronds."""
    top = (x + lean, base - h)
    pts = []
    for i in range(25):
        t = i / 24
        pts.append((x + lean * t * t, base - h * t))
    draw.line(pts, fill=color, width=max(7, h // 13), joint="curve")
    for ang_deg in range(-168, -11, 18):
        ang = math.radians(ang_deg)
        length = h * 0.52
        frond = []
        for i in range(17):
            t = i / 16
            fx = top[0] + math.cos(ang) * length * t
            fy = top[1] + math.sin(ang) * length * t + (t * t) * h * 0.22
            frond.append((fx, fy))
        draw.line(frond, fill=color, width=max(4, h // 30))


def person(draw: ImageDraw.ImageDraw, cx: int, base: int, h: int,
           color, rim, cap: bool = False, phone: bool = False,
           ticket: bool = False) -> None:
    """A simple queue silhouette seen from behind."""
    head_r = h * 0.105
    head_cy = base - h + head_r
    body_w = h * 0.36
    body_top = head_cy + head_r * 0.85
    body_bot = base - h * 0.34
    leg_w = body_w * 0.20
    # Rim light pass, nudged toward the sun, then the body on top of it.
    for dx, col in ((-4, rim), (0, color)):
        draw.ellipse([cx - head_r + dx, head_cy - head_r, cx + head_r + dx, head_cy + head_r], fill=col)
        draw.rounded_rectangle([cx - body_w / 2 + dx, body_top, cx + body_w / 2 + dx, body_bot],
                               radius=h * 0.07, fill=col)
        for side in (-1, 1):
            lx = cx + side * body_w * 0.24
            draw.rectangle([lx - leg_w / 2 + dx, body_bot, lx + leg_w / 2 + dx, base], fill=col)
    if cap:
        draw.pieslice([cx - head_r * 1.05, head_cy - head_r * 1.05,
                       cx + head_r * 1.05, head_cy + head_r * 0.75], 180, 360, fill=(214, 51, 108))
        draw.rectangle([cx - head_r * 1.3, head_cy - head_r * 0.12, cx + head_r * 1.3, head_cy], fill=(214, 51, 108))
    if phone:
        draw.rectangle([cx + body_w * 0.52, body_bot - h * 0.16,
                        cx + body_w * 0.52 + h * 0.075, body_bot - h * 0.02], fill=(240, 240, 220))
    if ticket:
        draw.rectangle([cx - body_w * 0.72, body_bot - h * 0.13,
                        cx - body_w * 0.72 + h * 0.11, body_bot - h * 0.03], fill=(245, 240, 220))


def shadow(draw: ImageDraw.ImageDraw, cx: int, base: int, w: int) -> None:
    draw.ellipse([cx - w / 2, base - 10, cx + w / 2, base + 12], fill=(10, 6, 20))


# ---------------------------------------------------------------- the scene

def build_scene() -> Image.Image:
    img = sky_gradient(W, H)
    draw = ImageDraw.Draw(img, "RGBA")

    # Ground.
    draw.rectangle([0, HORIZON, W, H], fill=(22, 14, 40))
    draw.rectangle([0, HORIZON, W, HORIZON + 26], fill=(52, 36, 84))

    # Sun, low over the water, left of centre.
    sun = outrun_sun(320)
    img.paste(sun, (150, HORIZON - 285), sun)
    draw = ImageDraw.Draw(img, "RGBA")

    # Skyline silhouettes along the horizon, windows lit, seeded so the
    # picture is the same every run.
    rng = random.Random(6)
    x = -10
    while x < W:
        bw = rng.randint(46, 96)
        bh = rng.randint(50, 165)
        draw.rectangle([x, HORIZON - bh, x + bw, HORIZON], fill=(30, 18, 52))
        for _ in range(bw * bh // 420):
            wx = x + rng.randint(5, max(6, bw - 10))
            wy = HORIZON - bh + rng.randint(6, max(7, bh - 14))
            draw.rectangle([wx, wy, wx + 4, wy + 6], fill=(255, 205, 105, 210))
        x += bw + rng.randint(4, 16)

    # Palms framing the scene.
    palm(draw, 66, HORIZON + 8, 300, 52, (26, 15, 44))
    palm(draw, 1152, HORIZON + 8, 340, -64, (26, 15, 44))
    palm(draw, 150, HORIZON + 10, 210, 30, (34, 20, 56))

    body_col, rim_col = (33, 27, 58), (86, 62, 122)

    # The queue, back to front. Feet on the ground line at y = 795.
    shadow(draw, 150, 795, 120)
    person(draw, 150, 795, 262, body_col, rim_col, phone=True)
    shadow(draw, 320, 798, 116)
    person(draw, 320, 798, 252, body_col, rim_col)

    # The ghost, third in line, holding its star coin.
    ghost = extract_ghost(MARK)
    gh = 336
    gw = round(ghost.width * gh / ghost.height)
    ghost = ghost.resize((gw, gh), Image.LANCZOS)
    gx, gy = 545 - gw // 2, 795 - gh
    shadow(draw, 545, 797, gw * 0.8)
    img.paste(ghost, (gx, gy), ghost)
    draw = ImageDraw.Draw(img, "RGBA")

    shadow(draw, 782, 795, 104)
    person(draw, 782, 795, 238, body_col, rim_col, cap=True, ticket=True)

    # The booth the line is (still) waiting for.
    bx0, bx1 = 872, 1192
    draw.rounded_rectangle([bx0 - 14, 296, bx1 + 8, 366], radius=12, fill=(22, 15, 40))
    draw.rounded_rectangle([bx0 - 14, 296, bx1 + 8, 366], radius=12, outline=(255, 120, 180), width=3)
    centered(draw, (bx0 + bx1) // 2, 316, "LEONIDA ADMISSIONS", fit_font(BOLD, "LEONIDA ADMISSIONS", 300, 34), (255, 255, 255))
    draw.rectangle([bx0, 392, bx1, 700], fill=(238, 226, 192))
    draw.rectangle([bx0, 392, bx1, 700], outline=INK, width=4)
    # Awning over the booth's top edge, magenta and cream stripes.
    for i in range(8):
        sx = bx0 + i * (bx1 - bx0) // 8
        col = (214, 51, 108) if i % 2 == 0 else (245, 238, 220)
        draw.polygon([(sx, 392), (sx + (bx1 - bx0) // 8, 392),
                      (sx + (bx1 - bx0) // 8 - 12, 428), (sx - 12, 428)], fill=col)
    draw.line([(bx0 - 12, 428), (bx1 - 12, 428)], fill=INK, width=3)
    # Window with the number that never changes.
    draw.rectangle([bx0 + 34, 452, bx1 - 34, 612], fill=(16, 22, 34))
    draw.rectangle([bx0 + 34, 452, bx1 - 34, 612], outline=INK, width=4)
    centered(draw, (bx0 + bx1) // 2, 470, "NOW SERVING", fit_font(MONO_BOLD, "NOW SERVING", 240, 30), (255, 190, 90))
    centered(draw, (bx0 + bx1) // 2, 508, "2013", fit_font(MONO_BOLD, "2013", 240, 74), (255, 190, 90))

    # Velvet rope across the booth entrance: the line has not been called.
    for post_x in (845, 1085):
        draw.ellipse([post_x - 9, 646, post_x + 9, 664], fill=(230, 190, 90))
        draw.rectangle([post_x - 4, 660, post_x + 4, 772], fill=(40, 32, 60))
    rope = []
    for i in range(33):
        t = i / 32
        rx = 845 + (1085 - 845) * t
        ry = 668 + math.sin(t * math.pi) * 44
        rope.append((rx, ry))
    draw.line(rope, fill=(178, 34, 52), width=8)

    # Speech bubble from the ghost: the pitch, in its own voice.
    bub = (372, 170, 838, 296)
    draw.rounded_rectangle(bub, radius=26, fill=(255, 255, 255), outline=(10, 10, 14), width=5)
    draw.polygon([(518, 294), (594, 294), (544, 436)], fill=(255, 255, 255))
    draw.line([(518, 294), (544, 436)], fill=(10, 10, 14), width=5)
    draw.line([(594, 294), (544, 436)], fill=(10, 10, 14), width=5)
    draw.rectangle([514, 288, 598, 298], fill=(255, 255, 255))
    line1 = "my agent earns real money"
    line2 = "on make.fun while I wait"
    f1 = fit_font(BOLD, line1, bub[2] - bub[0] - 44, 31)
    f2 = fit_font(BOLD, line2, bub[2] - bub[0] - 44, 31)
    centered(draw, (bub[0] + bub[2]) // 2, 192, line1, f1, (12, 10, 16))
    centered(draw, (bub[0] + bub[2]) // 2, 234, line2, f2, (12, 10, 16))

    # Caption bar across the top.
    draw.rectangle([0, 0, W, CAPTION_H], fill=(8, 6, 12))
    caption = "IN LINE FOR GTA 6 SINCE 2013"
    cf = fit_font(BOLD, caption, W - 60, 72)
    centered(draw, W // 2, (CAPTION_H - cf.size) // 2 - 4, caption, cf, (255, 255, 255))

    return img


if __name__ == "__main__":
    build_scene().save(OUT)
    print(f"wrote {OUT}")
