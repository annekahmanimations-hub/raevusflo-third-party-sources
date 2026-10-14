# Controlled Rebuild Specification & Dependency Gap Taxonomy

**Document**: `docs/third-party/CONTROLLED-REBUILD-SPEC.md`  
**Status**: Engineering Specification & Taxonomy  
**Date**: October 13, 2026  
**Target Application**: RaevusFlo v0.1.13  

---

## 1. Gap Taxonomy: Engineering Gaps vs. Legal Questions

To prevent conflating engineering tasks with statutory or legal evaluations, the remaining clearance items for third-party native dependencies (FFmpeg, Vosk, and the Stream Resolver) are categorized into four distinct domains:

```
+-----------------------------------------------------------------------------------------+
|                                    CLEARANCE DOMAINS                                    |
+-----------------------------+-----------------------------+-----------------------------+
|   A. TECHNICAL EVIDENCE     |    B. SOURCE/BUILD INPUTS   |    C. LEGAL INTERPRETATION  |
|  - Historical BuildKit 404  |  - Exact Debian apt pins    |  - GPLv3 §1 System Library  |
|  - Kaldi rebase commit gap  |  - CT_VERSION ambiguity     |  - GCC Exception 3.1 scope  |
|  - Historical CI log expiry |  - rav1e cc lock update     |  - MPEG-LA / Via patent pool|
+-----------------------------+-----------------------------+-----------------------------+
                              \                             /
                               v                           v
                              +-----------------------------+
                              | D. REPRODUCIBILITY PATHS    |
                              | - Pinned Docker Rebuild     |
                              | - Known-Source Construction |
                              | - ABI & Functional Matching |
                              +-----------------------------+
```

### Category A: Missing Technical Evidence (Historical Provenance Artifacts)
These represent artifacts, logs, or cache metadata from upstream third-party CI systems that were either lost, expired, or returned HTTP 404:
1. **FFmpeg BuildKit Cache Manifest (404)**: Upstream registry returned 404 for the intermediate Docker BuildKit cache layer manifest from October 4, 2026 (`FFMPEG-HISTORICAL-IMAGE-METADATA.json`).
2. **Vosk Kaldi-Win Release Tag Endpoint (404)**: The historical release URL referenced in the Vosk build script for `alphacep/kaldi-win` is no longer reachable (`VOSK-PUBLIC-IMAGE-AVAILABILITY.json`).
3. **Vosk API Build-Time Checkout**: `vosk-api` build script executed an unpinned Git clone during native wheel compilation, leaving the exact build-time commit to be inferred from the release tag `v0.3.38` (`f73088d`).

*Engineering Assessment*: Historical evidence cannot be created retroactively if upstream servers have deleted it. These gaps can only be closed either by (1) accepting established inferences supported by binary matching, or (2) executing a controlled rebuild from known sources (Category D).

---

### Category B: Missing Source & Build Inputs (Toolchain Ambiguities)
These represent gaps in the exact source inputs used during upstream compilation:
1. **Debian/Ubuntu Package Version Pins**: The historical container environments (`base-win64` digest `f27c68d...`) ran unpinned `apt-get install` commands at container construction time.
2. **crosstool-ng Commit Ambiguity**: The compiler image log recorded `CT_VERSION=1.29.0.7_b1a94f6`. Git tree search identified two candidates: configuration seed `b1a94f65c5...` vs default-branch HEAD `f697d16bd7...`. Both candidates are preserved in the 700 staged archives (`artifacts/Compliance/sources/`).
3. **rav1e `cargo update cc` Resolution**: The rav1e build recipe invoked `cargo update cc`, advancing `cc` from `1.2.26` to `1.6.0`. While both crate archives and downstream dependencies (`find-msvc-tools`, `shlex`) have been collected and verified against registry checksums, the final Cargo.lock was ephemeral.

*Engineering Assessment*: While the 700 staged archives provide a comprehensive source superset containing all referenced versions, byte-for-byte binary reconstruction of the historical binary is impossible without identical timestamps, compiler flags, and toolchain binaries.

---

### Category C: Legal & License Condition Questions (Counsel Review)
These represent questions of statutory interpretation and licensing condition fulfillment that belong strictly to qualified IP legal counsel:
1. **GPLv3 §1 "System Library" Classification for Microsoft CRT/UCRT**:
   - *Technical Fact*: The application bundle and resolver candidate include 45 Microsoft CRT and Universal CRT DLLs (`vcruntime140.dll`, `api-ms-win-crt-*.dll`).
   - *Question for Counsel*: Confirm that these DLLs satisfy the definition of "System Library" under GPLv3 §1 ("normally accompanies the major components of the operating system"), or are redistributable under Microsoft Visual Studio 2022 Redistributable EULA terms without requiring MS CRT source distribution.
