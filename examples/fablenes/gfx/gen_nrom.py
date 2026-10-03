# SPDX-License-Identifier: MIT
# Copyright 2026 Keitark. Maintainer-authored, Claude Code-assisted game.
# Published with maintainer authorization; see examples/fablenes/README.md.
"""Generate NROM (mapper 0, no extra chip, REAL CHR-ROM) build data.

This is the real-hardware-compatible edition: unlike the earlier CHR-RAM
draft, the PPU pattern tables are honest-to-goodness read-only CHR-ROM,
baked into the .nes file and never written at runtime (some NROM flashcart
boards, including WiFi-loader carts, only have CHR-ROM silicon - no SRAM to
write into). That means BOTH pattern tables (4KB BG + 4KB sprite = 512
tiles total) must hold EVERY scene's graphics simultaneously, for the whole
game session:

  - Sprites (<=256 tiles): the existing gameplay sprite sheet (150 tiles)
    plus the title's kana logo, now rendered as sprites instead of BG tiles
    (freeing the whole BG half for backgrounds; sprites are a separate 4KB
    half so this doesn't compete with the world's tile budget).
  - Background (<=256 tiles): a single shared atlas used by title + all 5
    stages. Stars and nebula are generated ONCE and reused everywhere (only
    the palette differs per stage - same trick real NES games use to reskin
    a location); each stage's terrain keeps its own distinct shape but is
    cropped to a narrower strip and tiled to bound its unique-tile cost.

Only the nametable + palette differ per scene now (both are ordinary
writable PPU RAM regardless of mapper) - CHR is 100% static from power-on.

Run: python gfx/gen_nrom.py
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art                                            # noqa: E402
from gen_all import (paint_stars, paint_nebula, paint_terrain,             # noqa: E402
                      paint_terrain_lava, paint_terrain_organic,
                      paint_terrain_ice, paint_terrain_fortress,
                      paint_planet, cut_tiles, tile_to_chr, tkey, BLANK,
                      NESPAL, write_png, SPR_PAL, STAGE_SPR_PALS)
from fontdata import glyph_bitmap, latin_tile, TITLE_LINES               # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
os.makedirs(BUILD, exist_ok=True)

TITLE_PAL = [0x0F, 0x11, 0x21, 0x30,      # 0: stars
             0x0F, 0x01, 0x2C, 0x30,      # 1: logo (navy shadow, cyan, white)
             0x0F, 0x07, 0x17, 0x27,      # 2: planet ambers
             0x0F, 0x00, 0x10, 0x20]      # 3: credit text

STAGE_PALS = [
    [0x0F, 0x11, 0x21, 0x30, 0x0F, 0x03, 0x13, 0x23, 0x0F, 0x0C, 0x1C, 0x2C, 0x0F, 0x00, 0x10, 0x20],
    [0x0F, 0x11, 0x21, 0x30, 0x0F, 0x06, 0x16, 0x26, 0x0F, 0x07, 0x16, 0x28, 0x0F, 0x00, 0x10, 0x20],
    [0x0F, 0x11, 0x21, 0x30, 0x0F, 0x09, 0x19, 0x29, 0x0F, 0x0B, 0x1B, 0x2B, 0x0F, 0x00, 0x10, 0x20],
    [0x0F, 0x11, 0x21, 0x30, 0x0F, 0x01, 0x11, 0x21, 0x0F, 0x0C, 0x21, 0x30, 0x0F, 0x00, 0x10, 0x20],
    [0x0F, 0x11, 0x21, 0x30, 0x0F, 0x04, 0x14, 0x24, 0x0F, 0x00, 0x10, 0x16, 0x0F, 0x00, 0x10, 0x20],
]

TERRAIN_PAINTERS = [paint_terrain, paint_terrain_lava, paint_terrain_organic,
                    paint_terrain_ice, paint_terrain_fortress]
# each stage's terrain is generated at this many tile-columns (< 32) and
# tiled to fill the width, bounding its unique-tile cost. Denser painters
# (fortress' crenellations, organic's domes) get a narrower crop.
TERRAIN_CROP_COLS = [12, 12, 10, 12, 10]

NEBULA_SEED = 0x42          # ONE nebula shared by every stage (palette-only reskin)
STAR_SEED = 0x51


class FlatTileSet:
    """Dedup tile container: flat physical indices 0..N-1 (N<=256)."""
    def __init__(self, name, cap=256):
        self.name, self.cap = name, cap
        self.tiles = []
        self.index = {}
        self.add(BLANK)   # index 0 = blank

    def add(self, t):
        key = tkey(t)
        if key in self.index:
            return self.index[key]
        idx = len(self.tiles)
        assert idx < self.cap, f'{self.name}: tile budget exceeded ({len(self.tiles)}/{self.cap})'
        self.tiles.append(t)
        self.index[key] = idx
        return idx

    def chr_bytes(self):
        out = bytearray(self.cap * 16)
        for i, t in enumerate(self.tiles):
            out[i * 16:i * 16 + 16] = tile_to_chr(t)
        return bytes(out)


def nam_from_grid(grid, zone_of):
    """32x30 tile-index grid + zone_of(row,col)->palette(0-3) -> 1KB blob
    (960 tile bytes + 64 attribute bytes)."""
    nam = bytearray()
    for r in range(30):
        nam += bytes(grid[r])
    for ay in range(8):
        for ax in range(8):
            # attribute cell covers a 4x4-tile (32x32px) block -> 2x2 grid
            # of 2x2-tile quadrants; sample the top-left tile of each.
            tl = zone_of(min(29, ay * 4), min(31, ax * 4))
            tr = zone_of(min(29, ay * 4), min(31, ax * 4 + 2))
            bl = zone_of(min(29, ay * 4 + 2), min(31, ax * 4))
            br = zone_of(min(29, ay * 4 + 2), min(31, ax * 4 + 2))
            nam.append(tl | (tr << 2) | (bl << 4) | (br << 6))
    return bytes(nam)


def build_stage_scene(stage_idx, atlas):
    """Returns a 1KB nametable half (32 cols) using shared atlas indices."""
    grid = [[0] * 32 for _ in range(30)]
    zone_rows = [0] * 6 + [1] * 4 + [2] * 5    # per 2-tile-row band

    stars = paint_stars(frames=1, h=96, seed=STAR_SEED)[0]
    for ty in range(12):
        for tx in range(32):
            grid[ty][tx] = atlas.add(cut_tiles(stars, tx * 8, ty * 8))

    neb = paint_nebula(h=64, seed=NEBULA_SEED)
    for ty in range(8):
        for tx in range(32):
            grid[12 + ty][tx] = atlas.add(cut_tiles(neb, tx * 8, ty * 8))

    ter = TERRAIN_PAINTERS[stage_idx](seed=0x21 + stage_idx * 0x11)
    crop = TERRAIN_CROP_COLS[stage_idx]
    for ty in range(10):
        for tx in range(32):
            src_tx = tx % crop              # tile the narrow crop across the width
            grid[20 + ty][tx] = atlas.add(cut_tiles(ter, src_tx * 8, ty * 8))

    def zone_of(r, c):
        return zone_rows[min(14, r // 2)]
    return nam_from_grid(grid, zone_of)


def build_title_scene(atlas):
    """Title never scrolls, so it only needs nametable A (1KB). The kana
    logo lives on the SAME shared BG atlas as everything else (there's no
    way around that with fixed CHR-ROM - every scene's tiles must coexist
    in one 256-tile table since it can never be rewritten at runtime)."""
    grid = [[0] * 32 for _ in range(30)]
    zone = [[0] * 32 for _ in range(30)]
    rng = random.Random(7)

    stars = paint_stars(frames=1, h=96, seed=STAR_SEED)[0]
    for _ in range(50):
        tx, ty = rng.randrange(32), rng.randrange(30)
        if grid[ty][tx] == 0:
            t = cut_tiles(stars, tx * 8, (ty * 8) % 96)
            if tkey(t) != tkey(BLANK):
                grid[ty][tx] = atlas.add(t)

    planet = paint_planet()
    for ty in range(8):
        for tx in range(9):
            t = cut_tiles(planet, tx * 8, ty * 8)
            if tkey(t) != tkey(BLANK):
                gr, gc = 2 + ty, 21 + tx
                grid[gr][gc] = atlas.add(t)
                zone[gr][gc] = 2

    line_rows = [10, 13, 16]
    for li, text_line in enumerate(TITLE_LINES):
        row = line_rows[li]
        col = (32 - len(text_line) * 2) // 2
        for gi, ch in enumerate(text_line):
            bm = glyph_bitmap(ch)
            big = [[0] * 16 for _ in range(16)]
            for y in range(16):
                for x in range(16):
                    if bm[y][x]:
                        big[y][x] = 3 if y < 9 else 2
                    elif y > 0 and x > 0 and bm[y - 1][x - 1]:
                        big[y][x] = 1
            for (oy, ox) in [(0, 0), (0, 8), (8, 0), (8, 8)]:
                t = cut_tiles(big, ox, oy)
                gr, gc = row + oy // 8, col + gi * 2 + ox // 8
                grid[gr][gc] = atlas.add(t)
                zone[gr][gc] = 1

    foot = '2026 CLAUDE FABLE'
    for i, ch in enumerate(foot):
        if ch != ' ':
            gc = (32 - len(foot)) // 2 + i
            grid[27][gc] = atlas.add(latin_tile(ch, color=2))
            zone[27][gc] = 3

    def zone_of(r, c):
        return zone[r][c]
    return nam_from_grid(grid, zone_of)


def main():
    atlas = FlatTileSet('nrom_bg', cap=256)
    title_nam = build_title_scene(atlas)
    stage_nams = [build_stage_scene(i, atlas) for i in range(5)]
    print(f'shared BG atlas: {len(atlas.tiles)} / 256 tiles')

    # Sprites are the OTHER physical 4KB half of CHR-ROM, so they don't
    # compete with the BG atlas above - but OAM only holds 64 sprites at
    # once in hardware, so unlike BG tiles, sprite CONTENT is fine to be
    # large (up to 256 unique tiles) as long as no single frame ever tries
    # to DRAW more than 64 of them - the title logo lives on the BG instead
    # of sprites for exactly this reason (22 glyphs x 4 tiles = 88 sprites
    # would blow the 64-sprite hardware limit if drawn all at once).
    sprite_tiles, metasprites = art.build()
    print(f'sprite atlas: {len(sprite_tiles)} / 256 tiles (max index '
          f'0x{max(sprite_tiles):02X})')

    # ---- bake BOTH pattern tables into ONE real 8KB CHR-ROM blob
    chr_rom = bytearray(0x2000)
    chr_rom[0x0000:0x1000] = atlas.chr_bytes()
    spr_bytes = bytearray(256 * 16)
    for idx, t in sprite_tiles.items():
        spr_bytes[idx * 16:idx * 16 + 16] = tile_to_chr(t)
    chr_rom[0x1000:0x2000] = bytes(spr_bytes)
    with open(os.path.join(BUILD, 'nrom_chrrom.bin'), 'wb') as f:
        f.write(chr_rom)

    with open(os.path.join(BUILD, 'nrom_title.nam'), 'wb') as f:
        f.write(title_nam)
    for i, nam in enumerate(stage_nams):
        with open(os.path.join(BUILD, f'nrom_stage{i+1}.nam'), 'wb') as f:
            f.write(nam)

    with open(os.path.join(BUILD, 'nrom_data.inc'), 'w') as f:
        f.write('; generated by gen_nrom.py - do not edit\n')
        f.write('nrom_title_pal:\n  .byte ' + ','.join(f'${v:02X}' for v in TITLE_PAL) + '\n')
        f.write('nrom_title_spr_pal:\n  .byte ' + ','.join(f'${v:02X}' for v in SPR_PAL) + '\n')
        f.write('nrom_stage_pals:\n')
        for p in STAGE_PALS:
            f.write('  .byte ' + ','.join(f'${v:02X}' for v in p) + '\n')
        f.write('nrom_stage_spr_pals:\n')
        for p in STAGE_SPR_PALS:
            f.write('  .byte ' + ','.join(f'${v:02X}' for v in p) + '\n')
        f.write('nrom_title_nam: .incbin "nrom_title.nam"\n')
        for i in range(5):
            f.write(f'nrom_stage{i+1}_nam: .incbin "nrom_stage{i+1}.nam"\n')
        f.write('nrom_stage_nam_l:\n  .byte '
                + ','.join(f'<nrom_stage{i+1}_nam' for i in range(5)) + '\n')
        f.write('nrom_stage_nam_h:\n  .byte '
                + ','.join(f'>nrom_stage{i+1}_nam' for i in range(5)) + '\n')
        # HUD sprite letter tiles (unchanged indices from the base sprite sheet)
        letters = {ch: 0x70 + i for i, ch in enumerate('GAMEOVRPUST12345')}
        letters.update({str(d): 0xA0 + d for d in range(10)})
        letters.update({ch: 0xAA + i for i, ch in enumerate('CHI')})
        def L(ch):
            return letters[ch]
        f.write('hud_score_lbl: .byte ' + ','.join(f'${L(c):02X}' for c in 'SCORE') + '\n')
        f.write('hud_hi_lbl:    .byte ' + ','.join(f'${L(c):02X}' for c in 'HI') + '\n')
        f.write('hud_rest_lbl:  .byte ' + ','.join(f'${L(c):02X}' for c in 'REST') + '\n')
        f.write('hud_stage_lbl: .byte ' + ','.join(f'${L(c):02X}' for c in 'S') + '\n')
        f.write(f'SPRITE_DIGIT_BASE = ${0xA0:02X}\n')

    # ---- previews
    def render_flat(nam, atlas, pal, cols, cropcols=None):
        img = [[(0, 0, 0)] * (cols * 8) for _ in range(240)]
        for half in range(cols // 32):
            base = half * (32 * 30 + 64)
            for r in range(30):
                for c in range(32):
                    idx = nam[base + r * 32 + c]
                    ab = nam[base + 32 * 30 + (r // 4) * 8 + c // 4]
                    sh = ((r % 4) // 2) * 4 + ((c % 4) // 2) * 2
                    p = (ab >> sh) & 3
                    t = atlas.tiles[idx]
                    for y in range(8):
                        for x in range(8):
                            v = t[y][x]
                            ci = pal[p * 4 + v] if v else pal[0]
                            img[r * 8 + y][(half * 32 + c) * 8 + x] = NESPAL[ci & 0x3F]
        return img

    write_png(os.path.join(BUILD, 'preview_nrom_title.png'), 256, 240,
              render_flat(title_nam, atlas, TITLE_PAL, 32))
    for i, nam in enumerate(stage_nams):
        write_png(os.path.join(BUILD, f'preview_nrom_stage{i+1}.png'), 512, 240,
                  render_flat(nam + nam, atlas, STAGE_PALS[i], 64))

    # sprite/logo sheet preview
    sheet = [[(20, 20, 30)] * (16 * 9) for _ in range(16 * 9)]
    for idx, t in sprite_tiles.items():
        bx, by = (idx % 16) * 9, (idx // 16) * 9
        for y in range(8):
            for x in range(8):
                v = t[y][x]
                if v:
                    rgb = NESPAL[SPR_PAL[v] & 0x3F] if v else (0, 0, 0)
                    sheet[by + y][bx + x] = rgb
    write_png(os.path.join(BUILD, 'preview_nrom_sprites.png'), 16 * 9, 16 * 9, sheet)
    print('OK: wrote NROM CHR-ROM build data + previews')


if __name__ == '__main__':
    main()
