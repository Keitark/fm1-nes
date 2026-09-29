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
