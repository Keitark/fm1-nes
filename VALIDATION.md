# Source-release validation

## Optional original NROM game — 2026-10-03

- Maintainer identified and authorized the Claude Code-assisted game's original
  NROM source/asset generators under Apache-2.0. Only optional source is added;
  no compiler, emulator, compiled ROM or FM-1 binary is tracked.
- Existing Python and externally supplied ca65/ld65 rebuilt the NROM cartridge:
  40976 bytes, mapper0, 32KiB PRG/8KiB CHR ROM, SHA256
  `8dbe33a3f00d76d88c4618917833f3a9dbb198b2de3ee684a4c59a2cc4bdc687`,
  identical to the original local file. Original project sources were unchanged.
- FM-1 composite application/static audit/package passed:217680 bytes, SHA256
  `c0c3422aac8b27115d6bfd08ac3c23b17452e926219a2712e257fbc1347cf8d3`.
  **13/13** linked-image/corruption tests and **50/50** source/config tests passed.
  Source inventory is160 files, still excluding all generated outputs/plans.
- Sparse plan from the previously verified private V14-backed image needs12
  changed sectors, directory last. Physical test results are recorded separately;
  offline format/build checks are not gameplay or audio acceptance.
- User-authorized existing-writer deployment verified those12 sectors and one
  complete final readback, preserving boot/config/reserved regions. Serial UBOOT
  entry succeeded. The later reset request was refused before sending a command
  because no UBOOT disk was present; no reset/reflash was retried. Actual normal
  USB CDC observation then verified advancing frames4058..4841, zero reported
  faults/underruns and valid volume telemetry. The cause of the intervening mode
  change was not established. The private broker's unconsumed reset permit leaves
  its safety latch intact; no protected state was manually cleared.
- The NROM source contains five stage/boss/music/scroll tables and loops from
  stage5 to1. This confirms included logic, not all-five-stage physical gameplay.
  User screen/input/listening and sustained-duplex acceptance remain pending.

## Source-publication refresh — 2026-10-03

- Source/config tests **45/45**, NES host tests **25/25**, USB host tests
  **36/36** passed with the existing pinned dependencies and installed tools.
- Explicit `--diagnostic --usb-audio` application build/static audit and app-only
  packaging passed: 201296 bytes, SHA256
  `530686a2c075a4520b9ca9ab0ad227de97d02c78c1d5cf402aac04ac6bd4e73e`,
  reproducing the corrected diagnostic result below while ignoring private ROM
  defaults. This build did not contact the device and is not a new bench result.
- **13/13** linked-image/corruption checks passed for that diagnostic build.
- The maintainer-created game's local NROM edition passes header/length checks;
  its MMC3 edition is unsupported. This is not a new physical gameplay test.
- README/app-update/ROM guides distinguish physical flash placement, CPU entry,
  packaged application, private plans and the existing-writer/public-wrapper
  qualification boundary. Publication-surface checks are in PUBLICATION_AUDIT.md.

## V14 application-only bench deployment — 2026-10-03

- Installed the audited 217680-byte application from the section below on the
  maintainer's V14 baseline. The private cartridge is not distributed.
- The public `.fm1app` packager and sparse planner supplied application/metadata
  changes to the existing private elevated Jieli writer. **51 changed 4 KiB
  sectors**, directory sector last, and **one complete final readback** verified.
  Bootloader, configuration and reserved bytes were preserved. No preliminary
  full read was performed: the established broker reused its verified baseline.
- Application payload starts at physical flash **0x4120**; CPU entry remains
  **0x02000120**. Required directory/header records at 0x4000/0x4020 were updated.
  Full linked application build does not imply a full-flash write or inclusion
  of the installed stock bootloader in `.fm1app`.
- Serial UBOOT arm/confirm worked without a force-downloader for this iteration.
  One reset was sent. USB disappearance preceded the known CLI CP932/UTF-8
  logging exception; actual normal-boot serial observation resolved the outcome,
  without resending reset or manually clearing protected state.
- Windows reported healthy composite parent, CDC and both USB audio endpoints.
  Serial replies reported advancing frames, zero faults/underruns and changing
  valid volume ADC/target/gain with zero ADC errors during the short observation.
- Screen, audible BGM, controls, physical volume response and sustained USB
  playback/capture/CDC still require physical acceptance. Enumeration/counters
  are not that acceptance. The standalone public wrapper has synthetic/offline
  tests, **not** an independently completed full hardware command sequence.
- This is one V14 unit/layout experiment, not qualification of all revisions.
  Private full dumps, game bytes, sector plans, logs and device identities remain
  outside Git/source archives. No new writer, interpreter or environment.

