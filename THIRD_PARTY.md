# Provenance and redistribution boundaries

Project-authored source in this export is offered under Apache-2.0; see LICENSE.
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

`licenses/Apache-2.0.txt` contains the dependency license text. Build-time overlays
in `firmware/usb-diag/vendor_overlay.py` adapt the pinned SDK USB implementation
and NES rendering/APU implementation without modifying upstream checkouts.
Generated copies retain upstream headers. Overlay substitutions are local
modifications, not upstream releases; generated copies are excluded from this
archive. If distributing linked binaries later, separately review and satisfy
all dependency/library notices and ROM redistribution rights.

## FM-1 reverse-engineering boundary

Board-specific register values, LCD initialization data, key decoding and power
parameters were recovered through investigation of the FM-1's behavior/firmware.
This is **not a claimed clean-room implementation**. The public source retains
that provenance and does not include stock ROMs, raw disassembly, firmware
patch payloads, chip keys, downloaded vendor archives or private evidence logs.
Power verification here checks the pinned SDK's generated instructions and
reviewed parameters, not a redistributed stock image.

The diagnostic ROM generator is original project source: checkerboard graphics,
pulse sound and controller checks, with no Nintendo/game assets. No commercial
ROM is included. The user must supply any other ROM locally and determine their
rights to use or distribute it. Brand references identify compatibility only;
this project has no claimed endorsement by M-VAVE, Jieli, Nintendo or PeakRacing.
