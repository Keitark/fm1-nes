# Provenance and redistribution boundaries

Project-authored material is offered under Apache-2.0 to the extent we hold the
necessary rights; see LICENSE and the source-reference map in PROVENANCE.md.
This does not relicense other parties' code, firmware, trademarks or game assets.
Review ownership of any future additions before publishing them.

## External dependencies

- **PeakRacing NES**, copyright PeakRacing, Apache-2.0.
  Upstream: https://github.com/PeakRacing/nes
  Pinned revision: `68bdfc8de570264c0e84f73766f1a1ed3591066f`.
- **Jieli AC79 SDK**, from Jieli-Tech, repository license Apache-2.0.
  Upstream: https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK
  Pinned revision: `e30b1ee375d1f2993fc23bf92c8b99006a6e5f9d`.
  Repository-level licensing does not replace individual notices or separately
  supplied library/toolchain terms. The SDK includes precompiled libraries used
  by the build. No SDK files or libraries are bundled in this source archive.
- **Jieli pi32v2 compiler/toolchain**: externally installed; not bundled and no
  redistribution rights are asserted here.
- **kagaimiq/jl-misctools**, copyright 2023 Andrey Grigoryev, MIT.
  Upstream: https://github.com/kagaimiq/jl-misctools
  Revision: `0a5b12db0ef38f3042acffbe2452730a37fd2405`.
  `scripts/jl_formats.py` adapts ENC/SFC and stored encoding-metadata routines
  from `firmware/jltech/{cipher,chipkeybin}.py`, with bounded FM-1 parsing and
  sparse planning. CRC-16 uses standard `binascii.crc_hqx`. No upstream extraction
  CLI, stock data or actual device encoding value is bundled.
- **kagaimiq/jl-uboot-tool**, copyright 2023 Andrey Grigoryev, MIT source.
  Upstream: https://github.com/kagaimiq/jl-uboot-tool
  Revision: `adb3f18889e88ac512ce0a3c4d8cc3d3cb30696a`.
  `tools/jltool-fm1-guards.patch.txt` transfers existing bench modifications for
  strict identity/transfer checks, 256-byte I/O, scoped sector writes and skipped
  optional chip-key query. Its upstream source context is MIT licensed.
  `scripts/jltool_update.py` calls the external patched tool, not a new USB writer.
  Tools/loader binaries are not bundled; source licensing is not asserted to
  license vendor-derived loader blobs.

`licenses/kagaimiq-MIT.txt` retains the MIT copyright/license notice for these
adaptations and patch context. Retain the external tool's original LICENSE too.

`licenses/Apache-2.0.txt` contains the dependency license text. Build-time overlays
in `firmware/usb-diag/vendor_overlay.py` adapt the pinned SDK USB implementation
and NES rendering/APU implementation without modifying upstream checkouts.
Generated copies retain upstream headers and carry a prominent FM-1 project
modification notice. The overlay script itself contains upstream match fragments
under their applicable terms. Overlay substitutions are local modifications,
not upstream releases; generated copies are excluded from this
archive. If distributing linked binaries later, separately review and satisfy
all dependency/library notices and ROM redistribution rights.

The host build-audit scripts also contain instruction-byte reference templates,
not only hashes: some check SDK startup code and others check project-compiled
wrappers. No complete SDK library or executable patch is included, but these
SDK-derived reference sequences are part of the source review. See
PUBLICATION_AUDIT.md for their origin and the separate linked-library boundary.

## MDX USB port added 2026-10-02

Generic USB audio bridge/profile/target, atomic packet submission, packet audit
and tests are reused/adapted from `Keitark/fm1-mdx` at
`41410578152eec195b534b3acfe2fa1b10e7476e`. Its root LICENSE is GPLv3; imported
files are conservatively marked **GPL-3.0-only**, not Apache or MIT. The complete
license is `licenses/fm1-mdx-GPL-3.0.txt`. MDX-derived CDC overlay, task/session
and composite descriptor/setup-policy portions have those terms too; original notices remain.
No MDX/YM2151/sequencer code, songs, recordings or proprietary firmware are
included by this port.

Both current CDC-only and composite firmware link the reused packet helper.
Their combined binaries must not be described as Apache-only or MIT; GPLv3
and retained Apache/dependency notices apply. Imported host audit/tests retain
their license. The root Apache license remains for the material it covers,
not a relabeling of imported code. Generated binaries are excluded from this
source release; SDK/toolchain/cartridge redistribution boundaries still apply.

## Hardware research and scope

Board-specific register values, LCD initialization data, key decoding and power
parameters were recovered through investigation of the FM-1's behavior/firmware.
In particular, the two `panel_init` arrays retain a 21-record table recovered
from FM-1_010. Excluding full stock images does not mean that no stock-derived
data remains. Its publication review is recorded separately in PUBLICATION.md.
This is **not a claimed clean-room implementation**. The public source retains
that provenance and does not include stock ROMs, raw disassembly, executable
stock firmware patch payloads, chip keys, downloaded vendor archives or private
evidence logs. The newly included jltool patch modifies MIT Python source only.
Power verification here checks the pinned SDK's generated instructions and
reviewed parameters, not a redistributed stock image.

Official SDK documentation and community research, including
[AL-255/FM-1-RE](https://github.com/AL-255/FM-1-RE), are technical references.
A link is not a claim that this project's existing implementation originated
there, nor permission to redistribute third-party firmware hosted elsewhere.
PROVENANCE.md distinguishes documented chip APIs from FM-1-specific findings.

The diagnostic ROM generator is original project source: checkerboard graphics,
pulse sound and controller checks, with no Nintendo/game assets. No commercial
ROM is included. The user must supply any other ROM locally and determine their
rights to use or distribute it. Brand references identify compatibility only;
this project has no claimed endorsement by M-VAVE, Jieli, Nintendo or PeakRacing.
