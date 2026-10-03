# ROMs for the NES example

An NES **`.nes` cartridge** is game data read by the emulator. FM-1 **`app.bin`**
is the linked WL82 application, including the selected cartridge and SDK runtime.
Changing games requires rebuilding and installing the application; there is no
independent ROM upload slot or live cartridge-loading command in this example.
Nothing in these build commands contacts your device.

## Start with the original diagnostic

Configure the existing pinned SDK/core/compiler as described in README.md, then:

```powershell
python scripts/build.py firmware --diagnostic --usb-audio --package build/diagnostic-v1.fm1app
```

`--diagnostic` ignores a private local default and generates the original
checkerboard/controller/pulse cartridge from source. The continuous pulse is
intentional, not game music or proof of an audio fault. Omit `--usb-audio` for
CDC-only. Use fresh package names; existing packages are not overwritten.

## Supported cartridge formats

The embedder validates the actual iNES header and length before linking:

| Feature | Accepted |
| --- | --- |
| Format | Bounded NTSC iNES 1, with zero bytes 8..15 |
| Mapper 0 / NROM | 16 or 32 KiB PRG, exactly 8 KiB CHR ROM |
| Mapper 3 / CNROM | 16 or 32 KiB PRG, 8 / 16 / 32 KiB CHR ROM |
| Unsupported | Mapper 4/MMC3 and other higher mappers, NES 2.0, trainers, battery/save RAM, four-screen mirroring, CHR RAM |

A filename does not determine compatibility. Do not change the mapper byte to
make an unsupported cartridge pass: its code still requires that mapper's
hardware. A separate genuine NROM edition is needed for an MMC3 game.
Passing header validation is not a promise of full game compatibility or speed.

## Maintainer-created game: ぼくがかんがえたさいきょうのファミコンゲーム

The local Claude Code-assisted project has two editions: `game_nrom.nes`
(mapper 0, 32 KiB PRG + 8 KiB CHR ROM) and `game.nes` (mapper 4/MMC3).
Use **`game_nrom.nes`**, not the MMC3 edition, with this firmware.
The reviewed local NROM file is 40976 bytes and passes this project's cartridge
validator; its SHA-256 is
`8dbe33a3f00d76d88c4618917833f3a9dbb198b2de3ee684a4c59a2cc4bdc687`.
This is a format check, not FM-1 gameplay acceptance. Recompute the hash for
your build; do not assume a later game revision has identical bytes.

The maintainer identified this game as their own and explicitly authorized its
source and generated original assets on 2026-10-03, then selected **MIT**.
The optional [NROM source example](examples/fablenes/README.md) is included;
compiled game/firmware files are not. Build it with existing Python and external
cc65 tools, then embed it using the explicit path/hash instructions below.
The example has its own copyable build commands. Do not substitute the separately
linked third-party game repository or assume its public availability grants
redistribution rights. The original local project stays unchanged.

## Use your own cartridge

Use your own original/homebrew ROM or another file you are authorized to use.
This project supplies no commercial game downloads or dumping instructions.
Public availability or AI-assisted creation is not by itself a license for
third-party code, fonts, artwork or music; retain applicable asset notices.

From the FM-1 repository root in PowerShell:

```powershell
$rom = (Resolve-Path 'D:/my-roms/my-homebrew.nes').Path
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rom).Hash.ToLowerInvariant()
python scripts/build.py firmware --usb-audio --rom $rom --rom-sha256 $hash --out build/my-homebrew --package build/my-homebrew-v1.fm1app
```

The build checks the expected SHA-256, validates the cartridge, links the full
application, runs the target static audit, then creates the application-only
package. Outputs include `fm1-usb-diag.app.bin`, the ELF and matching audit under
`build/my-homebrew/`. The package contains only `app.bin` and `manifest.json`;
it does not include the installed stock bootloader or a full NOR image.

Do not commit generated cartridges, ROM C arrays, firmware or `.fm1app` files.
The source-only release guards exclude them even when your own game is licensed
for redistribution. Binary publication requires its own dependency/asset review.

## Optional private default

Create ignored `local/rom.json` with exactly these two fields (example only):

```json
{
  "rom": "D:/my-roms/my-homebrew.nes",
  "sha256": "REPLACE_WITH_THE_64_HEX_DIGIT_SHA256"
}
```

Paths may be absolute or relative to the configuration's directory. Subsequent
`python scripts/build.py firmware --usb-audio ...` uses that cartridge. Explicit
`--rom` plus `--rom-sha256` overrides it; `--diagnostic` ignores it. A missing or
invalid configured file fails instead of silently selecting the diagnostic.
The configuration and commercial/private cartridge remain outside Git.

## Install the rebuilt application, not the .nes file

Follow [APP_UPDATES.md](APP_UPDATES.md) for recovery, the external pinned Jieli
tool/guard patch, private backup and offline sparse plan, explicit flash and
reset. The validated application starts at **physical flash `0x4120`**, with CPU
entry **`0x02000120`**. Required app metadata at `0x4000`/`0x4020` is updated;
boot/config/reserved regions and shared sector bytes are preserved.

Do not write either `.nes` or raw `app.bin` directly at that address. Encoding,
size/CRC records, layout/hash validation and erase-sector preservation matter.
Keep the whole device-derived plan and backup private. V14 bench results and
the standalone wrapper's remaining qualification limits are in VALIDATION.md.
