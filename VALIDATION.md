# Source-release validation

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
