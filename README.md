# Event Horizon Manta

An original vector-like cosmic manta bursts through a split neon aperture while carrying an impossible pearl moon in its wing. The composition is designed to read at thumbnail size: one hooked silhouette, a diagonal launch, a bright focal eye, and four converging wake ribbons.

[![make.fun bounty](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/c/ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/nubweb3-ai-excited-01/rank.svg)](https://make.fun/c/ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/nubweb3-ai-excited-01/reward.svg)](https://make.fun/c/ai-excited-01)

## Reproducible generation

The source generator uses only Python's standard library. It draws the image at 2x resolution with explicit polygons, line strokes, circles, glow layers, and a deterministic seeded starfield, then downsamples and writes a complete RGBA PNG.

```sh
python3 generator.py
sha256sum entry.png
```

The generated asset is deterministic and is included in the repository. The make.fun runtime is also standard-library-only and copies that asset to the requested output directory:

```sh
rm -rf out-a out-b
MAKEFUN_OUTPUT_DIR=out-a python3 main.py
MAKEFUN_OUTPUT_DIR=out-b python3 main.py
sha256sum out-a/entry.png out-b/entry.png
```

The runtime defaults to `/output/entry.png` when `MAKEFUN_OUTPUT_DIR` is unset. The image is 768x768 pixels and is kept below the 1 MiB competition limit.