2. **GCC Runtime Library Exception 3.1 Eligibility**:
   - *Technical Fact*: Vosk native binaries ship MinGW runtime libraries (`libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll`).
   - *Question for Counsel*: Confirm whether standard binary redistribution under GCC Runtime Library Exception 3.1 is effective when the compiler used was standard Debian MinGW, without distributing the full GCC compiler source suite.
3. **Patent Pool Licensing (MPEG-LA / Via Licensing Alliance)**:
   - *Technical Fact*: RaevusFlo utilizes Windows hardware encoders via `ScreenRecorderLib` and FFmpeg for MP4 demuxing/remuxing (H.264/AAC).
   - *Question for Counsel*: Assess commercial exposure regarding MPEG-LA / Via AVC/H.264 and AAC patent pool licenses for end-user distribution.
4. **Sufficiency of Source Superset vs. Bit-Identical Reconstruction**:
   - *Technical Fact*: 700 source archives provide all source code, patches, and build scripts.
   - *Question for Counsel*: Confirm whether LGPLv3 §4 / GPLv3 §6 is satisfied by providing the complete corresponding source superset and recipes, even if compiler toolchain seed differences preclude bit-identical re-compilation.

---

### Category D: Reproducibility Improvements (Controlled Rebuild Path)
If legal counsel determines that Category B toolchain ambiguities or Category A missing receipts prevent commercial clearance of the upstream vendor binaries, engineering can eliminate all ambiguity by executing a **Controlled Rebuild**.

Below are the exact specifications for controlled container builds.

---

## 2. FFmpeg Controlled Rebuild Specification

### 2.1 Rebuild Objectives
- Build an LGPL-3.0 shared library set (`avcodec-61.dll`, `avformat-61.dll`, `avutil-59.dll`, `swresample-5.dll`, `swscale-8.dll`, `ffmpeg.exe`, `ffprobe.exe`).
- Strictly enforce `version3` enabled, `gpl` disabled, `nonfree` disabled.
- Pinned toolchain, pinned source archives, and deterministic build recipes.

### 2.2 Container Environment
- **Base Image**: `docker.io/library/debian:12.7-slim@sha256:d5598e3b4a20b7...` (pinned immutable Debian Bookworm).
- **Cross-Compiler**: `x86_64-w64-mingw32-gcc` (MinGW-w64 v10.0 / GCC 12.2).
- **Rust Toolchain**: `rustup` pinned to `1.81.0-x86_64-unknown-linux-gnu` with target `x86_64-pc-windows-gnu`.
- **NASM**: `2.16.01` pinned Debian package.

### 2.3 Input Sources & Configuration Flags
- **FFmpeg Source**: Tarball of commit `330caae0c1acccd2222edc52a05940c574561ce5` (FFmpeg n8.1.3).
- **Configuration Flags**:
  ```bash
  ./configure \
    --prefix=/build/dist \
    --target-os=mingw32 \
    --arch=x86_64 \
    --cross-prefix=x86_64-w64-mingw32- \
    --enable-shared \
    --disable-static \
    --enable-version3 \
    --disable-gpl \
    --disable-nonfree \
    --enable-pic \
    --enable-w32threads \
    --disable-debug \
    --enable-zlib \
    --enable-libopus \
    --enable-libdav1d \
    --enable-libvpx \
    --enable-librsvg \
    --enable-librav1e
  ```
- **Dependencies**: All external static library dependencies built strictly from the staged source archives in `artifacts/Compliance/sources/`.

### 2.4 Acceptance Criteria
1. Binary PE export inspection confirms all 65 export symbols required by RaevusFlo / ScreenRecorderLib / NAudio are present.
2. Binary imports link against MSVCRT / UCRT and Win32 subsystem libraries without introducing non-whitelisted dependencies.
3. Functional verification passes:
   - Video container demuxing and trimming (`Trim_Click` pipeline).
   - Audio extraction to WAV for Whisper transcription (`Test-WhisperCaptions.ps1`).
   - MP4 export rendering with audio synchronization.

---

## 3. Vosk Native Controlled Rebuild Specification

