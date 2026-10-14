# RaevusFlo Third-Party Source Rebuild Recipes

This repository contains standalone, redistributable build recipes, source manifests, and CI workflows for third-party native libraries used by RaevusFlo.

## Contents
- `.github/workflows/build-vosk-candidate.yml`: GitHub Actions workflow for containerized MinGW cross-compilation on free `ubuntu-latest` runners.
- `recipes/vosk/`:
  - `Dockerfile`: Pinned Debian 12 Bookworm container definition (`debian:12-slim@sha256:a4672c0cb26fbdde88e38fa2dfb6c681942306680e41e4378b28770b6e79ee91`).
  - `sources.json`: Immutable Git commit refs and SHA-256 digests for OpenFST, OpenBLAS, CLAPACK, Kaldi, and Vosk-API.
  - `download-sources.py`: Self-contained script to download and verify all source tarballs.
- `scripts/Test-VoskCandidate.py`: Standalone validation harness to verify PE architecture, export symbols, import tables, and speech fixtures.
- `docs/`: Technical specifications, build report receipts, and installer evidence bounds.

## Triggering Candidate Build
1. In the GitHub web UI, navigate to **Actions** -> **Build Vosk Candidate**.
2. Click **Run workflow**.
3. Upon completion, download the `vosk-candidate-win64` artifact containing `libvosk.dll`, MinGW runtime DLLs, build logs, and `SHA256SUMS.txt`.

## License & Attribution
All recipes, manifests, and documentation in this repository are dedicated to the public domain or licensed under Apache-2.0 / MIT. Individual upstream components are governed by their respective open-source licenses (Apache-2.0, BSD-3-Clause, GPLv3 with GCC Runtime Library Exception 3.1).
