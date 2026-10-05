# USB audio, serial and application-only updates

The optional `--usb-audio` profile reuses generic USB code from the MDX karaoke
work at `41410578152eec195b534b3acfe2fa1b10e7476e`. It does not include its
MDX player, songs or stock firmware. Offline tests and a V14 startup/USB/serial
UBOOT experiment have passed; sustained simultaneous audio/CDC, physical audio
and recovery coverage still need bench acceptance. See VALIDATION.md.

## Functions on one cable

| Function | Path |
| --- | --- |
| USB playback | PC stereo 48 kHz / 16-bit PCM, converted/mixed into the 44.1 kHz DAC |
| USB capture | NES after its effects, before master volume and PC return |
| CDC serial | Existing diagnostics, peripheral controls and guarded UBOOT entry |

NES is mono, duplicated into stereo capture. Capture is **not analog input
recording**. PC return is excluded to prevent digital loopback. Saturating
mixing can clip when both signals are loud; lower PC level when combining them.
The physical volume knob sets digital DAC master gain, not USB capture level.
It remains sampled with NES stopped and CDC closed.

## Controller II microphone switch

The composite NES build includes a runtime switch over the existing CDC serial
port (send one command at a time, LF only):

```text
MIC ON
MIC OFF
MIC STATUS
```

Default is **OFF**. With `MIC ON`, audio played by the PC to the FM-1 USB
playback endpoint activates the emulated Famicom controller II microphone.
To use a PC microphone, route that microphone to this playback endpoint in
your host audio software; the FM-1 does not capture a physical microphone.
Regular USB playback remains audible, capture stays isolated, and no game
key/knob assignment changes. `MIC OFF` clears the signal immediately.
`MIC STATUS` (also included in `TEST STATUS`) reports `enabled` and `active`.