### 3.1 Rebuild Objectives
- Produce clean, fully traceable builds of `libvosk.dll`, `libwinpthread-1.dll`, `libgcc_s_seh-1.dll`, and `libstdc++-6.dll`.
- Eliminate the historical unpinned Git clone and 404 endpoint ambiguities.

### 3.2 Pinned Git Revisions & Input Tarballs
All components are strictly permissive (Apache-2.0 or BSD-3-Clause):
| Component | Pinned Revision / Tag | Declared License | Source Archive |
|---|---|---|---|
| **Vosk API** | `f73088da5840f9a382eb949f65cbfeaef901e983` (tag `v0.3.38`) | Apache-2.0 | `vosk-api-f73088d.tar.gz` |
| **OpenFST** | `7dfd808194105162f20084bb4d8e4ee4b65266d5` (historical HEAD) | Apache-2.0 | `openfst-7dfd808.tar.gz` |
| **CLAPACK** | `931173de8032c9dbb588f82b58b66a57fce830eb` (v3.2.1 branch tip) | BSD-3-Clause | `clapack-931173d.tar.gz` |
| **Kaldi** | `alphacep/kaldi` pinned fork commit matching Vosk 0.3.38 | Apache-2.0 | `kaldi-alphacep-pinned.tar.gz` |
| **OpenBLAS** | `v0.3.20` release archive | BSD-3-Clause | `openblas-0.3.20.tar.gz` |

### 3.3 Build Recipe (MinGW Cross-Compilation)
```bash
# 1. OpenFST
cd /build/openfst
./configure --host=x86_64-w64-mingw32 --prefix=/build/target --enable-static --disable-shared
make -j$(nproc) && make install

# 2. OpenBLAS & CLAPACK
cd /build/clapack && make f2clib && make blaslib
cd /build/openblas && make HOSTCC=gcc CC=x86_64-w64-mingw32-gcc TARGET=NEHALEM ONLY_CBLAS=1
make PREFIX=/build/target install

# 3. Kaldi
cd /build/kaldi/src
./configure --fst-root=/build/target --blac-root=/build/target --host=x86_64-w64-mingw32 --static
make -j$(nproc)

# 4. LibVosk
cd /build/vosk-api/src
KALDI_ROOT=/build/kaldi OPENFST_ROOT=/build/target OPENBLAS_ROOT=/build/target \
  make -j$(nproc) EXTRA_CFLAGS="-O3 -fPIC"
x86_64-w64-mingw32-g++ -shared -o /build/dist/libvosk.dll *.o \
  -L/build/target/lib -L/build/kaldi/src/lib -lkaldi-online2 -lkaldi-lat -lkaldi-decoder -lkaldi-feat -lkaldi-transform -lkaldi-gmm -lkaldi-hmm -lkaldi-tree -lkaldi-matrix -lkaldi-util -lkaldi-base -lfst -lopenblas -lwinpthread
```

### 3.4 Acceptance Criteria
1. `libvosk.dll` exports `vosk_model_new`, `vosk_recognizer_new`, `vosk_recognizer_accept_waveform`, `vosk_recognizer_result`, `vosk_recognizer_free`.
2. Existing small-en-us-0.15 and en-us-0.22 models load and transcribe audio correctly.
3. Transcribes `jfk.wav` human speech test fixture with matching token output (`Test-WhisperCaptions.ps1` fallback check).

---

## 4. Engineering Action Matrix vs. Milestone Roadmap

| Milestone | Action | Engineering Prerequisite | Legal / Business Prerequisite |
|---|---|---|---|
| **Current State** | Maintain 700 staged source archives, isolated candidate resolver, draft terms | Completed | Prelaunch review |
| **Pre-Commercial Gate 1** | Decide between Upstream Source Superset vs. Controlled Rebuild | Controlled Rebuild Container prepared | Legal opinion on LGPLv3 §4 source superset sufficiency |
| **Pre-Commercial Gate 2** | Finalize Third-Party EULA & Reverse Engineering terms | Terms draft integrated locally (`licenses.html`, installer) | Counsel sign-off on terms and patent pool risk |
| **Pre-Commercial Gate 3** | Deploy Public Source Hosting Package | Versioned ZIP bundle assembled (`RaevusFlo-0.1.13-third-party-sources.zip`) | Owner repository designated (GitHub Releases 2GB free tier) |
| **Pre-Commercial Gate 4** | Resolver Active Integration (if promoted from Beta) | Isolated compatibility tests passed | Approval to run active helper replacement & recording test |

---