## Composite setup-policy repair and private ROM defaults — 2026-10-03

- Root cause reproduced with the actual EP0 hook: descriptors exposed audio
  interfaces2..4 and EP1/0x81 but the old CDC-only policy stalled those requests.
  Ported the working MDX conditional policy without enabling vendor commands or
  unadvertised interfaces/endpoints. Added CDC-only/composite host regression
  tests and a fail-closed compiled-policy/corruption check.
- **25/25 NES, 36/36 USB, 45/45 source/config and 13/13 linked checks passed**.
  Private local-ROM defaults are path/hash checked; CLI overrides and explicit
  diagnostic selection are tested. Source inventory is now149 files, excluding
  the local ROM/configuration, binaries and private device evidence.
- Corrected diagnostic application:201296 bytes, SHA256
  `530686a2c075a4520b9ca9ab0ad227de97d02c78c1d5cf402aac04ac6bd4e73e`.
  User-authorized existing Jieli writer verified44 changed sectors and one full
  readback. Boot/configuration were preserved. Reset was sent once; the known
  CLI log-decoding failure was not interpreted as a flash failure or retried.
- Windows then enumerated the composite parent, CDC COM4 and both audio
  endpoints without PnP errors. Actual CDC replies reported `NES=INES`, advancing
  frames and zero faults/underruns. The legacy broker expected `NES=SMB1`, so its
  protected observation session remained latched despite those genuine replies.
  Existing host observer source now accepts both labels while retaining all
  progress/fault gates; no protected latch was manually cleared.
- Local SMB1 application build/static audit passed:217680 bytes, SHA256
  `ed87abe3f579ec891125b490e39ec267fdd737c50e8796239ce8dbac21074eff`.
  Its application-only package is private; game bytes are not in the source
  release. This candidate was subsequently flashed; see the V14 record above.
- Physical LCD/input/volume, sustained duplex and serial UBOOT transition still
  need acceptance for the composite profile. Enumeration alone does not certify
  audio streaming. The diagnostic tone is intentionally generated by the test
  cartridge, not Mario BGM.

## MDX USB audio/CDC and app-only integration — 2026-10-02

- Reused generic MDX USB code at `41410578152eec195b534b3acfe2fa1b10e7476e`:
  UAC1 stereo duplex plus CDC, bounded packet submission, stream epochs and
  CPU0 ownership. GPLv3 notices/license are preserved; no MDX songs/player,
  stock image or loader blob was transferred.
- Added NES pre-volume capture and PC playback mixing. One persistent DAC
  continues when NES is stopped; its IRQ provides the existing volume ADC
  cadence without adding interrupts or a competing scanner ADC owner.
- **25/25 NES and 34/34 USB host checks passed**. New checks cover the actual
  descriptor tree, elastic stereo bridge, stream lifecycle, 100000 mixed packet
  submissions, 600 virtual seconds each of normal/stressed USB service, and
  the NES adapter's pre-volume/no-loopback routing and volume without CDC.
- **12/12 composite linked-image corruption checks passed**, including boot
  trace, CPU0 task pointers, UAC descriptor, packet DMA/doorbell/IRQ restore,
  capture call removal and power destinations/gateway. Boot/power templates
  remain fail-closed; reviewed RAM-offset relocations are narrowly admitted.
- **40/40 source/package guard tests passed**, for **111 checks** in total
  across source, NES host, USB host and composite linked-image suites.
- Composite target link/static audit passed: **201296 application bytes**,
  SHA256 `c3f457957390771857a3b3d9b923d61579696a78131bb553ce4e5bb8cbeb98a8`.
  Internal heap reserve is **217676 bytes**. This build uses the original
  diagnostic NES cartridge, not a commercial ROM.
- CDC-only target also linked/audited: **198384 bytes**, SHA256
  `d83e59d467da83210c34acd8bc202170138a8b884dee21e84d24ecf3886c9ce4`.
- `scripts/build.py firmware --usb-audio --package ...` invokes the existing
  app-only packager after the passed audit. Its two-member package validated;
  an offline plan against a reviewed owner V14 backup contains **50 changed
  sectors**, directory last, with boot/configuration preservation checks.
  No full-ROM candidate or new hardware writer is created.
- Source inventory is **147 files**. Build artifacts, app packages, private
  backups/plans and local logs are excluded. Root/dependency licenses remain
  mixed; the current linked examples are not Apache-only binaries.
