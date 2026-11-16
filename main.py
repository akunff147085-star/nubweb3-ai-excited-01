"""make.fun runtime entry: copy the prebuilt deterministic image."""
from __future__ import annotations

import os
import shutil
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "entry.png"
TARGET_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
TARGET = TARGET_DIR / "entry.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _validate_png(image: bytes) -> None:
    if not image.startswith(PNG_SIGNATURE):
        raise ValueError("packaged image does not have a PNG signature")

    offset = len(PNG_SIGNATURE)
    saw_header = False
    saw_end = False
    while offset < len(image):
        if len(image) - offset < 12:
            raise ValueError("packaged image has a truncated PNG chunk")

        length = struct.unpack_from(">I", image, offset)[0]
        chunk_start = offset + 4
        chunk_end = chunk_start + 4 + length + 4
        if chunk_end > len(image):
            raise ValueError("packaged image has a truncated PNG chunk")

        chunk_type = image[chunk_start:chunk_start + 4]
        chunk_data = image[chunk_start + 4:chunk_start + 4 + length]
        expected_crc = struct.unpack_from(">I", image, chunk_start + 4 + length)[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError("packaged image has an invalid PNG chunk checksum")

        if not saw_header:
            if chunk_type != b"IHDR" or length != 13:
                raise ValueError("packaged image has an invalid PNG header")
            saw_header = True
        elif chunk_type == b"IHDR":
            raise ValueError("packaged image has multiple PNG headers")

        if chunk_type == b"IEND":
            if length != 0:
                raise ValueError("packaged image has an invalid PNG end chunk")
            saw_end = True
            if chunk_end != len(image):
                raise ValueError("packaged image has data after the PNG end chunk")
            break

        offset = chunk_end

    if not saw_header or not saw_end:
        raise ValueError("packaged image is truncated")


def main() -> None:
    image = SOURCE.read_bytes()
    _validate_png(image)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, TARGET)


if __name__ == "__main__":
    main()
