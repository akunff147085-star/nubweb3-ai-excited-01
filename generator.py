"""Generate the original 'Event Horizon Manta' image.

The scene is deliberately built from vector-like primitives and a tiny PNG
writer so the build has no asset downloads or runtime dependencies.
"""
from __future__ import annotations

import math
import random
import struct
import zlib
from pathlib import Path

W = H = 768
S = 2
SW = SH = W * S


def clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def blend(dst: list[int], src: tuple[int, int, int, int]) -> None:
    sa = src[3]
    if sa <= 0:
        return
    if sa >= 255:
        dst[:] = [src[0], src[1], src[2], 255]
        return
    da = dst[3]
    out_a = sa + (da * (255 - sa) + 127) // 255
    if out_a == 0:
        return
    for i in range(3):
        dst[i] = (src[i] * sa + dst[i] * da * (255 - sa) // 255) // out_a
    dst[3] = out_a


class Canvas:
    def __init__(self, width: int, height: int, color=(0, 0, 0, 255)):
        self.width = width
        self.height = height
        self.px = [list(color)] * (width * height)
        self.px = [list(p) for p in self.px]

    def put(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            blend(self.px[y * self.width + x], color)

    def disc(self, cx: float, cy: float, radius: float, color: tuple[int, int, int, int]) -> None:
        x0 = max(0, int(cx - radius - 1))
        x1 = min(self.width - 1, int(cx + radius + 1))
        y0 = max(0, int(cy - radius - 1))
        y1 = min(self.height - 1, int(cy + radius + 1))
        rr = radius * radius
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                d = (x - cx) ** 2 + (y - cy) ** 2
                if d <= rr:
                    a = color[3]
                elif d <= (radius + 1.2) ** 2:
                    a = int(color[3] * max(0.0, 1.0 - (math.sqrt(d) - radius) / 1.2))
                else:
                    continue
                self.put(x, y, (color[0], color[1], color[2], a))

    def line(self, points: list[tuple[float, float]], color: tuple[int, int, int, int], width: float) -> None:
        r = width / 2.0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy) or 1.0
            steps = max(1, int(length * 1.5))
            for i in range(steps + 1):
                t = i / steps
                self.disc(ax + dx * t, ay + dy * t, r, color)

    def polygon(self, points: list[tuple[float, float]], color: tuple[int, int, int, int]) -> None:
        if not points:
            return
        min_y = max(0, int(min(y for _, y in points)))
        max_y = min(self.height - 1, int(max(y for _, y in points)) + 1)
        for y in range(min_y, max_y + 1):
            scan = []
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
                if (y1 <= y < y2) or (y2 <= y < y1):
                    scan.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            scan.sort()
            for left, right in zip(scan[::2], scan[1::2]):
                for x in range(max(0, int(left)), min(self.width, int(right) + 1)):
                    self.put(x, y, color)

    def glow_disc(self, cx: float, cy: float, radius: float, color: tuple[int, int, int], strength=1.0) -> None:
        for k in range(8, 0, -1):
            r = radius * (1.0 + k * 0.28)
            a = int(max(1, color[0] * 0 + 18 * strength * (9 - k)))
            self.disc(cx, cy, r, (color[0], color[1], color[2], a))
        self.disc(cx, cy, radius, (color[0], color[1], color[2], 255))

    def downsample(self, factor: int) -> "Canvas":
        out = Canvas(self.width // factor, self.height // factor, (0, 0, 0, 255))
        for oy in range(out.height):
            for ox in range(out.width):
                acc = [0, 0, 0, 0]
                for yy in range(factor):
                    for xx in range(factor):
                        p = self.px[(oy * factor + yy) * self.width + ox * factor + xx]
                        for c in range(4):
                            acc[c] += p[c]
                n = factor * factor
                out.px[oy * out.width + ox] = [v // n for v in acc]
        return out


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def save_png(canvas: Canvas, path: Path) -> None:
    raw = bytearray()
    for row in range(canvas.height):
        raw.append(0)
        for r, g, b, a in canvas.px[row * canvas.width:(row + 1) * canvas.width]:
            raw.extend((clamp(r), clamp(g), clamp(b), clamp(a)))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 6, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


def starfield(c: Canvas) -> None:
    rng = random.Random(120401)
    for _ in range(150):
        x = rng.randrange(c.width)
        y = rng.randrange(c.height)
        # Keep the central flight path open so the silhouette reads instantly.
        if 180 < x < 720 and 160 < y < 650:
            continue
        r = rng.choice((1, 1, 1, 2, 3))
        col = rng.choice(((99, 238, 255, 150), (206, 114, 255, 145), (255, 232, 137, 155)))
        c.disc(x, y, r, col)


def arc(c: Canvas, cx: float, cy: float, radius: float, start: float, end: float,
        color: tuple[int, int, int, int], width: float, steps=80) -> None:
    points = []
    for i in range(steps + 1):
        t = start + (end - start) * i / steps
        points.append((cx + math.cos(t) * radius, cy + math.sin(t) * radius))
    c.line(points, color, width)


def draw_scene() -> Canvas:
    c = Canvas(SW, SH, (5, 7, 25, 255))
    # Deep-space gradient bands are cheap at this scale and avoid a flat fill.
    for y in range(SH):
        t = y / (SH - 1)
        ccolor = (7 + int(10 * t), 7 + int(3 * t), 36 + int(28 * t), 255)
        for x in range(SW):
            c.px[y * SW + x] = list(ccolor)
    starfield(c)

    # The impossible aperture: two opposing crescents make a clear focal frame.
    cx, cy = 412 * S, 418 * S
    c.glow_disc(cx, cy, 178 * S, (79, 240, 255), 0.22)
    arc(c, cx, cy, 214 * S, math.radians(203), math.radians(350), (45, 247, 255, 210), 15 * S)
    arc(c, cx, cy, 214 * S, math.radians(18), math.radians(158), (255, 75, 208, 235), 15 * S)
    arc(c, cx, cy, 190 * S, math.radians(204), math.radians(338), (166, 101, 255, 210), 5 * S)
    arc(c, cx, cy, 190 * S, math.radians(22), math.radians(155), (255, 185, 69, 220), 5 * S)

    # Perspective shards point toward the launch, creating momentum even small.
    shard_colors = ((36, 224, 255, 130), (179, 75, 255, 120), (255, 95, 196, 115))
    shards = [
        [(58, 88), (210, 154), (188, 177), (44, 134)],
        [(14, 254), (174, 282), (165, 300), (10, 304)],
        [(690, 72), (568, 185), (549, 168), (659, 50)],
        [(760, 246), (594, 291), (603, 272), (766, 214)],
        [(32, 692), (228, 574), (242, 591), (69, 744)],
        [(706, 714), (563, 580), (579, 565), (760, 666)],
    ]
    for pts, col in zip(shards, shard_colors * 2):
        c.polygon([(x * S, y * S) for x, y in pts], col)

    # Directional wake: ribbons are brighter near the body and taper to points.
    wake = [
        ([(70, 552), (224, 512), (375, 472), (459, 430)], (34, 226, 255, 180), 9),
        ([(118, 638), (244, 576), (380, 502), (459, 432)], (173, 76, 255, 170), 7),
        ([(54, 426), (220, 431), (367, 430), (463, 424)], (255, 72, 192, 155), 5),
        ([(164, 700), (286, 600), (398, 490), (472, 426)], (255, 188, 73, 135), 4),
    ]
    for pts, col, width in wake:
        c.line([(x * S, y * S) for x, y in pts], col, width * S)

    # Main silhouette: a manta ray flying out of the aperture toward upper-right.
    # The hooked wingtips and long tail keep its identity legible at thumbnail size.
    manta = [
        (304, 448), (334, 391), (388, 354), (457, 333), (530, 322),
        (596, 335), (651, 368), (614, 383), (584, 405), (610, 437),
        (566, 427), (526, 414), (493, 427), (472, 464), (444, 506),
        (423, 555), (410, 611), (397, 559), (374, 508), (346, 476),
    ]
    manta = [(x * S, y * S) for x, y in manta]
    c.polygon(manta, (12, 18, 61, 255))
    c.line(manta + [manta[0]], (91, 243, 255, 240), 4 * S)

    # Iridescent wing planes give the creature volume without losing the silhouette.
    c.polygon([(340*S, 421*S), (388*S, 358*S), (457*S, 333*S), (421*S, 421*S)], (38, 214, 235, 235))
    c.polygon([(421*S, 421*S), (457*S, 333*S), (530*S, 322*S), (494*S, 423*S)], (115, 65, 234, 235))
    c.polygon([(494*S, 423*S), (530*S, 322*S), (596*S, 335*S), (566*S, 427*S)], (251, 72, 185, 230))
    c.polygon([(421*S, 421*S), (494*S, 423*S), (472*S, 464*S), (444*S, 506*S)], (17, 37, 101, 245))
    c.line([(421*S, 421*S), (444*S, 506*S), (423*S, 555*S)], (129, 252, 255, 210), 3*S)

    # The face and eye are deliberately tiny but high contrast.
    c.disc(464*S, 387*S, 10*S, (3, 10, 32, 255))
    c.glow_disc(467*S, 384*S, 4*S, (255, 238, 122), 0.9)
    c.disc(468*S, 383*S, 1.5*S, (255, 255, 255, 255))

    # The surprise: an impossible pearl moon suspended inside the wing notch.
    c.glow_disc(408*S, 404*S, 25*S, (255, 235, 120), 0.65)
    c.disc(408*S, 404*S, 23*S, (255, 245, 168, 255))
    c.disc(401*S, 397*S, 18*S, (255, 255, 224, 255))
    c.disc(398*S, 393*S, 6*S, (255, 255, 255, 170))
    c.disc(414*S, 414*S, 4*S, (232, 202, 115, 160))

    # Bright leading edge and a charged tail lance focus the release direction.
    c.line([(333*S, 435*S), (389*S, 375*S), (456*S, 345*S), (526*S, 335*S), (588*S, 346*S)], (255, 255, 231, 230), 3*S)
    c.line([(423*S, 553*S), (420*S, 613*S), (430*S, 662*S)], (78, 237, 255, 220), 5*S)
    c.glow_disc(431*S, 665*S, 7*S, (255, 103, 210), 0.9)

    # Three impact sparks at the portal rim sell the exact moment of escape.
    for angle, length, col in ((-1.0, 42, (255, 227, 120, 230)), (-0.45, 30, (85, 249, 255, 230)), (0.2, 38, (255, 94, 202, 220))):
        x0, y0 = 510*S, 380*S
        x1 = x0 + math.cos(angle) * length * S
        y1 = y0 + math.sin(angle) * length * S
        c.line([(x0, y0), (x1, y1)], col, 3*S)
        c.glow_disc(x1, y1, 4*S, col[:3], 0.7)
    return c


def main() -> None:
    out = Path(__file__).with_name("entry.png")
    image = draw_scene().downsample(S)
    save_png(image, out)


if __name__ == "__main__":
    main()
