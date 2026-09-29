# Custom firmware development for the M-VAVE FM-1

[![Status: experimental](https://img.shields.io/badge/status-experimental-orange)](#verification-status)
[![MIDI: hardware unverified](https://img.shields.io/badge/MIDI-hardware%20unverified-orange)](#verification-status)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

This repository shares resources, board-support code and a worked example of
**how to develop custom firmware for the FM-1**, based on the Jieli WL82. The
goal is to make the hardware accessible for experiments with synthesizers,
instruments, effects and other applications—not to turn the FM-1 into an NES box.

The NES player is an example that exercises the display, audio, keys, knobs and
real-time scheduling together. Use it as a reference, or replace it with your own
application. This is an independent, experimental project, not an official
M-VAVE or Jieli release. No game ROM or stock firmware is included.

## Verification status

**The MIDI path has not yet been confirmed by the maintainer on hardware.**
Treat MIDI input/output, patch/parameter SysEx and MIDI/SysEx firmware upload as
unverified for this project. Stock documentation and source-code analysis are
references, not evidence of successful end-to-end hardware tests here.

USB CDC serial and Jieli UBOOT are separate from MIDI. Their implementation does
not establish MIDI support. The SysEx section below describes a possible future
transport, not a confirmed upload path. Local build and host-test evidence is
recorded in [VALIDATION.md](VALIDATION.md); it is not hardware certification.

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
device. The source export's diagnostic artifact remains unflashed/unqualified;
see [VALIDATION.md](VALIDATION.md).

### What about SysEx uploads?

**Status: unverified on hardware by the maintainer. No working MIDI/SysEx
firmware-upload path is claimed by this repository.**

**MIDI SysEx can be another update transport**, if the running firmware or
bootloader implements a matching update protocol. That requires both receiver
and uploader support: framing, image validation, flash layout and a recovery
strategy. It is an alternative development option, not an uploader supplied by
this source release.

DX7-style **patch/parameter SysEx is not firmware upload**. Likewise, this
example's CDC `BEGIN`/`DATA`/`END` commands only verify received length and CRC;
they do not store or install an image, and `COMMIT` is deliberately blocked.
The implemented iteration route is serial **entry into UBOOT**, followed by a
separate compatible writer—not self-flashing over CDC or SysEx. A software
upload route also cannot replace forced-entry recovery when that software no
longer runs.

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
repository was initialized from the reviewed source export, without private
development history.

**Publish the source archive, not a ZIP of the whole working directory.** Local
build results can embed your chosen ROM and contain machine-specific paths.
Excluded: ROM files/generated ROM C arrays, SDK/core checkouts, toolchain,
compiled firmware, flash backups, stock disassembly, session logs, device
identifiers, and elevated-session configuration. Packaging includes a limited
secret-pattern/binary check, not a guarantee against every possible disclosure.

See [VALIDATION.md](VALIDATION.md) for the actual verification results.

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