The [Famicom mic input](https://www.nesdev.org/wiki/NES_controller) is an
immediate one-bit signal at `$4016` bit 2, not a serial pad bit at `$4017` or
PCM input to the APU. Only games that read that microphone signal respond;
do not expect an effect in games that ignore it.

This implementation is a sound-activity approximation, not cycle-exact analog
waveform emulation. Either channel can trigger it, including opposite-phase
stereo. The fixed attack threshold is 1024 signed-16-bit counts (about -30 dBFS),
release threshold 512, with a 10 ms hold. Adjust the PC playback level if needed.
Detection uses consumed USB samples before master gain; NES music and USB
capture do not trigger it. It shares the existing DAC callback and adds no
interrupt, allocation or blocking wait. The CPU reads a volatile bit snapshot.
Silence clears after the hold; unprimed/starved playback or stream stop clears
immediately. A playback alternate-setting restart retains the switch but clears
activity; USB reset/reconnect, UBOOT entry and firmware restart turn it OFF.
Closing CDC alone does not turn it off. CDC-only builds reject these commands.

Host detector, target lifecycle and actual generated CPU register tests pass;
physical microphone-aware cartridge acceptance is still pending.

UAC1 uses interfaces 2..4 and EP1 IN/OUT: fixed stereo PCM, 192 bytes per
millisecond in each direction. CDC uses interfaces 0/1, EP2 OUT, EP2 IN
notifications and EP3 IN data. The composite descriptor includes IADs. No
unimplemented sample-rate/device-volume controls are advertised. The virtual
line-capture category inherited from MDX does not imply physical line-in.

## Build and package app.bin

Configure the existing pinned SDK/core/compiler as in GETTING_STARTED.md.
Reuse your Python installation: no interpreter or environment is installed.
With no ROM option or private local default these commands use the original
diagnostic cartridge:

```powershell
python scripts/build.py host
python scripts/build.py firmware --usb-audio --package build/usb-audio-v1.fm1app
python firmware/usb-audio/test_link.py -v
```

Choose a fresh package name for each build. Composite output defaults to
`build/firmware-audio`. CDC-only remains `python scripts/build.py firmware`
in a separate directory. A lawfully supplied cartridge uses the existing
`--rom` and `--rom-sha256` arguments.

The linked `fm1-usb-diag.app.bin` is the **application payload**. `--package`
calls the existing packager only after the matching static audit passes.
The `.fm1app` contains exactly `app.bin` and a minimal manifest, without the
installed bootloader or unit configuration. No full-ROM candidate is generated.
All generated binaries/packages are excluded from the source release.

For a persistent private bench default, put only `rom` (a local file path) and
`sha256` (its expected hash) in ignored `local/rom.json`. Relative paths are
resolved from that file's directory. Explicit `--rom`/`--rom-sha256` override
it; `--diagnostic` explicitly selects the original test cartridge. An invalid
or missing configured ROM fails instead of silently substituting the test ROM.
Neither the local configuration nor game bytes are included in Git/releases.

## Program using the existing method

Follow [APP_UPDATES.md](APP_UPDATES.md), not a direct write of raw app.bin:

1. Preserve the original private recovery backup and independent UBOOT entry.
2. In CDC send `TEST STOP`; wait for the worker's `TEST END`. Send `UBOOT`,
   wait for `OK UBOOT ARMED`, then `UBOOT CONFIRM` within 5 seconds. Use LF only.
3. In UBOOT use the existing guarded jltool wrapper to load the external RAM
   helper, read a fresh baseline, and prepare/review an offline sparse plan.
4. Explicit `flash` changes application sectors and directory metadata only;
   boot/configuration are preserved and the directory sector is written last.
5. Explicit `reset`, then observe normal boot and USB enumeration.

Physical app placement remains `0x4120`, CPU entry `0x02000120`; required
metadata at `0x4000`/`0x4020` is updated. The installed loader is retained.
Programming is not atomic: interruption may require physical recovery.
No new writer or elevation service is introduced.

CDC `BEGIN`/`DATA`/`END` still validates transfer only; `COMMIT` is blocked.
There is **no serial/SysEx firmware installation**. Serial requests UBOOT;
the established PC-side Jieli tool programs the application.

## Ownership and diagnostics

One persistent DAC owner handles NES, tone tests and PC playback. USB control
and the peripheral worker are pinned to CPU0 with USB/ALINK IRQs. DAC callbacks
tap capture, mix PC audio, then apply master gain. The existing DAC IRQ supplies
the bounded ADC cadence, averaging one volume tick per 2 ms. No extra volume
interrupt or scanner is added, and the NES scanner no longer owns ADC in this
profile. ADC failure mutes the DAC without a polling wait.

The reused bridge has two 1024-frame stereo queues, linear conversion and
bounded drift correction. Busy USB submission returns immediately, without
the SDK's jiffies polling writer. Rejected capture packets remain staged for
retry. Epochs/generations reject old-session DMA writes; short CDC packets
avoid blocking zero-length-packet handling.

`TEST STATUS` adds `USB AUDIO` and `USB TRANSPORT` queue/error/submission
counters. Submission is not proof of host receipt. Only confirmed UBOOT disarms
streams and quiesces the DAC IRQ; an expired arm does not stop audio. The
transition retains the existing RAM-resident SDK boot entry, not a flash writer.

## Validation and bench gate

Host tests cover conversion/drift, stereo, malformed packets, clipping, capture
isolation, reset/epoch cancellation, DMA ownership, idle volume sampling and
600 virtual seconds of normal/backpressured shared-endpoint service. These
models are not Windows, physical bus or timing certification.

Target audits pin descriptors, packet instructions, CPU0 tasks, capture/mix/gain
call order, actual setup-filter policy, UBOOT teardown, boot/power and internal RAM placement. Corruption
tests check rejection. Bench acceptance must cover physical enumeration,
playback/capture, volume while stopped, concurrent CDC, sustained duplex,
disconnect/reconnect and serial UBOOT.

The first bench build missed the MDX composite setup policy: its stale CDC-only
hook rejected interfaces2..4 and EP1, producing Windows `CM_PROB_FAILED_START`.
The corrected policy was rewritten and Windows enumerated CDC plus both audio
endpoints. CDC telemetry showed advancing NES frames with zero faults/underruns.
That confirms startup/liveness, not sustained duplex audio or physical volume
acceptance. Windows may retain the old MDX endpoint display name for this shared
bench VID/PID; the bus-reported product is `FM1 NES USB Audio`.

The subsequent 2026-10-03 private cartridge build was installed on the V14
baseline through 51 changed sectors and one complete final readback, with
boot/config/reserved preservation. Serial UBOOT entry and post-reset advancing
frames were observed. Volume ADC/target/gain changed with valid readings and
zero reported errors. These are telemetry observations, not a listening test
or qualification of the standalone public wrapper's hardware command sequence.

## License boundary

Imported USB/packet/audit/test code retains GPLv3 and attribution; original
Apache source keeps its notices. Both current profiles link the reused GPLv3
packet helper, so their combined binaries are not Apache-only or MIT. See
THIRD_PARTY.md and `licenses/fm1-mdx-GPL-3.0.txt`. SDK/cartridge terms remain
applicable. Source-only publication is a separate maintainer decision recorded
in PUBLICATION.md, not binary redistribution clearance.
