#!/usr/bin/env python3
"""Create the deterministic "Event Horizon Kite" competition image."""

from __future__ import annotations

import math
import struct
import sys
import zlib
from collections.abc import Sequence
from pathlib import Path

WIDTH = 768
HEIGHT = 768
TAU = math.tau


class Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 4)

    def set_pixel(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 4
            self.pixels[offset:offset + 4] = bytes(color)

    def blend(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        offset = (y * self.width + x) * 4
        alpha = color[3]
        if alpha == 255:
            self.pixels[offset:offset + 4] = bytes(color)
            return
        if alpha == 0:
            return
        inverse = 255 - alpha
        old = self.pixels[offset:offset + 4]
        self.pixels[offset] = (color[0] * alpha + old[0] * inverse) // 255
        self.pixels[offset + 1] = (color[1] * alpha + old[1] * inverse) // 255
        self.pixels[offset + 2] = (color[2] * alpha + old[2] * inverse) // 255
        self.pixels[offset + 3] = min(255, alpha + (old[3] * inverse) // 255)

    def disc(self, cx: float, cy: float, radius: float,
             color: tuple[int, int, int, int]) -> None:
        left = max(0, int(cx - radius - 1))
        right = min(self.width - 1, int(cx + radius + 1))
        top = max(0, int(cy - radius - 1))
        bottom = min(self.height - 1, int(cy + radius + 1))
        radius_sq = radius * radius
        for y in range(top, bottom + 1):
            dy = y - cy
            for x in range(left, right + 1):
                dx = x - cx
                distance_sq = dx * dx + dy * dy
                if distance_sq <= radius_sq:
                    self.blend(x, y, color)
                elif distance_sq <= radius_sq + radius * 2:
                    edge = max(0.0, min(1.0, radius + 1.0 - math.sqrt(distance_sq)))
                    self.blend(x, y, (color[0], color[1], color[2], int(color[3] * edge)))

    def line(self, points: Sequence[tuple[float, float]], width: float,
             color: tuple[int, int, int, int]) -> None:
        # Union segment coverage before blending: translucent joins stay smooth.
        radius = width / 2.0
        coverage: dict[int, int] = {}
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            dx, dy = x1 - x0, y1 - y0
            length_sq = dx * dx + dy * dy
            for y in range(max(0, math.floor(min(y0, y1) - radius - 1)),
                           min(self.height, math.ceil(max(y0, y1) + radius + 2))):
                for x in range(max(0, math.floor(min(x0, x1) - radius - 1)),
                               min(self.width, math.ceil(max(x0, x1) + radius + 2))):
                    t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / length_sq)) if length_sq else 0.0
                    distance = math.hypot(x - x0 - t * dx, y - y0 - t * dy)
                    alpha = int(color[3] * max(0.0, min(1.0, radius + 0.5 - distance)))
                    if alpha:
                        key = y * self.width + x
                        coverage[key] = max(coverage.get(key, 0), alpha)
        for key, alpha in coverage.items():
            self.blend(key % self.width, key // self.width, (*color[:3], alpha))

    def polygon(self, points: Sequence[tuple[float, float]],
                color: tuple[int, int, int, int]) -> None:
        min_x = max(0, int(min(x for x, _ in points)))
        max_x = min(self.width - 1, int(max(x for x, _ in points)) + 1)
        min_y = max(0, int(min(y for _, y in points)))
        max_y = min(self.height - 1, int(max(y for _, y in points)) + 1)
        for y in range(min_y, max_y + 1):
            intersections: list[float] = []
            for index, (x0, y0) in enumerate(points):
                x1, y1 = points[(index + 1) % len(points)]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    intersections.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            intersections.sort()
            for left, right in zip(intersections[::2], intersections[1::2]):
                for x in range(max(min_x, int(left)), min(max_x, int(right)) + 1):
                    self.blend(x, y, color)


def background(canvas: Canvas) -> None:
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Deep indigo corners, with a hot aurora centered on the opening.
            distance = math.hypot(x - 430.0, y - 380.0) / 560.0
            glow = max(0.0, 1.0 - distance)
            horizon = max(0.0, 1.0 - math.hypot(x - 400.0, y - 265.0) / 420.0)
            red = int(7 + 24 * glow + 22 * horizon)
            green = int(12 + 8 * glow + 25 * horizon)
            blue = int(34 + 47 * glow + 67 * horizon)
            canvas.set_pixel(x, y, (red, green, blue, 255))


def starfield(canvas: Canvas) -> None:
    # Coordinates and brightness are fixed so every invocation is byte-identical.
    stars = [
        (58, 88, 2, (116, 218, 255, 180)), (112, 174, 1, (255, 244, 180, 190)),
        (178, 64, 2, (198, 154, 255, 170)), (245, 135, 1, (255, 255, 255, 180)),
        (318, 52, 2, (112, 229, 255, 160)), (399, 102, 1, (255, 255, 222, 210)),
        (526, 62, 2, (255, 178, 114, 155)), (625, 124, 1, (182, 241, 255, 180)),
        (714, 75, 2, (249, 133, 255, 150)), (80, 334, 1, (255, 255, 255, 160)),
        (154, 288, 2, (104, 218, 255, 180)), (690, 318, 2, (255, 217, 130, 160)),
        (734, 491, 1, (174, 172, 255, 170)), (77, 610, 2, (255, 123, 187, 140)),
        (188, 704, 1, (120, 231, 255, 180)), (610, 683, 2, (255, 245, 172, 140)),
        (704, 641, 1, (255, 255, 255, 190)),
    ]
    for x, y, radius, color in stars:
        canvas.disc(x, y, radius, color)


def energy_trails(canvas: Canvas) -> None:
    # Sweeping arcs pull the eye toward the impossible opening.
    trails = [
        ([(35, 574), (115, 521), (197, 475), (285, 431), (356, 390)], 24,
         (255, 68, 171, 120)),
        ([(25, 652), (134, 619), (239, 565), (322, 493), (383, 409)], 12,
         (55, 222, 255, 205)),
        ([(83, 731), (190, 698), (290, 635), (367, 546), (407, 423)], 7,
         (255, 198, 67, 220)),
        ([(728, 572), (653, 536), (579, 486), (522, 425), (478, 349)], 18,
         (153, 72, 255, 125)),
        ([(747, 647), (657, 617), (586, 572), (527, 503), (487, 405)], 8,
         (255, 102, 216, 190)),
    ]
    for points, width, color in trails:
        canvas.line(points, width + 18, (color[0], color[1], color[2], 22))
        canvas.line(points, width, color)


def horizon_ring(canvas: Canvas) -> None:
    # A broken glowing ellipse, assembled from sampled arc segments.
    center_x, center_y = 407.0, 341.0
    for radius, width, color in [
        (192, 46, (35, 213, 255, 45)),
        (164, 16, (255, 89, 190, 190)),
        (147, 7, (255, 231, 119, 230)),
    ]:
        arc: list[tuple[float, float]] = []
        for index in range(221):
            angle = -0.34 + index * TAU / 220.0
            # Leave a dramatic gap where the kite pierces the ring.
            if 2.26 < angle < 3.06:
                if len(arc) > 1:
                    canvas.line(arc, width, color)
                arc = []
                continue
            arc.append((center_x + radius * math.cos(angle),
                        center_y + radius * 0.58 * math.sin(angle)))
        if len(arc) > 1:
            canvas.line(arc, width, color)


def kite_and_burst(canvas: Canvas) -> None:
    # The central silhouette is a kite-shaped void surfing out of the ring.
    canvas.polygon([(404, 113), (548, 302), (429, 405), (311, 286)],
                   (20, 115, 160, 255))
    canvas.polygon([(404, 113), (548, 302), (414, 293)], (79, 232, 241, 255))
    canvas.polygon([(311, 286), (414, 293), (429, 405)], (72, 67, 157, 255))
    canvas.line([(404, 113), (548, 302), (429, 405), (311, 286), (404, 113)],
                8, (255, 238, 142, 245))
    canvas.line([(404, 113), (429, 405)], 3, (83, 221, 255, 220))
    canvas.line([(311, 286), (548, 302)], 3, (255, 91, 201, 220))

    # Four radiant fins make the silhouette read as a launch, not a flat diamond.
    fins = [
        ([(404, 113), (373, 42), (429, 105)], (49, 216, 255, 225)),
        ([(548, 302), (638, 291), (557, 326)], (255, 92, 186, 220)),
        ([(429, 405), (446, 494), (407, 414)], (255, 199, 63, 220)),
        ([(311, 286), (223, 310), (303, 263)], (139, 89, 255, 210)),
    ]
    for points, color in fins:
        canvas.polygon(points, color)
        canvas.line(points + [points[0]], 4, (255, 245, 196, 170))


    # The burst behind the kite gives the eye a single, explosive moment.
    for index in range(28):
        angle = index * TAU / 28.0 + 0.08
        inner = 116 + (index % 3) * 10
        outer = 238 + (index % 5) * 18
        start = (407 + inner * math.cos(angle), 312 + inner * 0.7 * math.sin(angle))
        end = (407 + outer * math.cos(angle), 312 + outer * 0.7 * math.sin(angle))
        color = [(255, 214, 74, 180), (72, 220, 255, 180), (255, 77, 190, 175)][index % 3]
        canvas.line([start, end], 3 + index % 3, color)

    canvas.disc(407, 312, 42, (255, 191, 66, 24))
    canvas.disc(407, 312, 24, (255, 239, 169, 245))
    canvas.disc(407, 312, 11, (255, 255, 247, 255))

    # Draw the rider last, silhouetted against the light rather than hidden by it.
    canvas.disc(397, 259, 14, (5, 10, 28, 255))
    canvas.polygon([(384, 273), (410, 273), (420, 315), (392, 325), (377, 305)],
                   (5, 10, 28, 255))
    canvas.line([(389, 319), (371, 346)], 8, (5, 10, 28, 255))
    canvas.line([(407, 316), (430, 340)], 8, (5, 10, 28, 255))
    canvas.line([(380, 286), (348, 300)], 7, (5, 10, 28, 255))
    canvas.line([(408, 282), (434, 264)], 7, (5, 10, 28, 255))
    canvas.line([(434, 264), (470, 199)], 1.5, (255, 247, 204, 240))


def foreground_sparks(canvas: Canvas) -> None:
    sparks = [
        (264, 420, 5, (255, 212, 67, 245)), (293, 381, 3, (255, 98, 193, 240)),
        (540, 391, 5, (55, 226, 255, 240)), (573, 452, 3, (192, 109, 255, 220)),
        (205, 525, 4, (255, 129, 88, 220)), (622, 533, 4, (255, 215, 74, 230)),
        (484, 181, 3, (97, 235, 255, 220)), (342, 194, 3, (255, 112, 204, 230)),
    ]
    for x, y, radius, color in sparks:
        canvas.disc(x, y, radius * 3, (color[0], color[1], color[2], 28))
        canvas.disc(x, y, radius, color)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


def write_png(canvas: Canvas, destination: Path) -> None:
    raw = bytearray()
    for y in range(canvas.height):
        raw.append(0)  # PNG filter type: none, explicit for straightforward validation.
        start = y * canvas.width * 4
        raw.extend(canvas.pixels[start:start + canvas.width * 4])
    compressed = zlib.compress(bytes(raw), level=9)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(png_chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)))
    png.extend(png_chunk(b"IDAT", compressed))
    png.extend(png_chunk(b"IEND", b""))
    destination.write_bytes(png)


def main() -> None:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("entry.png")
    canvas = Canvas(WIDTH, HEIGHT)
    background(canvas)
    starfield(canvas)
    energy_trails(canvas)
    horizon_ring(canvas)
    kite_and_burst(canvas)
    foreground_sparks(canvas)
    write_png(canvas, destination)
    print(f"wrote {destination} ({destination.stat().st_size} bytes, {WIDTH}x{HEIGHT} RGBA)")


if __name__ == "__main__":
    main()
