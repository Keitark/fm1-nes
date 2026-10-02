# ぼくがかんがえたさいきょうのファミコンゲーム — NROM example

An optional horizontal-scrolling shoot-'em-up authored by the maintainer with
Claude Code assistance. The maintainer identified this project and authorized
its original source and generated game assets under **Apache-2.0** on
2026-10-03; see the repository's [LICENSE](../../LICENSE). This is not a Nintendo
game and no commercial ROM/assets or external toolchain are bundled.

This directory contains the **mapper-0 NROM** edition: 32 KiB PRG and genuine
8 KiB CHR ROM. Its fixed pattern atlas, sprite HUD and single scroll speed
avoid MMC3 bank-switching/scanline IRQs. The original mapper-4 edition is not
included and is unsupported by the current FM-1 example.

The game has five stages, stage music/SFX, bosses, scoring, pause and a loop.
D-pad moves, A shoots, Start begins/pauses. On FM-1, A is the upper G key and B
the upper F key; use the existing lower direction/start/select assignments.
Format/build acceptance is not full gameplay or performance qualification.

## Build the cartridge locally

Use existing Python 3 and an external cc65 bin directory containing `ca65`
and `ld65` (Windows `.exe` names also accepted). No download/install/venv,
emulator executable or FM-1 device operation is performed.

From the FM-1 repository root:

```powershell
python examples/fablenes/build.py --cc65-bin 'D:/tools/cc65/bin'
$rom = (Resolve-Path 'examples/fablenes/build/game_nrom.nes').Path
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rom).Hash.ToLowerInvariant()
python scripts/build.py firmware --usb-audio --rom $rom --rom-sha256 $hash --out build/homebrew-nrom --package build/homebrew-nrom-v1.fm1app
```

Change the external tool path to your existing installation. The source asset
generators use only Python's standard library: authored bitmap glyphs, ASCII
sprite grids, procedural backgrounds and APU note streams become local CHR,
nametable, palette, music and preview files. `gen_all.py` supplies supporting
metasprite/music tables; the NROM engine loads `nrom_chrrom.bin`, not its MMC3
CHR banks. No external artwork/font/music file is read by these generators.

Generated data goes under ignored `examples/fablenes/build/`; compiled FM-1
output goes under ignored top-level `build/`. The cartridge is 40976 bytes.
The builder rejects an existing ROM output: choose a fresh `--out` path for
another build, e.g. `--out examples/fablenes/build/game_nrom-v2.nes`.
Other local generator intermediates are regenerated normally.

The original local cartridge's SHA-256 is
`8dbe33a3f00d76d88c4618917833f3a9dbb198b2de3ee684a4c59a2cc4bdc687`.
Recompute it for your actual build; source versions/toolchains may change it.
The build validates iNES shape and the interrupt/reset vectors using the FM-1
embedder plus game-specific checks. No generated ROM, preview, object or
firmware is tracked or included in the source ZIP, even though the game's
original assets have the stated license. cc65 retains its own external terms.

Follow [ROM_GUIDE.md](../../ROM_GUIDE.md) and [APP_UPDATES.md](../../APP_UPDATES.md)
to install the rebuilt application through a reviewed private sparse plan.
Do not write the `.nes` file or raw `app.bin` directly into flash. Physical
FM-1 gameplay/audio acceptance is a separate bench check.
