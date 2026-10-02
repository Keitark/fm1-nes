# Application-only updates

Experimental source/tool workflow, not an official M-VAVE updater. The new
wrapper is offline/synthetic-tested, **not hardware-qualified**. Existing private
flashing tools and rollback artifacts are unchanged. No new Python environment,
USB writer, dependency installer or elevation server is created.

**V14 bench result (2026-10-03):** the public packager/planner plus the existing
private elevated Jieli writer installed an audited application in 51 changed
sectors, verified one complete final readback, preserved boot/config/reserved
bytes, then reset into live composite USB/CDC. Serial UBOOT entry worked.
This qualifies that bounded programming experiment, **not** every standalone
wrapper command or every firmware revision. The wrapper below additionally
performs a fresh preflight read; the established bench broker reused its verified
baseline instead. Do not describe these host orchestration paths as identical.
See [VALIDATION.md](VALIDATION.md) for remaining physical acceptance gates.

## Package and preserved layout

`scripts/app_package.py` creates a deterministic `.fm1app` ZIP with exactly
`app.bin` and `manifest.json`. The manifest contains layout/format identifiers,
CPU entry, length, SHA-256, static-audit status and `hardware_qualified: false`.
It copies no private build-report fields and reads no stock backup. SHA-256 is
integrity checking, not a signature: only use trusted, reviewed builds.

| Physical flash | Update |
| --- | --- |
| `0x0000..0x3FFF`, existing boot/header/config | Never written |
| `0x4000..0x401F`, area header | CRC fields only |
| `0x4020..0x403F`, app record | Size and CRC fields only |
| `0x4040..0x411F`, other records/prefix | Byte-identical |
| `0x4120..`, application | New application bytes only |
| Unused old app tail, cfg_tool, reserved data | Byte-identical |

Application CPU entry stays `0x02000120`, not a physical flash offset. Only the
reviewed 010/V14 layouts (583228/584956-byte allocations) and existing bootloader
code hash are accepted. Capacity comes from the preserved config boundary, so a
small installed application can later be replaced with a larger one. Unexpected
layout/bootloader is a stop condition; do not force an update.

`app.bin` byte zero maps to physical flash **`0x4120`**, after validated encoding,
not to `0x0000` or `0x4000`. Application-relative offset `0x120` is relative to
the application area at `0x4000`. CPU addresses are a third address space.
The file must go through this planner, not a bare `write 0x4120 app.bin`.
The application can link SDK runtime/RTOS libraries; it does not contain a
copied stock bootloader. A full linked app build and sparse flashing are distinct.

## Offline package and plan

For the MDX-derived USB-audio/CDC profile, build and package in one offline
command: `python scripts/build.py firmware --usb-audio --package build/audio-v1.fm1app`.
This calls the same app-only packager, not a different writer. See
[USB_AUDIO.md](USB_AUDIO.md). Raw app.bin must not be written directly.

Use the existing Python 3.11 installation. Package/plan need only its standard
library and never contact USB:

```powershell
python scripts/app_package.py --app build/firmware/fm1-usb-diag.app.bin --audit build/firmware/static-audit.json --output build/app-v1.fm1app
python scripts/jltool_update.py plan --package build/app-v1.fm1app --baseline local/owner-backup.bin --baseline-sha256 YOUR_BACKUP_SHA256 --out local/plan-v1
```

The audit must pass and match the application's entry, size and hash. A passed
audit does not prove hardware boot. The baseline is your private, verified 1 MiB
raw backup, not an updater container or another device's image. No backup is
bundled. Keep a separate original recovery backup across all later updates.

The planner reads/validates necessary metadata and the application area in
memory, updates size/CRCs, and prepares only changed 4 KiB sectors. It **does not
construct or save a full candidate ROM**. Existing encoding metadata is used
only in memory: no OTP/chip-key query, logging or serialized encoding value.
This does not bypass device access controls; stop on any access/key rejection.

