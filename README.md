# FM-1 NES firmware — source-only build

Experimental standalone NES player and USB CDC diagnostics for the M-VAVE FM-1
(Jieli WL82). This is an independent project, not an official vendor release.

Includes the current LCD, audio, digital volume, paced key scanner, per-channel
effects and Famicom-style key mapping. B/A use the highest F/G keys; directional
controls use the low keys. No game ROM or stock firmware is included.

## Requirements

The verified environment is Windows, Python 3.11, Git, CMake 3.20+, Visual Studio
2022 C++ build tools, and an **existing Jieli pi32v2 toolchain**. No pip packages
or new Python environment are needed. The toolchain is not redistributed or
installed by these scripts.

Two external source repositories must match these commits exactly:

| Dependency | Commit |
| --- | --- |
| [Jieli AC79/WL82 SDK](https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK) | `e30b1ee375d1f2993fc23bf92c8b99006a6e5f9d` |
| [PeakRacing NES core](https://github.com/PeakRacing/nes) | `68bdfc8de570264c0e84f73766f1a1ed3591066f` |

From this directory in PowerShell, use existing clean checkouts:

```powershell
$env:FM1_SDK_DIR = 'D:/dependencies/fw-AC79_AIoT_SDK'
$env:FM1_NES_CORE_DIR = 'D:/dependencies/peak-nes'
$env:FM1_TOOLCHAIN_DIR = 'C:/JL/pi32/bin'
python scripts/dependencies.py
python scripts/build.py host
python scripts/build.py firmware
```

Change those paths to your installation. If you do not already have the source
dependencies, leave the first two environment variables unset and explicitly run
`python scripts/dependencies.py --fetch`. This clones the pinned revisions into
ignored `.deps/` directories. It never replaces an existing checkout. Upstream
availability and a fresh network clone were not tested for this release; builds
were verified against existing clean checkouts at the stated revisions.

The default firmware build generates an original checkerboard/pulse/controller
diagnostic ROM from source. It needs neither a commercial ROM nor a stock dump.
Build outputs go under ignored `build/`.

To embed your own lawfully obtained ROM instead:

```powershell
$rom = (Resolve-Path 'D:/my-roms/diagnostic.nes').Path
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rom).Hash
python scripts/build.py firmware --rom $rom --rom-sha256 $hash
```

The ROM is checked against the supplied SHA-256 and its iNES structure before
embedding. Supported here: mapper 0 with 16/32 KiB PRG and 8 KiB CHR, or mapper 3
with 16/32 KiB PRG and 8/16/32 KiB CHR. NES 2.0, trainers, battery saves,
four-screen mirroring and CHR RAM are rejected. Higher mappers are not enabled.

Some internal identifiers (`rom50`, `smb1`, `--nes-smb1`) remain for compatibility
with reviewed code; they do not select, fetch or bundle a game. The public entry
point supplies the ROM explicitly and the serial identity is `NES=INES`.

## Outputs and limits

`build/firmware/fm1-usb-diag.app.bin` is the linked **application payload**, not a
complete 1 MiB flash image, vendor update package or ready-to-flash release.
The ELF, build manifest and `static-audit.json` accompany it. Entry instructions,
memory sections, power-init code, boot compatibility and embedded ROM are checked.
Audits still fail closed on an unexpected SDK layout or code change.

This source release intentionally omits the stock-image packager, vendor images,
recovery blobs and all PC-side flash/elevation tools. It does not reproduce or
distribute the device's bootloader/configuration regions. **Do not write the
application binary directly over the full flash.** Existing private recovery and
flash workflows are separate and unchanged. The clean diagnostic build has not
been flashed or hardware-qualified. Firmware CDC boot-entry support remains in
source; running a build does not contact the device.

## Source-only release

```powershell
python -m unittest discover -s tests -v
python scripts/release.py
```

This creates `dist/fm1-public-source.zip` using only exact paths in
`public-files.txt`, with a SHA-256 inventory. The restrictive `.gitignore` allows
only these reviewed source files. New files require an explicit update to both
lists. Neither mechanism removes a sensitive file already tracked in Git; this
copy starts without Git history.

**Publish the source archive, not a ZIP of the whole working directory.** Local
build results can embed your chosen ROM and contain machine-specific paths.
Excluded: ROM files/generated ROM C arrays, SDK/core checkouts, toolchain,
compiled firmware, flash backups, stock disassembly, session logs, device
identifiers, and elevated-session configuration. Packaging includes a limited
secret-pattern/binary check, not a guarantee against every possible disclosure.

See [THIRD_PARTY.md](THIRD_PARTY.md) for provenance and licensing boundaries and
[VALIDATION.md](VALIDATION.md) for the actual verification results.