- Existing Python/compiler/pinned dependencies were reused. No environment
  install, device operation, flash, reset or repository visibility change.
  Physical enumeration, sustained duplex/concurrent CDC, volume and recovery
  remain unqualified for this port; MDX session results do not certify it.

## Application-only package and jltool wrapper — 2026-10-02

- Added deterministic `fm1-app-v1` packaging with exactly application/manifest,
  bound to the passed application's static audit. No full-ROM generation or
  stock input in the distributable application package.
- Added sparse planning from the owner's private backup and a wrapper invoking
  existing guarded `jluboottool.py` commands. No new USB protocol, interpreter,
  installed packages, automatic reset/retry or device operations.
- **18/18 new synthetic tests passed**, including archive/audit rejection,
  both allocations, growth after a smaller update, cipher/sector boundaries,
  full-slot config preservation, valid-CRC unsupported layouts, stale preimages,
  write/readback failures and directory-last ordering.
- **40/40 source tests and 25/25 NES plus 27/27 USB host tests passed**. Existing
  pinned dependency checkouts were selected through the documented environment
  variables after the first host invocation rejected missing default paths.
  No dependency was installed. The existing MSVC code-page warning is non-fatal.
- Private, offline comparison against the old full-image transform: **all 49
  changed sectors match byte-for-byte for both 010 and V14 baselines**, using
  the previously audited 198480-byte diagnostic application. All other sectors
  are unchanged. The old transform was used in memory only for this comparison;
  the new planner never constructs a full candidate. No private bytes were
  added to the source inventory.
- The transferred source patch applied to a separate local upstream checkout
  and reproduced the exact existing guard-file/helper hashes. Existing bench
  checkout also passed the read-only tool check; it was not modified.
- Source inventory: **128 files**. Generated `.fm1app` packages, private plans,
  sector/restore files, backups, logs and external loader blobs remain excluded.
- These results qualify offline behavior only. No write/reset/USB command was
  performed and the new wrapper/application remains **hardware-unqualified**.

Earlier dated records below remain historical evidence for their own revisions.

Local verification on 2026-09-29, Windows, Python 3.11, Visual Studio 2022/MSVC
19.44 and existing Jieli clang 4.0.1/pi32v2 tools. Dependencies were clean at the
README pins. No newly installed environment and no device operations.

- `python scripts/build.py host`: **25/25 NES tests and 27/27 USB/peripheral tests
  passed**. These include generated mapper-0/mapper-3 diagnostics, LCD ownership
  and packing, paced key scanning, audio/effects and digital volume tests.
- `python scripts/build.py firmware`: **passed**, with the generated original
  diagnostic ROM, not a commercial ROM. Application size: **198,480 bytes**.
- Boot/memory/power/ROM static audit: **passed**. Power-init audit verifies 1,082
  bytes after checked relocation normalization. No raw stock dump is required.
- `python -m unittest discover -s tests -v`: **5/5 packaging checks passed**,
  including rejection of binary/credential samples, unsafe paths and ignore-list
  drift, and exclusion of unlisted ROMs/generated C files/private data.
- Application SHA-256:
  `a8bbb8f3cd4e44bf784cbff8a174da9d0de121d0e79a00bc2ef76c4f7ec1b663`.
- Generated diagnostic ROM SHA-256:
  `def4ba164d061280c20ae77cdaa921eede2b063c542a3ab2506932b7372d0f69`.

MSVC emitted code-page warnings for external UTF-8 headers/source; builds and
tests completed. Hashes describe this local build, not a promise of byte-identical
outputs across different compiler installations or paths.

Original runtime source was carried into the export with its latest input/LCD
fixes. Export-only changes replace private build paths and stock-dump inputs,
select/hash-check the local ROM, use a generic serial label, and omit unused
stock patch assembly and game-dependent tests. The original workspace and its
installed firmware were not changed.

Build success is **not** hardware acceptance or full-image packaging. This
application has not been flashed; boot/display/audio on hardware remain untested
for the clean diagnostic artifact. Existing private backups and flashing tools
are intentionally outside this release. See THIRD_PARTY.md for provenance;
source sanitization is not a clean-room or comprehensive legal clearance claim.

## Starting-guide command checks — 2026-09-30

No runtime source was changed for these checks. Existing pinned dependencies
and the installed toolchain were reused; no device operations were performed.

- USB-only: `python firmware/usb-diag/build.py --controller 0 --out build/usb-first`
  **passed** its build/static audit. Application: **129,392 bytes**, SHA-256
  `aa8e5a484465785f7f29a0cc3efd28a5618316af9193f197a15531df43da5ebd`.
  No NES ROM or peripheral tests included. Hardware acceptance remains pending.