`local/plan-v1` contains a sanitized `plan.json`, changed sector files and matching
restore sectors. These contain unit-derived/stock bytes preserved in shared
erase sectors. **Keep this whole directory private**, along with backups and
flash logs. Only the `.fm1app` is application-only. It can still contain linked
SDK/game code; review binary notices/redistribution rights before sharing it.
The source-release archive excludes all generated packages, plans and binaries.

## Existing Jieli tool and source patch

The wrapper calls the same guarded `jluboottool.py` used by the bench workflow;
the USB protocol remains inside that tool. Supply an existing compatible Python
environment and an external [kagaimiq/jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool)
checkout at `adb3f18889e88ac512ce0a3c4d8cc3d3cb30696a`.
The external tool's Python requirements remain prerequisites; no automatic
install, download or patching occurs.

Apply the transferred source-only guards to a **separate clean checkout** at
that revision (do not apply again to the already-patched bench checkout):

```powershell
$patchPath = (Resolve-Path tools/jltool-fm1-guards.patch.txt).Path
git -C .deps/jl-uboot-tool apply --check $patchPath
git -C .deps/jl-uboot-tool apply $patchPath
```

The wrapper verifies the external Git revision, modifications/untracked files,
normalized guard-file hashes and WL82 RAM-helper hash. No loader blob is bundled.
The patch and adapted format routines carry MIT notices in THIRD_PARTY.md and
`licenses/kagaimiq-MIT.txt`. Retain upstream LICENSE too. MIT source terms do not
automatically license vendor-derived RAM-loader binaries; review those separately.

## Explicit hardware commands

Prepare physical recovery first; use stable power and the exact FM-1 disk path.
Do not guess `PHYSICALDRIVE3`: the commands below are examples. Every invocation
checks `WL82 UBOOT1.00 1.00` and SPI NOR ID `0x856014`. Windows raw-disk access
may require elevation: use the existing elevated terminal/session and interpreter.
This wrapper does not change the existing persistent broker or configure UAC.

After entering UBOOT, upload the existing RAM helper **once**, then read:

```powershell
python scripts/jltool_update.py load-loader --jltool .deps/jl-uboot-tool --device \\.\PHYSICALDRIVE3 --out local/load-v1
python scripts/jltool_update.py backup --jltool .deps/jl-uboot-tool --device \\.\PHYSICALDRIVE3 --out local/read-v1
```

The backup command creates `local/read-v1/backup.bin` and prints its hash. Use
that fresh backup with offline `plan`. Power-cycling invalidates the running
helper; never use reuse-loader operations until it is loaded again.

Review the plan/hash. Writing requires a separate explicit command:

```powershell
python scripts/jltool_update.py flash --package build/app-v1.fm1app --baseline local/read-v1/backup.bin --baseline-sha256 YOUR_BACKUP_SHA256 --approve-plan PLAN_SHA256 --jltool .deps/jl-uboot-tool --device \\.\PHYSICALDRIVE3 --out local/write-v1 --write
```

The plan is recomputed and approval mismatch rejected before device I/O. One
fresh full preflight read must match the baseline; each sector preimage is also
checked. The existing CLI erases only the requested 4 KiB sector, programs in
256-byte chunks and verifies erase/program readback. The wrapper independently
checks sector readback and writes the directory sector last. One final full
readback is compared sparsely, with no full candidate created.

Every run directory must be fresh. No automatic retry, rollback or reset occurs.
This is not atomic: interruption can leave an unbootable application. On failure,
stay in UBOOT/recovery; do not blindly rerun with a stale backup or boot the
partial update. Partial-failure recovery is not implemented by this new wrapper.
Keep receipts private and use the independently reviewed recovery workflow.

After successful readback, reset is a separate command:

```powershell
python scripts/jltool_update.py reset --jltool .deps/jl-uboot-tool --device \\.\PHYSICALDRIVE3 --out local/reset-v1
```

A completed reset or USB disconnect is not boot verification. Test screen,
audio, controls and serial UBOOT entry separately on the bench.

The existing CLI can report a CP932/UTF-8 log-decoding exception after a reset
already reached the device. An ambiguous reset log is not permission to resend
reset or rewrite flash: check actual disappearance/re-enumeration and normal
serial replies first. If normal boot cannot be confirmed, retain recovery state.
