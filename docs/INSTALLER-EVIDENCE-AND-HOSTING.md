# Installer Verification Evidence, Packaging Boundaries & Source Hosting Plan

**Document**: `docs/third-party/INSTALLER-EVIDENCE-AND-HOSTING.md`  
**Status**: Engineering Specification & Verification Record  
**Target Release**: RaevusFlo Preview 0.1.13  
**Date**: October 13, 2026  

---

## 1. Verified Target Installer Evidence

### 1.1 Installer Binary Specifications
| Property | Value |
|---|---|
| **Executable Name** | `RaevusFlo-Preview-Setup-0.1.13.exe` (and identical `RaevusFlo-Preview-Setup.exe`) |
| **Directory** | `artifacts/Installer-Preview/` |
| **Byte Size** | `560,805,940 bytes` |
| **SHA-256 Hash** | `D9867EEB2395ACDDAB83BC1A10AED0FDCA99F11DE321810A376D6F8237FAFAA3` |
| **Internal Preview Version** | `0.1.13` |
| **Channel** | `internal-preview` |
| **Product Identifier** | `clipforge` (internal compatibility marker) / `RaevusFlo Preview` (UI & Windows display) |
| **Authenticode Status** | Explicitly unsigned development preview |

### 1.2 Verification Procedure (`scripts/Test-Installer.ps1`)
The automated verification script executes the built installer binary in a clean sandbox and verifies:
1. **Target Binary Verification**: Computes SHA-256 of the target installer (`RaevusFlo-Preview-Setup-0.1.13.exe`) before execution.
2. **Payload Completeness**: Installs silently into `$LOCALAPPDATA\Programs\Annekham Animations\ClipForge Preview` and verifies all 127 manifest entries against SHA-256 digests.
3. **Notices Deployment**: Confirms that all 31 third-party notice files are deployed to `$INSTDIR\notices\third-party` and match their source hashes.
4. **Embedded In-App Notices**: Rebuilt `RaevusFlo.exe` contains embedded resource `RaevusFlo.LicensingPrivacy` providing full LGPL-3.0 §4 reverse-engineering carveouts and notices.
5. **UI & Execution Check**: Launches installed `RaevusFlo.exe --ui-check`, rendering the UI to `interface.png`.
6. **Local Speech Inference Check**: Runs installed Whisper CLI on public speech fixture `jfk.wav` (`59DFB9A4...`), verifying accurate transcription of human speech locally.
7. **Clean Uninstallation**: Uninstalls via `Uninstall.exe /S`, verifying complete removal of executables, Start menu shortcut, and toast registrations while strictly preserving customer-owned files and encrypted licensing state.
8. **Directory Confinement**: Rejects nonempty unrecognized install directories with exit code 3.

---

## 2. Packaging Evidence Boundaries

### 2.1 Separation of Active Payload from Candidate Rebuild Sources
To prevent confusing active binary attribution with experimental rebuild candidates:
- **Active Installer Payload**:
  - Contains upstream vendor libraries (`libvosk.dll` SHA-256 `9EE0301E8C29...`, FFmpeg n8.1.3 LGPL shared binaries, active stream helper `yt-dlp.exe` SHA-256 `66674953FE...`).
  - Attributed via `artifacts/Installer-Preview/clipforge-preview-manifest.json` and 31 notices in `notices/third-party/`.
- **Candidate Rebuild Workspace (`artifacts/Compliance/vosk-rebuild-workspace/`)**:
  - Contains pinned rebuild recipes (`Dockerfile.vosk-candidate`, `scripts/Build-VoskCandidate.py`).
  - Staged source archives in `artifacts/Compliance/sources/` for prospective compilation.
  - Candidate sources and container recipes are **strictly isolated** and do NOT modify active application binaries or active installer attribution.

---

## 3. Source Distribution Package Architecture