- Standalone peripherals: the command shown in GETTING_STARTED.md **failed**
  the static audit with `USB trace merged-global offset changed: 240` after
  linking. This profile is not qualified; checks were not disabled or relaxed.
- The earlier complete NES-example result is a different build profile; it
  does not imply that every combination of build flags is audited successfully.
- Source inventory/packaging tests: **5/5 passed** after adding the guide.
- README/guide local document links and heading anchors were checked.

## Publication preparation checks - 2026-09-30

- Source-release/attribution tests: **16/16 passed**, including historical
  credential detection after removal, annotated-tag messages, historical
  alternate filenames, tracked-inventory drift, shallow-checkout refusal and
  repeatable archives without overwriting prior candidates.
- Rebuilt host targets: **25/25 NES and 27/27 USB/peripheral tests passed**.
- Rebuilt the complete diagnostic example using the same external pinned SDK,
  NES core and existing compiler: **build/static audit passed**. Output in
  `build/publication-check` is **198,480 bytes**, SHA-256
  `a8bbb8f3cd4e44bf784cbff8a174da9d0de121d0e79a00bc2ef76c4f7ec1b663`,
  identical to the prior diagnostic application. Generated upstream sources
  now carry project modification notices; runtime logic was not changed.
- Allowlist: **117 source/document/workflow files**. The new Git check also
  scans local reachable historical blobs and commit/tag messages with limited
  patterns. These checks do not establish code ownership or inspect all hosted
  GitHub surfaces. CI uses the same source-only checks and uploads no artifacts.
- PROVENANCE.md maps the reviewed SDK interfaces and retained board findings.
  The LCD table's stock origin is explicitly preserved, not reassigned to the
  SDK. PUBLICATION.md records unresolved source-publication decisions separately
  from binary-distribution and hardware qualification gates.

No SDK/toolchain installation, firmware flashing, device access, visibility
change or legal sign-off was performed. The standalone peripheral-profile audit
failure above remains unresolved; the passing example is a different profile.

## LCD reference review - 2026-09-30

- Compared all 21 local LCD records with the three pinned SDK S/V/T3
  initializers: **10 exact candidate matches**. Both local arrays retain SHA-256
  `280cb746088bea4a2fce2819c1415da0597a286120e3a8229449fbafdc1280c7`.
  See LCD_PROVENANCE.md for the full map and manual datasheet review.
- `python -m unittest discover -s tests -v`: **22/22 passed**. Six new checks
  cover the literal parser, delayed row, unused B2 byte, table identity/hash and
  complete report row coverage. These tests do not verify datasheet interpretation.
- `python scripts/build.py host`: **25/25 NES and 27/27 USB tests passed** after
  setting the documented dependency environment variables to existing pinned
  checkouts. An initial invocation without those variables stopped at the
  missing default `.deps/peak-nes` path; nothing was downloaded or installed.
- Source allowlist expanded to **120 files**. Reference PDFs and rendered pages
  remain ignored local research inputs, not release contents.
- No changes under `firmware/` relative to publication-preparation commit
  `0907a48`. No new firmware build, flash, device test or visibility change was
  performed for this documentation/offline-audit update. Earlier firmware build
  evidence above remains separate from this review.

## Remaining publication audit - 2026-09-30

- Pinned dependency licenses and selected adaptation notices reviewed; five
  generated adaptations retain modification notices and the two NES adaptations
  retain upstream copyright headers. No toolchain redistribution grant claimed.
- Boot/power comparison and the SDK-derived instruction-template boundary are
  recorded in PUBLICATION_AUDIT.md. No firmware or static-audit logic changed.
- Fetched advertised PR head refs and the available PR merge ref for the local
  history check. Baseline scan: **9 commits / 149 objects**, including that merge.
- GitHub snapshot: four branches, no tags, three issues, three PRs, four comments,
  four CI run logs. No configured secret-pattern hit or attachment link. No
  releases, uploaded artifacts, deployments or forks; wiki/Pages/Discussions off.
  This is a dated bounded review, not a guarantee about inaccessible/deleted data.
- **22/22 source tests and 25/25 NES plus 27/27 USB host tests passed** again.
  Existing pinned dependencies/toolchain reused; MSVC's known code-page warning
  remained non-fatal. No new target firmware build or hardware acceptance claimed.
- Source manifest now contains **121 files**. Audit evidence remains ignored
  under `local/`; the public report includes findings, not private logs.
- No history rewrite, file deletion, firmware change, device operation or
  visibility change. No concrete history-removal target identified by this audit.
