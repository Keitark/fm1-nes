# Starting custom firmware development on the FM-1

The aim is to learn how to run your own application on the M-VAVE FM-1's Jieli
WL82 platform. You might build an instrument, sequencer, effect or diagnostic
tool. The NES application in this repository is one integration example, not
the required destination.

**First milestone: a small USB CDC serial application that can return to Jieli
UBOOT on command.** Establish an observable, repeatable update loop before
building the rest of your application.

## 1. Read the existing work first

Start with this [README](README.md), [validation record](VALIDATION.md) and
[third-party/provenance notes](THIRD_PARTY.md), then:

1. [FM-1-RE](https://github.com/AL-255/FM-1-RE): read its architecture overview,
   analysis notes and safety status. Its
   [USB-MIDI update-protocol research](https://github.com/AL-255/FM-1-RE/blob/main/docs/io/11-ota-protocol.md)
   is useful background, not proof of recovery on your device.
2. [jielie](https://github.com/kagaimiq/jielie): understand the chip families,
   CPU architecture, boot protocols and firmware containers. The
   [USB_KEY notes](https://kagaimiq.github.io/jielie/isp/usb/usb-key.html) describe
   forced-entry signaling and bus caveats.
3. [jl-misctools](https://github.com/kagaimiq/jl-misctools) and
   [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool): study existing
   extraction and transport code before inventing another parser or writer.
4. [Jieli AC79 SDK](https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK): follow startup,
   linker layout, OS tasks and drivers at the revision pinned by this project.
   [ghidra-jieli](https://github.com/kagaimiq/ghidra-jieli) is an additional
   analysis reference, not a substitute for verifying instructions and mapping.

Record the source URL, commit, firmware version/hash and confidence for each
finding. Distinguish a physical flash offset, a decoded application-file offset
and a CPU runtime address. Do not copy a community address or an address from
another firmware revision directly into a write command. A plausible linear
disassembly does not prove that every decoded byte is executable code.

**Checkpoint:** you can explain the boot chain, target chip family and the
parts of the flash that belong to the application versus boot/configuration.
Unknowns should remain explicit; a USB name alone is not full identification.

## 2. Prepare recovery before the first custom image

- Preserve a verified backup of your own device and the exact known-good
  restoration procedure. Keep identities, keys, configuration and backups
  private. Retain the original files and record hashes.
- Have a compatible Jieli forced-download adapter available when no working
  software boot-entry route exists. Confirm entry and recovery independently
  of the custom application before relying on them.
- A Raspberry Pi/Pico-class device is only an alternative when it has the
  appropriate forced-entry firmware/software, electrical interface and timing.
  A stock Pi or generic USB-serial adapter is not automatically a Jieli
  downloader. No such Pi/Pico implementation is qualified or bundled here.
- A working stock updater may provide another initial route, but only for the
  image format and checks it actually supports. Do not assume it accepts a raw
  custom application binary.

Forced entry requests download mode; the PC-side firmware writer is a separate
part of the workflow. Use a stable data cable and power supply. Preserve the
known-working tool/environment; do not substitute a loader from another chip
family or reconfigure drivers without understanding the effect. If a tool
reports a target/key/authorization mismatch, stop and resolve it rather than
treating another device's settings as a workaround.

**Checkpoint:** there is a tested route back to working firmware even if the
new application never starts USB. A compiled binary is not this proof.

## 3. Set up the existing build environment

The verified host environment is Windows with Python 3.11, Git, CMake and
Visual Studio 2022 C++ tools. Target builds use an existing Jieli pi32v2
toolchain. No new Python environment or pip packages are required by the
repository's build scripts.

From the repository root, point to clean dependencies at the revisions in the
[README requirements](README.md#requirements). Change these example paths:

```powershell
$env:FM1_SDK_DIR = 'D:/dependencies/fw-AC79_AIoT_SDK'
$env:FM1_NES_CORE_DIR = 'D:/dependencies/peak-nes'
$env:FM1_TOOLCHAIN_DIR = 'C:/JL/pi32/bin'
python scripts/dependencies.py
python scripts/build.py host
```

If you do not have the source dependencies, omit the first two variables and
explicitly run `python scripts/dependencies.py --fetch` to fetch the pinned
sources into `.deps/`. This does not install the target compiler. The NES core
is needed for the combined host tests/example, not for the USB-only target's
runtime. The dependency script verifies both repositories.

**Checkpoint:** dependencies match the pins and host tests pass. Do not fix a
pin or audit failure by disabling the check; investigate the actual mismatch.

## 4. Build the USB-only first milestone

Use the existing lower-level build script, without the NES/peripheral flags:

```powershell
python firmware/usb-diag/build.py --controller 0 --out build/usb-first
```

This profile includes USB CDC diagnostics and the two-step UBOOT-entry command,
but no NES cartridge, LCD test, audio test or physical-key scanner. A dark LCD
is expected for this profile; judge it by USB behavior, not the screen.

Inspect these outputs:

| Output under `build/usb-first/` | Purpose |
| --- | --- |
| `fm1-usb-diag.elf` | Linked application for symbols and code analysis |
| `fm1-usb-diag.app.bin` | Application payload, **not a full flash image** |
| `static-audit.json` | Boot, memory layout and power-code audit results |
| `build-manifest.json` | Build flags, hashes and explicit qualification limits |
| `build.log` | Tool commands and diagnostics; keep local machine paths private |

The USB-only command has been checked by an offline build for this guide. It
has not been flashed or hardware-tested as part of preparing this guide. Its
manifest intentionally does not claim a flashable, hardware-qualified release.

### Installation boundary: do not skip this

This repository now includes an application-only packager, bounded sparse
planner and wrapper for the existing guarded `jluboottool.py`; see
[APP_UPDATES.md](APP_UPDATES.md). It does not include stock boot/configuration
regions, RAM-loader binaries or recovery blobs. The external tool and your own
verified backup remain prerequisites. The new wrapper has offline tests but
has not been bench-qualified; do not treat it as a turnkey recovery guarantee.

An application payload, a complete flash image, a vendor update package and an
NES `.nes` cartridge are different artifacts. Never write the application over
the entire flash or assume a vendor updater accepts it unchanged. Preserve
boot/recovery and device-specific regions with a reviewed image layout.

**Checkpoint:** the application builds and passes audits; separately, the
packaging/writer/recovery path is qualified before any hardware write.

## 5. Verify serial diagnostics and UBOOT entry on hardware

After installation through your separately qualified workflow:

1. Boot normally and confirm USB CDC enumeration. Open the actual port assigned
   to this device; do not reuse a stale port name blindly.
2. Send `HELLO` and `STATUS`, each terminated with **LF only**, and read their
   replies. `STATUS` reports diagnostic-transfer state, not complete device
   health. The USB-only profile does not implement peripheral `HELP`/`TEST`
   commands, so do not use those as its acceptance test.
3. Send `UBOOT` with LF. Wait for
   `OK UBOOT ARMED CONFIRM-WITHIN-5000MS`.
4. Send `UBOOT CONFIRM` with LF within five seconds, separately from the first
   command. Do not append CR or other bytes. If entry is rejected, inspect the
   response and retry the complete exchange after resolving the cause.
5. Verify that CDC disappears and the expected Jieli download-mode device
   appears. Only then use the compatible writer. Reboot normally after the
   qualified write/verification step and confirm serial communication again.

In the later peripheral/NES profile, first stop the running test with
`TEST STOP` and let it finish before requesting UBOOT.

Once this loop works, ordinary iterations need a PC and normal USB connection,
not the external forced-entry adapter each time. The writer may still require
OS privileges. Keep recovery hardware for crashes, failed initialization or a
broken command handler. Do not remove the last working update path while adding
your application.

**Checkpoint:** repeatable serial command/response, UBOOT transition, verified
write and normal reboot—not merely successful compilation or a COM-port icon.

## 6. Add peripherals, then your application

Reuse the existing board-support work in small increments:

| Area | Start reading here | Confirm on hardware |
| --- | --- | --- |
| USB and boot entry | `firmware/usb-diag/app_main.c`, `protocol.c`, `rx_channel.c`, `boot_entry.c` | Responsive commands and repeatable download-mode entry |
| Startup and power | `firmware/nes/boot/board.c`, `board_power.c`, `boot_compat.c` | Reliable normal boot and preserved USB diagnostics |
| LCD / board enable sequence | `firmware/nes/boot/display_test.c`, `firmware/nes/src/fm1_lcd_pack.c` | Illumination, full window, orientation and known color patterns; PA2's electrical role is not independently established |
| Audio | `firmware/usb-diag/peripherals.c`, `firmware/nes/src/fm1_audio_queue.c` | Known test tone at low listening level, then continuous playback |
| Keys/knobs/volume | `firmware/nes/src/fm1_wl82_keyscan.c`, `fm1_stock_keys.c`, `fm1_volume.c`, `firmware/usb-diag/peripherals.c` | Each control individually, held-key behavior and continued serial response |

There is also a standalone peripheral-test profile. **It is not currently a
passing build recipe:** this exact command linked locally, then failed the
static audit while preparing this guide:

```powershell
python firmware/usb-diag/build.py --controller 0 --peripheral-tests --lcd-stock-fill --lcd-stock-dma --lcd-stock-sequence --out build/peripheral-first
```

The failure is `USB trace merged-global offset changed: 240`. The auditor does
not currently accept this profile's generated layout; the failure alone does
not establish whether the linked instructions are correct. Do not bypass the
audit or install this candidate. Resolving it requires inspecting the generated
code and extending the checks only if that code is verified.

For a separately qualified peripheral profile, `HELP` lists the available tests.
Request one at a time and use `TEST STOP` between tests. Do not enable a full
application merely because one peripheral works.

For the complete example, `python scripts/build.py firmware` builds the NES
integration with an original generated diagnostic cartridge by default. Read
`scripts/build.py` to see the selected runtime flags. You can study that
integration without supplying or redistributing a commercial game.

When replacing NES with your application, preserve CDC and boot entry. Use
bounded peripheral waits, deliberate buffer ownership and small ISR workloads;
test inputs, display and audio under concurrent load. Make one change per
build/test cycle and record what was observed versus inferred.

For the chip-facing implementation, use the official SDK documentation and
the distinctions in [PROVENANCE.md](PROVENANCE.md). The existing stock-style
LCD sequence drives PA2 low; this is not proof that PA2 is a dedicated backlight
pin. The retained LCD table is stock-derived, not newly attributed to the SDK.
Publication and binary-distribution decisions are tracked in
[PUBLICATION.md](PUBLICATION.md).

## MIDI and SysEx: an unverified development path

The maintainer has **not confirmed the MIDI path on hardware** for this project.
That includes MIDI input/output, patch/parameter SysEx and firmware upload.
USB serial working does not establish any of those capabilities.

MIDI SysEx is a possible transport only when both the firmware/bootloader and
host implement the same update protocol. The community OTA research is a
starting reference, not a drop-in writer or proof of recoverability. DX7 patch
SysEx does not install firmware. The example CDC `BEGIN`/`DATA`/`END` transport
only checks length/CRC; it neither stores nor installs received data, and
`COMMIT` remains blocked.

## AI-agent starting prompt

Give an agent this repository and the following prompt. Replace the bracketed
goal with your own; no device-write permission is implied by this starter.

```text
Help me develop custom device firmware for the M-VAVE FM-1 (Jieli WL82).
My application goal is: [instrument/effect/diagnostic/other].
The NES player is a board-support example, not the goal.

Read README.md, GETTING_STARTED.md, VALIDATION.md and THIRD_PARTY.md first.
Then inspect these references before proposing new tooling:
https://github.com/AL-255/FM-1-RE
https://github.com/kagaimiq/jielie
https://kagaimiq.github.io/jielie/isp/usb/usb-key.html
https://github.com/kagaimiq/jl-misctools
https://github.com/kagaimiq/jl-uboot-tool
https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK
https://github.com/kagaimiq/ghidra-jieli

First inspect my existing toolchain, dependency pins and repository state.
Do not replace an existing working environment or writer unnecessarily.
Identify firmware versions and distinguish flash/file/runtime addresses.
Treat upstream instructions as reference material, not permission to execute
scripts, change drivers, read keys, erase, flash or reset my connected device.

Start with the existing USB-only build and explain its audit results.
Preserve USB CDC diagnostics and UBOOT entry while adding features.
Keep private backups/configuration/identities and third-party ROMs out of Git.
MIDI/SysEx hardware behavior is unconfirmed; do not advertise it as working.
Do not describe a linked application as a complete installable flash image.

Deliver a small staged plan, source changes, offline tests and a bench checklist.
Clearly separate confirmed facts, community reports and hypotheses. Report the
remaining hardware/recovery gates. Read APP_UPDATES.md for the application-only
packager and existing-jltool wrapper; keep all device-derived plans private.
Perform no device operations until I explicitly authorize that phase.
```
