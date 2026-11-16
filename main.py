#!/usr/bin/env python3
"""Validate and copy the packaged deterministic competition image."""

from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_FILE_SIZE = 1 << 20
MAX_DIMENSION = 1024


class PngError(ValueError):
    """Raised when the packaged PNG is incomplete or structurally invalid."""


def _fail(message: str) -> PngError:
    return PngError(f"invalid PNG: {message}")


def validate_png(data: bytes) -> tuple[int, int]:
    """Validate the complete PNG byte stream and return (width, height)."""
    if len(data) > MAX_FILE_SIZE:
        raise _fail("file exceeds 1 MiB")
    if len(data) < len(PNG_SIGNATURE) or data[:8] != PNG_SIGNATURE:
        raise _fail("bad signature")

    position = 8
    seen_ihdr = False
    seen_idat = False
    seen_iend = False

    idat_parts: list[bytes] = []
    width = height = 0

    while position < len(data):
        if len(data) - position < 12:
            raise _fail("truncated chunk header")
        length = struct.unpack(">I", data[position:position + 4])[0]
        chunk_start = position
        position += 4
        chunk_type = data[position:position + 4]
        position += 4
        if any(not (65 <= byte <= 90 or 97 <= byte <= 122) for byte in chunk_type):
            raise _fail("invalid chunk type")
        if length > len(data) - position - 4:
            raise _fail("truncated chunk payload")
        payload = data[position:position + length]
        position += length
        checksum = struct.unpack(">I", data[position:position + 4])[0]
        position += 4
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != checksum:
            raise _fail(f"CRC mismatch in {chunk_type.decode('ascii')}")

        if seen_iend:
            raise _fail("data after IEND")
        if not seen_ihdr and chunk_type != b"IHDR":
            raise _fail("IHDR must be the first chunk")
        if chunk_type == b"IHDR":
            if seen_ihdr or length != 13 or chunk_start != 8:
                raise _fail("invalid IHDR placement or length")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if not width or not height or width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise _fail("dimensions outside allowed range")
            if (bit_depth, color_type, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise _fail("only 8-bit RGBA non-interlaced PNGs are supported")
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            if not seen_ihdr or seen_iend:
                raise _fail("IDAT is out of order")
            seen_idat = True
            idat_parts.append(payload)
        elif chunk_type == b"IEND":
            if not seen_ihdr or not seen_idat or length != 0:
                raise _fail("invalid IEND")
            seen_iend = True
            if position != len(data):
                raise _fail("trailing bytes after IEND")
        else:
            # Restrict the asset to the generator's minimal PNG profile.
            raise _fail(f"unsupported chunk {chunk_type.decode('ascii')}")

    if not seen_ihdr or not seen_idat or not seen_iend:
        raise _fail("missing required chunk")

    compressed = b"".join(idat_parts)
    row_bytes = width * 4
    expected_size = height * (row_bytes + 1)
    decompressor = zlib.decompressobj()
    try:
        raw = decompressor.decompress(compressed, expected_size + 1)
    except zlib.error as error:
        raise _fail(f"image stream cannot be decompressed: {error}") from error
    if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
        raise _fail("incomplete or concatenated image stream")

    if len(raw) != expected_size:
        raise _fail("decompressed data length does not match IHDR")
    for row in range(height):
        filter_type = raw[row * (row_bytes + 1)]
        if filter_type > 4:
            raise _fail(f"invalid scanline filter at row {row}")
    return width, height


def main() -> None:
    package = Path(__file__).resolve().with_name("entry.png")
    with package.open("rb") as source:
        data = source.read(MAX_FILE_SIZE + 1)
    width, height = validate_png(data)
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "entry.png").write_bytes(data)
    print(f"copied {package} -> {output_dir / 'entry.png'} ({width}x{height}, {len(data)} bytes)")


if __name__ == "__main__":
    main()
