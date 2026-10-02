# Remaining publication audit

## Application-update tooling follow-up — 2026-10-02

The application-only packager, bounded sparse planner and existing-jltool wrapper
are now included as source. The earlier snapshot below predates this addition.
MIT jl-misctools routine adaptations and the transferred MIT jl-uboot-tool Python
source patch are attributed in THIRD_PARTY.md with a license copy. No vendor
loader, full stock image, unit-derived sector plan or generated app package is
added to the source inventory. New FM-1 geometry/hash checks retain their actual
stock-research provenance. The new hardware execution path is not bench-qualified;
technical results are recorded in VALIDATION.md. Private visibility is unchanged.

Date: 2026-09-30. Reviewed baseline: `a1a7fae`, with this documentation-only
follow-up. Scope: the source candidate, pinned dependencies relevant to included
adaptations, boot/power provenance and available GitHub publication surfaces.
This completes the bounded engineering/publication review, not a legal opinion,
exhaustive authorship certification or approval to change visibility.

## Outcome

- No credential-pattern hit, prohibited full binary, stock dump, commercial ROM
  or private attachment was identified in the checked source/history/surfaces.
  Limited scans cannot establish universal absence of sensitive information.
- The reviewed upstream source adaptations have identifiable Apache-2.0 terms;
  license copies and modification notices are present.
- One attribution gap was corrected in documentation: audit scripts include
  **instruction-byte reference sequences as well as hashes**. Some reference
  SDK startup code. Source-only must not be read as zero SDK-derived content.
- The stock-derived LCD/boot/power findings remain honestly identified. Public
  documentation corroborates interfaces, not the origin of this implementation.
- No concrete history-removal target was found. Preserve private development
  evidence; do not rewrite history merely to make provenance less visible.

## Source licenses and acquisition evidence

| Input | Evidence examined | Conclusion for this candidate |
| --- | --- | --- |
| PeakRacing NES, `68bdfc8de570264c0e84f73766f1a1ed3591066f` | Pinned LICENSE, `src/nes.c`, `src/nes_apu.c`, tree notice filenames, generated adapted files | Apache-2.0 headers identify Copyright PeakRacing. Generated copies retain these and project modification notices. No separate NOTICE file found in this tree. |
| Jieli AC79 SDK, `e30b1ee375d1f2993fc23bf92c8b99006a6e5f9d` | Pinned LICENSE/README-en.md, USB files `cdc.c`, `usb_device.c`, `msd_upgrade.c`, power headers and demo configuration, notice-file inventory | Root declares Apache-2.0. The three adapted USB files have no additional license/restriction notice detected. No root or ancestor NOTICE applies to those paths; unrelated components have their own notices. This is not a license audit of the entire SDK. |
| SDK header `asm/p33.h` | Header and selector enums | Contains a JIELI copyright notice. It stays external and unmodified; do not remove its header when distributing a copy. |
| Build overlays | `vendor_overlay.py`, five generated files in the previous verified build | All five carry project modification notices. Both NES copies retain upstream copyright/license headers. THIRD_PARTY.md credits the match fragments included in the overlay script itself. |
| Jieli toolchain | Official installation page and installed file inventory | External prerequisite, not bundled. An installation guide is not an exhaustive toolchain EULA or redistribution grant. Installer-specific terms were not established by this review. |
| Vendor firmware/updater | M-VAVE download landing page and maintainer statement | Public update downloads exist, but no redistribution grant was identified on the inspected landing page. No vendor archive or updater is distributed here. Historical installer/download terms and access-method legality are not independently established. |
| Community research/tools | README/guide reference links and source manifest | Links are references, not a sublicense or a claim of origin. Their repositories, firmware assets and tools are not bundled by this release. |

The maintainer reported: **"No NDA or private agreement that I know of"**.
That qualified report is recorded, not broadened to cover every installer or
public-download condition. This audit did not download or execute new installers.