### 3.1 Self-Contained Source Bundle
- **Archive File**: `artifacts/Compliance/RaevusFlo-0.1.13-third-party-sources.zip`
- **Size**: `1,417,053,351 bytes` (~1,351.4 MB)
- **Total Entries**: 720 (700 source tarballs/crates + 4 recipes + 4 BtbN patches + 10 licenses + `MANIFEST.json`)
- **Self-Contained Verification**: Tested via `scripts/Test-SourceArchiveBundle.py` in an isolated temp directory without network access or original workspace access:
  - 100% of 700 archives streamed and verified against SHA-256 digests.
  - Zero absolute paths, zero machine-specific references, zero path traversal.
  - `MANIFEST.json` explicitly references target installer `RaevusFlo-Preview-Setup-0.1.13.exe` (SHA-256 `D9867EEB...`).
- **Clear Status**: Explicitly labeled `INCOMPLETE_NOT_CLEARED_FOR_COMMERCIAL_DISTRIBUTION` until legal counsel approves LGPLv3 §4 source superset sufficiency.

---

## 4. Hosting Specification & Verification Workflow

### 4.1 Primary Hosting Option: GitHub Releases (Free Tier)
- **Target Repository**: Owner repository (recommended name: `raevusflo-third-party-sources`).
- **Asset Size Limit**: GitHub Releases supports **2 GB per file** (official limit). The 1.35 GB archive fits comfortably within the free tier.
- **Cost**: **$0.00** (free public repository storage and egress).
- **Release Layout**:
  - Release Tag: `v0.1.13-sources`
  - Release Title: `RaevusFlo 0.1.13 Third-Party Source Distribution (Provisional)`
  - Primary Asset: `RaevusFlo-0.1.13-third-party-sources.zip` (1.35 GB)
  - Detached Checksum: `RaevusFlo-0.1.13-third-party-sources.zip.sha256`
  - Release Notes: Transcludes `README-SOURCE-OFFER-DRAFT.md` with explicit disclaimer and instructions.

### 4.2 End-User Authenticity & Download Verification
Users can verify package authenticity using standard operating system utilities:
```powershell
# 1. Download bundle and detached hash from official release tag
curl.exe -L -O https://github.com/[OWNER]/raevusflo-third-party-sources/releases/download/v0.1.13-sources/RaevusFlo-0.1.13-third-party-sources.zip
curl.exe -L -O https://github.com/[OWNER]/raevusflo-third-party-sources/releases/download/v0.1.13-sources/RaevusFlo-0.1.13-third-party-sources.zip.sha256

# 2. Verify SHA-256 checksum
certutil -hashfile RaevusFlo-0.1.13-third-party-sources.zip SHA256
```

### 4.3 Redundancy, Retention & Host Failure Recovery
1. **Offline Master Copy**: Retained permanently in local archival storage (`artifacts/Compliance/`).
2. **Secondary Redundancy Mirror**: Internet Archive item uploaded as secondary backup once public repository is approved.
3. **Domain Redirection**: Official source URL `https://annekham.test/sources/0.1.13` redirects to the active release asset, allowing instant target URL reconfiguration without modifying published application binaries if GitHub changes hosting policies.
4. **Direct Fulfillment Fallback**: Requests submitted to `compliance@annekham.test` will be fulfilled directly via cloud storage download link or physical optical/USB media.

---

## 5. Commercial Guards & Active Scope Preservation

All commercial release guards remain strictly fail-closed:
- `completeCorrespondingSource: false` (pending counsel review of Category B/C gaps).
- `supportedResolverRuntime: false` (staged candidate remains isolated; active helper preserved).
- `approvedDistributionTerms: false` (draft terms pending qualified legal review).
- `sourceHostingVerified: false` (publication pending owner repository setup).
- **Live-stream support remains Beta / Experimental** (not a launch acceptance baseline).
- Active stream helper `.tools/stream/yt-dlp.exe` (`66674953FE...`) remains active and untouched.
