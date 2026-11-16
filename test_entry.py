"""Offline reproducibility and malformed-PNG integration checks (stdlib only)."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

import main

ROOT = Path(__file__).resolve().parent


def chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff))


def tiny(raw=b'\0\xff\x80\0\xff', compressed=None):
    header = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)
    return (main.PNG_SIGNATURE + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(raw) if compressed is None else compressed)
            + chunk(b'IEND', b''))


class EntryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'out').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'out')
        self.work = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def run_entry(self, package, output):
        return subprocess.run([sys.executable, '-I', str(package / 'main.py')],
                              cwd=self.work, capture_output=True, text=True,
                              env={**os.environ, 'MAKEFUN_OUTPUT_DIR': str(output)})

    def test_generation_and_runtime_reproducibility(self):
        packaged = (ROOT / 'entry.png').read_bytes()
        self.assertEqual(main.validate_png(packaged), (768, 768))
        self.assertLess(len(packaged), 1048576)
        for index in range(2):
            generated = self.work / f'generated-{index}.png'
            subprocess.run([sys.executable, '-I', str(ROOT / 'generator.py'),
                            str(generated)], check=True, capture_output=True)
            self.assertEqual(generated.read_bytes(), packaged)
            output = self.work / f'run-{index}'
            result = self.run_entry(ROOT, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((output / 'entry.png').read_bytes(), packaged)
        print(f'\nRGBA 768x768; {len(packaged)} bytes; SHA-256 '
              f'{hashlib.sha256(packaged).hexdigest()}; two generators + two runtimes identical')

    def test_malformed_isolated_packages_do_not_write(self):
        valid = tiny()
        compressed = zlib.compress(b'\0\xff\x80\0\xff')
        cases = {
            'signature': b'not a PNG',
            'truncated-header': valid[:20],
            'truncated-data': valid[:-17],
            'missing-end': valid[:-12],
            'bad-crc': valid[:40] + bytes([valid[40] ^ 1]) + valid[41:],
            'trailing-bytes': valid + b'junk',
            'ancillary-before-header': valid[:8] + chunk(b'tEXt', b'x\0y') + valid[8:],
            'duplicate-header': valid[:33] + valid[8:33] + valid[33:],
            'bad-filter': tiny(b'\5\xff\x80\0\xff'),
            'short-pixels': tiny(b'\0\xff'),
            'extra-pixels': tiny(b'\0\xff\x80\0\xff\0'),
            'truncated-zlib': tiny(compressed=compressed[:-1]),
            'extra-zlib': tiny(compressed=compressed + compressed),
            'expansion-overrun': tiny(b'\0' * 1000000),
            'unsupported-chunk': valid[:33] + chunk(b'abcd', b'') + valid[33:],
            'oversized-file': b'\0' * (1048576 + 1),
        }
        package = self.work / 'package'
        package.mkdir()
        shutil.copyfile(ROOT / 'main.py', package / 'main.py')
        for name, data in cases.items():
            with self.subTest(name=name):
                (package / 'entry.png').write_bytes(data)
                output = self.work / name
                result = self.run_entry(package, output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('invalid PNG:', result.stderr)
                self.assertFalse(output.exists(), 'invalid image created an output directory')
        print(f'\n{len(cases)} isolated malformed packages rejected without output')

    def test_minimal_valid_stream(self):
        self.assertEqual(main.validate_png(tiny()), (1, 1))
        for filter_type in range(5):
            self.assertEqual(main.validate_png(tiny(bytes([filter_type, 1, 2, 3, 255]))), (1, 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