The two bundled Apache license files are identical. The redistribution review
uses the license's section 4 requirements: provide the license, retain applicable
notices, mark modifications and retain applicable NOTICE attributions when one
is supplied. No new third-party license grant is inferred.
[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

Primary acquisition/license references:

- [Pinned PeakRacing license](https://github.com/PeakRacing/nes/blob/68bdfc8de570264c0e84f73766f1a1ed3591066f/LICENSE).
- [Pinned SDK license](https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK/blob/e30b1ee375d1f2993fc23bf92c8b99006a6e5f9d/LICENSE)
  and [SDK README](https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK/blob/e30b1ee375d1f2993fc23bf92c8b99006a6e5f9d/README-en.md).
  Reviewed from existing pinned Git blobs; the Gitee web renderer was unavailable.
- [Jieli environment guide](https://doc.zh-jieli.com/Tools/zh-cn/dev_tools/dev_env/index.html).
- [M-VAVE downloads](https://www.m-vave.com/download). Landing-page review only;
  no claim that absence of displayed terms proves absence of obligations.

## Boot and power: what the public references establish

Local `boot_compat.c` copies six words into a 23-word temporary argument, zeros
the extension, then calls the SDK initializer. The Windows host test places the
six-word input against a protected page and checks its immutability. This tests
the adapter contract; it does not independently establish the stock boot ABI.
The previous build map resolves `boot_info_init` to `cpu.a(boot.c.o)`.

The inspected [UBOOT guide](https://doc.zh-jieli.com/AC79/zh-cn/release_v1.2.0/module_example/system/UBOOT%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E.html)
describes bootloader selection/debug variants, not that six-to-23-word contract.
Keep the stock-analysis origin for this adapter. Do not relabel it SDK-documented.

Power comparison uses pinned `include_lib/driver/cpu/wl82/asm/{power_interface.h,p33.h}`
and `apps/demo/demo_hello/{board/wl82/board.c,include/app_config.h}`:

| Existing FM-1 setting | SDK support / example comparison | Remaining board-specific point |
| --- | --- | --- |
| `power_init(struct low_power_param *)` | Public API and demo board call | The SDK call is reused, not a transplanted stock function. |
| `config=0`, `btosc_disable=0` | Same demo macro values | Intended board power policy. |
| `VDDIOM_VOL_32V` | Named enum; same demo selection | Actual PCB rail topology. |
| `VDDIOW_VOL_32V` | Named enum; demo uses it conditionally for RTC | Applicability to this PCB. |
| `vdc14_dcdc=1` | Demo also enables it | Actual supply arrangement. |
| `VDC14_VOL_SEL_160V` | Valid named enum; demo selects 140V | FM-1 selection is not justified by the demo default. |
| `SYSVDD_VOL_SEL_138V` | Valid named enum; demo selects 126V | FM-1 selection is not justified by the demo default. |
| `VLVD_SEL_26V`, enable=1 | Named enum; demo enables reset at 25V | Threshold choice remains board-specific. |
| Other zero input fields | Local comments identify unused inputs for the reviewed SDK path | Not reconstructed stock source values. |

The official [voltage configuration guide](https://doc.zh-jieli.com/AC79/zh-cn/release_v1.2.0/module_example/system/VDDIO_SYSVDD_DCDC14%E7%B3%BB%E7%BB%9F%E7%94%B5%E5%8E%8B%E9%85%8D%E7%BD%AE%E8%AF%B4%E6%98%8E.html)
explains the configuration interfaces and hardware-dependent choices. It does
not qualify the FM-1 PCB. No voltage, timing or initialization change is proposed.

## Audit constants and linked libraries

`firmware/nes/audit_boot.py` includes literal instruction templates. In the
verified build map, startup comes from `cpu.a(startup.S.o)`. That template is
SDK-derived build evidence, not a stock firmware image. Other templates check
project-compiled boot/trace wrappers. `audit_pre_os.py` contains a project wrapper
template and an SDK-linked main hash. `audit_power.py` uses a normalized SDK
function hash, relocation expectations and short instruction encodings.

These are host-side comparisons, not executable patch payloads, but they are
still included material whose origin must be disclosed. The SDK-derived byte
templates belong in the source-publication decision too; merely excluding `.a`
files does not remove them. No determination that these constants are infringing
or require exclusion is made. No audit was weakened or replaced in this review.

Linked inputs are listed in PROVENANCE.md. The official
[library guide](https://doc.zh-jieli.com/AC79/zh-cn/release_v1.2.0/module_example/system/lib_info.html)
describes library functions, not complete component-level redistribution terms.
Newlib headers also carry component-specific notices. A future binary release
needs an exact linked-component/notice review; this source release does not
distribute the SDK archives, compiler, generated application or commercial ROM.

## GitHub and history snapshot

Read-only authenticated API inventory was paginated. Snapshot taken before this
follow-up commit; rerun if hosted content changes before publication.

| Surface | Result |
| --- | --- |
| Visibility | Private |
| Branches / tags | Four branches; no tags |
| Pull-request refs | Three PR heads and available PR #6 merge ref fetched into local audit refs; included in history scan |
| Reachable baseline history | Nine commits including the generated merge, 149 unique scanned objects; source checks passed |
| Issues / PR descriptions | Three issues and three PRs; bodies reviewed |
| Conversation comments | Four; reviewed, with no attachment link detected |
| Review bodies / inline review comments / commit comments | None |
| Actions | Four completed runs; all logs retrieved and pattern-scanned, 101,294 characters total |
| Releases / release assets / Actions artifacts / deployments | None |
| Forks | None returned |
| Wiki / Pages / Discussions | Disabled |

Checked CI runs: `36599700814`, `36599757026`, `36601899505`, `36601906100`.
No hit in the configured credential/private-path patterns. Discussions contain
technical review, hashes and the already-recorded qualified acquisition response,
not raw dumps. CI is read-only, SHA-pinned, disables persisted checkout credentials,
builds only the source package, and has no artifact-upload step.

Limits: this is a point-in-time visible-surface review, not GitHub's internal
storage, deleted edits, inaccessible caches, every possible token format or
third-party clones. A public release also exposes commit metadata and hosted
discussions; do not assume a squash hides those surfaces. Raw API evidence/log
processing stays under ignored `local/`, not in this source archive.

## Decision after the audit

There is no identified reason to purge history now. The maintainer can either
accept a truthful experimental-source release with the documented research
origins, obtain focused advice/permission for the retained material, or request
a reduced/reimplemented release. That decision concerns the LCD table, boot ABI,
board-specific findings and SDK-derived audit templates; it cannot be made by
a secret scanner or by deleting their history.

Keep the repository private until that decision and separate visibility approval.
Binary redistribution, USB identity and hardware qualification remain future
product gates, not completed checks for this source-only candidate.
