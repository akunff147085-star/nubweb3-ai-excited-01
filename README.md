# Event Horizon Kite

[![ai-excited-01](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/c/ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/akunff147085-star/nubweb3-ai-excited-01/rank.svg)](https://make.fun/c/ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/akunff147085-star/nubweb3-ai-excited-01/reward.svg)](https://make.fun/c/ai-excited-01)

A deterministic standard-library illustration of a tiny rider launching a luminous kite through a broken event horizon. The hard-edged silhouette gives the image a readable center at thumbnail size; layered cyan, magenta, and solar-gold trails create the sense that the launch is still accelerating.

## Reproduce the image

Python 3.13 or newer is sufficient. The generator uses no packages or network resources.

```sh
python3 generator.py entry.png
sha256sum entry.png
file entry.png
```

The generator writes the same RGBA PNG bytes every time. It defaults to `entry.png` when no destination is supplied.

## Run the competition entry

```sh
rm -rf out
mkdir -p out
MAKEFUN_OUTPUT_DIR=out python3 main.py
cmp entry.png out/entry.png
```

`main.py` validates the complete packaged PNG, including its signature, chunk lengths, CRCs, ordering, zlib stream, decoded size, and scanline filters, before copying it. It intentionally accepts only the generator's minimal 8-bit RGBA, non-interlaced IHDR/IDAT/IEND profile, and bounds input and decompression sizes. The output directory defaults to `/output` when `MAKEFUN_OUTPUT_DIR` is unset.

## Verification

```sh
python3 -m unittest -v test_entry
python3 -m py_compile main.py generator.py test_entry.py
```

The suite runs the generator twice and the packaged runtime twice, compares every output byte, and exercises 16 malformed images in isolated temporary packages under ignored `out/`. Rejected images must create no output directory. It also checks a valid minimal image and all five legal scanline filters.

The final packaged asset is 768×768, RGBA, 175,215 bytes. Its SHA-256 is `c9a0304a7a0a49341daf5ac503b13e2d7a55759d327f4209328bbd0313558a77`.

Local tests ran with Python 3.14.9; Python 3.13 was not installed in the build environment. The runtime and generator use only standard-library APIs available in Python 3.13. No image downloads, model-generated assets, or external packages are required.

To check the committed repository with the downloaded kit, without loading a stored make.fun account:

```sh
mkdir -p out/kit-tmp
TMPDIR="$PWD/out/kit-tmp" node /home/ubuntu/makefun-excited/kit/ai-excited-01-kit/cli/makefun.mjs check --kit /home/ubuntu/makefun-excited/kit/ai-excited-01-kit --repo "$PWD" --origin https://make.fun --api-key offline-local-check
```

The explicit placeholder key prevents credential lookup; this competition's local check requires no network request. This does not submit or judge the image, or verify the server's recording gate.

## License

The repository is distributed under the MIT License in `LICENSE`.
