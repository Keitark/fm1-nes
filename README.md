# Custom firmware development for the M-VAVE FM-1

[![Status: experimental](https://img.shields.io/badge/status-experimental-orange)](VALIDATION.md)
[![Licenses: mixed](https://img.shields.io/badge/licenses-Apache--2.0%20%2B%20GPLv3-blue)](THIRD_PARTY.md)

This repository shares resources, board-support code and a worked example of
**how to develop custom firmware for the FM-1**, based on the Jieli WL82. The
goal is to make the hardware accessible for experiments with synthesizers,
instruments, effects and other applications—not to turn the FM-1 into an NES box.

The NES player is an example that exercises the display, audio, keys, knobs and
real-time scheduling together. Use it as a reference, or replace it with your own
application. This is an independent, experimental project, not an official
M-VAVE or Jieli release. No commercial game ROM or stock firmware is included.

## Playing NES: controls

The current NES example maps the FM-1's 27 note keys directly to NES controller 1.
The note names below refer to the **physical key positions from left to right**
(lowest F through highest G); synth octave/transpose settings do not change this mapping.

| NES control | FM-1 key |
| --- | --- |
| D-pad Left | Lowest F |
| D-pad Down | First G |
| D-pad Up | First G# |
| D-pad Right | First A |
| Select | First A# |
| Start | First C# |
| B | Highest F |
| A | Highest G |

This is the mapping implemented by the current firmware example.

## Application-only programming: tested on V14

**Build the complete application; update only its changed flash sectors.**
The `.fm1app` package contains exactly `app.bin` and `manifest.json`, **not the
stock bootloader**. Keep the working bootloader already installed on your FM-1.
The source export neither rebuilds nor distributes that loader.

| Address / artifact | Meaning |
| --- | --- |
| Physical flash `0x0000..0x3FFF` | Existing boot/header/config; preserved, never written by this scheme |
| Physical flash `0x4000`, record `0x4020` | Application directory/header; required size/CRC metadata updated |
| Physical flash **`0x4120`** | Start of the installed application payload, after the `0x120`-byte directory prefix |
| CPU address **`0x02000120`** | Application entry address; **not** a flash write offset |
| `.fm1app` | Application and sanitized manifest only |
| Owner backup / sector plan | Private unit-derived data; never publish these |

Do **not** issue a raw write of `app.bin` at `0x4120`: the planner must validate
the installed layout, encode the application, update metadata and preserve
shared erase-sector bytes. Only reviewed layouts/boot hashes are accepted;
the version label alone does not establish compatibility.

On **2026-10-03**, the app-only scheme was tested on the maintainer's FM-1
with an installed **V14** baseline: **51 changed 4 KiB sectors**, directory last,
and **one complete final readback** matched. Bootloader/configuration/reserved
regions were preserved. Serial UBOOT entry, reset, normal USB CDC plus both
audio endpoints, advancing NES frames and changing volume telemetry were
observed, with zero reported faults/underruns during that observation.
This used the existing private elevated Jieli writer with the public
packager/planner; the standalone public wrapper's full hardware command sequence
has **not** independently been bench-qualified. Physical screen/BGM/controls and
sustained duplex audio remain separate acceptance checks. No compatibility
claim is made for every FM-1 revision. See [VALIDATION.md](VALIDATION.md).

Start with [APP_UPDATES.md](APP_UPDATES.md) for the existing-tool guard patch,
offline package/plan and explicit load/backup/flash/reset commands.
Read the [ROM guide](ROM_GUIDE.md) to build the original diagnostic or select
your own compatible homebrew cartridge. A `.nes` cartridge is embedded in
`app.bin`; it is **not** itself an FM-1 firmware image or a separate flash slot.

## Research and attribution

Development has used the Jieli AC79 SDK, publicly available research, device
testing, and analysis of stock firmware behavior. This source release excludes
stock firmware images, raw disassembly, chip keys and commercial game ROMs;
it does contain stock-derived board parameters and an LCD initialization table.
It is not presented as a clean-room implementation.

Third-party components and adaptations retain their applicable licenses and
attribution. The project license applies only to material we have the right to
license. See [THIRD_PARTY.md](THIRD_PARTY.md), the focused
[source-reference map](PROVENANCE.md), and the
[publication checklist](PUBLICATION.md). Technical checks do not establish
redistribution rights. Source-only publication is the maintainer's decision;
it is not legal clearance or authorization to redistribute generated binaries.

**New to FM-1 development? Start with the [custom-firmware starting guide](GETTING_STARTED.md).**
It includes a minimal USB-only build, bring-up checkpoints and a copyable prompt
for an AI coding agent. “Custom ROM” here means device firmware, not a game ROM.

## Starting resources for developers and AI agents

Give your agent these links before asking it to write firmware. Read the linked
documentation and source first; do not automatically execute their setup,
update or flash scripts. Pin the revisions used for an experiment.

| Resource | What to use it for |
| --- | --- |
| [FM-1-RE](https://github.com/AL-255/FM-1-RE) | FM-1-specific architecture, disassembly, function maps and update-protocol research. Check firmware versions, address conventions and its unresolved recovery gates. |
| [jielie](https://github.com/kagaimiq/jielie) | Jieli chip/CPU, firmware-format and programming-protocol notes; start with the [USB_KEY notes](https://kagaimiq.github.io/jielie/isp/usb/usb-key.html) when studying forced entry. |
| [jl-misctools](https://github.com/kagaimiq/jl-misctools) | Existing offline firmware-container and resource utilities. Inspect format support before using a parser on your backup. |
| [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool) | UBOOT protocol and read/write tooling reference. Upstream lists WL82 support as unknown; review the exact loader and transport, not just the product name. |
| [Official AC79 SDK](https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK) | WL82 startup, linker, RTOS, USB and peripheral APIs. Use this project's pinned revision for builds. |
| [ghidra-jieli](https://github.com/kagaimiq/ghidra-jieli) | Jieli processor-module research for disassembly. Verify coverage of the exact pi32v2 instructions before trusting a decompilation. |

These are references, not bundled dependencies or guarantees that their images
and commands work on your board. Community findings must be checked against the
actual firmware and hardware. See the guide's [AI-agent starting prompt](GETTING_STARTED.md#ai-agent-starting-prompt).

## Start with USB serial and a way back to UBOOT

Our recommended first custom firmware is small: **USB CDC serial diagnostics,
plus a command that returns the device to Jieli UBOOT/download mode**. Establish
this before working on the LCD, audio engine or a complete application.

1. **Prepare recovery first.** Keep a private, verified backup of your own device
   and a proven way to enter download mode independently of the application.
2. **Bring up USB serial.** Confirm that the PC can enumerate the device and
   exchange diagnostic commands and responses reliably.
3. **Implement and test serial UBOOT entry.** Confirm that the device leaves CDC
   mode and re-enumerates in download mode, then verify the appropriate upload
   and normal-boot procedure for your hardware.
4. **Add peripherals one at a time.** Test the LCD/backlight, audio, keys, knobs
   and volume independently before integrating an application.
5. **Keep the update path working.** Iterate through build, serial UBOOT entry,
   upload with a compatible tool, reboot and observation over ordinary USB.

Once a working firmware provides that entry command, **routine updates do not
require the external force-downloader**. You still need a compatible PC-side
writer, the correct image layout and any OS permissions it requires. This does
not mean that an unresponsive or unbootable firmware can recover itself.

### Initial installation and recovery hardware

For initial installation when no usable software entry route exists—and for
recovery if the application crashes before USB starts—have a compatible **Jieli
forced-download adapter** available. Its job is to request download mode during
startup; this is distinct from transferring the firmware after USB enumeration.
Jieli documents [forced-download operation](https://doc.zh-jieli.com/Tools/zh-cn/dev_tools/forced_upgrade/upgrade_and_download.html)
and [AC79/WL82 USB download mode](https://doc.zh-jieli.com/AC79/zh-cn/release_v1.1.0/getting_started/preparation/update.html).

A programmable device, such as a Raspberry Pi/Pico-class board, could serve as
an alternative **only with suitable Jieli forced-entry firmware/software and
the correct electrical interface, timing and USB hand-off**. Simply connecting
a Raspberry Pi or installing generic USB-serial firmware is not sufficient.
This repository does not supply or qualify such an adapter implementation for
the FM-1. Retain a tested recovery method even after serial entry works.

Here, “UBOOT” means Jieli's download mode, not the unrelated Das U-Boot project.
The [jl-uboot-tool project](https://github.com/kagaimiq/jl-uboot-tool) is a useful
protocol/tool reference, but its upstream support table lists WL82 as unknown;
do not assume that an arbitrary checkout, loader or another Jieli product's
image is compatible with the FM-1.

### Serial entry implemented in this example

The CDC command path is in [protocol.c](firmware/usb-diag/protocol.c),
[rx_channel.c](firmware/usb-diag/rx_channel.c) and
[boot_entry.c](firmware/usb-diag/boot_entry.c). With this firmware running:

1. Stop any active peripheral/NES test with `TEST STOP` and wait for it to stop.
2. Send `UBOOT` followed by **LF only**.
3. Wait for `OK UBOOT ARMED CONFIRM-WITHIN-5000MS`.
4. Within five seconds, send `UBOOT CONFIRM` followed by **LF only**, as a
   separate command. Do not append CR or other bytes.
5. Expect the serial connection to disappear; detect the download-mode device
   before using a compatible firmware writer.

This two-step confirmation is part of our custom firmware, not a command claimed
to exist in the stock firmware. Recheck the transition on your exact build and
device. The V14 composite application passed this transition in the test above;
the separate USB-only first-milestone artifact remains hardware-unqualified.
See [VALIDATION.md](VALIDATION.md).

## What the example provides

The source includes LCD/backlight initialization and buffered transfers, audio,
digital volume, paced key scanning, knob handling, per-channel effects and USB
diagnostics. The NES example combines these components and uses Famicom-style
controls: B/A on the highest F/G keys, with directional controls on the low keys.

For a new application, begin with `firmware/usb-diag/` for CDC diagnostics and
boot entry, then study `firmware/nes/boot/` and `firmware/nes/src/` for board and
peripheral integration. The current top-level build recipe builds the NES-based
example with an original diagnostic ROM; it is not yet a generic application
wizard or a turnkey first-install/recovery package.

## Build the example

### Requirements

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

On a fresh checkout the default firmware build generates an original
checkerboard/pulse/controller diagnostic ROM from source. It needs neither a
commercial ROM nor a stock dump. An optional ignored `local/rom.json` can select
your own persistent cartridge default; `--diagnostic` explicitly ignores it.
Build outputs go under ignored `build/`. See [ROM_GUIDE.md](ROM_GUIDE.md).

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

An application-only packager and wrapper around the existing guarded Jieli
writer are now provided: see [APP_UPDATES.md](APP_UPDATES.md). Packages contain
only the caller's audited application and minimal manifest, not full ROMs.
The offline planner prepares private changed sectors from the owner's backup,
preserving bootloader, configuration and application placement. The wrapper
and source-only guard patch do not bundle RAM loaders, vendor images, SDK
binaries, recovery blobs or an elevation server.

**Do not write the application binary directly over the full flash.** Hardware
operations require an explicit wrapper subcommand; package/plan/build commands
do not contact the device. The V14 app-only scheme was tested using the existing
private writer; the standalone wrapper is offline-tested, not independently
hardware-qualified. Existing private recovery/flash workflows are unchanged.
Firmware CDC boot-entry support remains in source.

Optional **USB audio plus serial**, reused from the MDX karaoke work, is
available with `--usb-audio`. See [USB_AUDIO.md](USB_AUDIO.md) for PC playback,
NES capture, volume ownership, build/package commands and the unchanged
app-only Jieli programming method. V14 startup/USB/telemetry observations are
recorded above; sustained audio acceptance remains pending. Imported GPLv3 code
means the combined current firmware
examples are not Apache-only binaries.

## Source-only release

```powershell
python -m unittest discover -s tests -v
python scripts/release.py --check --git
python scripts/release.py --git --output dist/fm1-source-candidate.zip
```

This creates `dist/fm1-source-candidate.zip` using only exact paths in
`public-files.txt`, with a SHA-256 inventory. The restrictive `.gitignore` allows
only these reviewed source files. New files require an explicit update to both
lists. Choose a fresh `--output` name for another candidate; existing archives
are never overwritten. Archive entry timestamps and permissions are fixed.
Neither mechanism removes a sensitive file already tracked in Git; this
repository was initialized from the reviewed source export, without private
development history.

The `--git` check requires a non-shallow checkout, matches the tracked-file list
to the manifest, and checks paths/modes and limited secret patterns across local
reachable history (including commit/tag messages and deleted files). It does not
scan remote-only refs, issues, PR discussions, releases, caches or Git LFS payloads.
The [source-only CI workflow](.github/workflows/source-release.yml) runs the same
checks with read-only repository permissions and does not upload any artifacts.
Stage reviewed new files before running the tracked-inventory check. For an
extracted source ZIP without `.git`, use `--check` without `--git` instead.

**Publish the source archive, not a ZIP of the whole working directory.** Local
build results can embed your chosen ROM and contain machine-specific paths.
Excluded: ROM files/generated ROM C arrays, SDK/core checkouts, toolchain,
compiled firmware, flash backups, stock disassembly, session logs, device
identifiers, and elevated-session configuration. Packaging includes a limited
secret-pattern/binary check, not a guarantee against every possible disclosure.

See [VALIDATION.md](VALIDATION.md) for the actual verification results.
The [publication audit](PUBLICATION_AUDIT.md) records the reviewed source terms,
boot/power evidence, included SDK-derived audit constants and GitHub surface
checks. It also separates completed checks from the maintainer's release decision.

The USB descriptor currently retains an SDK VID/PID (`3654:5155`) for local bench
compatibility, not a project-owned allocation. Resolve identity authorization
before distributing a USB product; no USB-IF certification is claimed.

## License

Project-authored material is currently licensed under
[Apache-2.0](LICENSE). The license badge describes that current choice; this
repository has not been switched to MIT.

External dependencies and any upstream-derived portions retain their applicable
licenses and notices. The project's license does not grant rights to stock
firmware, game ROMs or third-party tools. A different license for project-owned
contributions would not remove those obligations or resolve the provenance of
stock-derived material. See [THIRD_PARTY.md](THIRD_PARTY.md) and the retained
[Apache-2.0 dependency license](licenses/Apache-2.0.txt).
