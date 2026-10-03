# SPDX-License-Identifier: MIT
# Copyright 2026 Keitark. Maintainer-authored, Claude Code-assisted game.
# Published with maintainer authorization; see examples/fablenes/README.md.
"""Generate all NES data: build/chr.bin, stage.nam, title.nam, pal.inc,
gfx.inc, metasprites.inc, music.inc + PNG previews.

Run: python gfx/gen_all.py
"""
import os
import sys
import math
import random
import struct
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art
import music
from fontdata import latin_tile, glyph_bitmap, TITLE_LINES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
os.makedirs(BUILD, exist_ok=True)

# ---------------------------------------------------------------- palettes
STAGE_BG_PAL = [0x0F, 0x00, 0x10, 0x30,   # 0: HUD grays
                0x0F, 0x11, 0x21, 0x30,   # 1: stars (dim blue, lt blue, white)
                0x0F, 0x03, 0x13, 0x23,   # 2: nebula violets
                0x0F, 0x0C, 0x1C, 0x2C]   # 3: terrain teals

# per-stage BG palettes (HUD + stars fixed; nebula/terrain themed)
STAGE_BG_PALS = [
    STAGE_BG_PAL,                                                    # 1 city
    STAGE_BG_PAL[:8] + [0x0F, 0x06, 0x16, 0x26, 0x0F, 0x07, 0x16, 0x28],  # 2 lava
    STAGE_BG_PAL[:8] + [0x0F, 0x09, 0x19, 0x29, 0x0F, 0x0B, 0x1B, 0x2B],  # 3 organic
    STAGE_BG_PAL[:8] + [0x0F, 0x01, 0x11, 0x21, 0x0F, 0x0C, 0x21, 0x30],  # 4 ice
    STAGE_BG_PAL[:8] + [0x0F, 0x04, 0x14, 0x24, 0x0F, 0x00, 0x10, 0x16],  # 5 fortress
]
TITLE_BG_PAL = [0x0F, 0x11, 0x21, 0x30,   # 0: sky/stars + white text
                0x0F, 0x11, 0x21, 0x30,   # 1: unused
                0x0F, 0x01, 0x2C, 0x30,   # 2: logo (navy shadow, cyan, white)
                0x0F, 0x07, 0x17, 0x27]   # 3: planet ambers
SPR_PAL = [0x0F, 0x16, 0x30, 0x12,        # 0: player (red, white, blue)
           0x0F, 0x17, 0x28, 0x30,        # 1: enemy A / bullets (orange, yellow)
           0x0F, 0x14, 0x24, 0x30,        # 2: enemy B / boss (purples)
           0x0F, 0x16, 0x28, 0x30]        # 3: explosions / flame (fire)

# per-stage sprite palettes: only pal 2 (boss & heavy enemies) is themed
def _spr_pal(p2):
    return SPR_PAL[:8] + [0x0F] + p2 + SPR_PAL[12:]

STAGE_SPR_PALS = [
    SPR_PAL,
    _spr_pal([0x16, 0x26, 0x30]),   # 2 red
    _spr_pal([0x1A, 0x2A, 0x30]),   # 3 green
    _spr_pal([0x11, 0x21, 0x30]),   # 4 ice blue
    _spr_pal([0x15, 0x25, 0x30]),   # 5 crimson
]

# NES master palette (RGB) for previews
NESPAL = [
    (84,84,84),(0,30,116),(8,16,144),(48,0,136),(68,0,100),(92,0,48),(84,4,0),(60,24,0),
    (32,42,0),(8,58,0),(0,64,0),(0,60,0),(0,50,60),(0,0,0),(0,0,0),(0,0,0),
    (152,150,152),(8,76,196),(48,50,236),(92,30,228),(136,20,176),(160,20,100),(152,34,32),(120,60,0),
    (84,90,0),(40,114,0),(8,124,0),(0,118,40),(0,102,120),(0,0,0),(0,0,0),(0,0,0),
    (236,238,236),(76,154,236),(120,124,236),(176,98,236),(228,84,236),(236,88,180),(236,106,100),(212,136,32),
    (160,170,0),(116,196,0),(76,208,32),(56,204,108),(56,180,204),(60,60,60),(0,0,0),(0,0,0),
    (236,238,236),(168,204,236),(188,188,236),(212,178,236),(236,174,236),(236,174,212),(236,180,176),(228,196,144),
    (204,210,120),(180,222,120),(168,226,144),(152,226,180),(160,214,228),(160,162,160),(0,0,0),(0,0,0),
]

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# ---------------------------------------------------------------- tile utils

def tile_to_chr(t):
    lo, hi = bytearray(8), bytearray(8)
    for r in range(8):
        b0 = b1 = 0
        for c in range(8):
            v = t[r][c]
            b0 = (b0 << 1) | (v & 1)
            b1 = (b1 << 1) | ((v >> 1) & 1)
        lo[r], hi[r] = b0, b1
    return bytes(lo) + bytes(hi)


def tkey(t):
    return tuple(tuple(row) for row in t)


BLANK = [[0] * 8 for _ in range(8)]


class TileSet:
    """Dedup tile container. For animated sets, each entry is a tuple of
    `frames` tiles (same index across frame banks)."""
    def __init__(self, name, cap=128, frames=1):
        self.name, self.cap, self.frames = name, cap, frames
        self.tiles = []
        self.index = {}
        self.add([BLANK] * frames if frames > 1 else BLANK)  # index 0 = blank

    def add(self, t):
        if self.frames > 1:
            key = tuple(tkey(f) for f in t)
        else:
            key = tkey(t)
        if key in self.index:
            return self.index[key]
        idx = len(self.tiles)
        assert idx < self.cap, f'{self.name}: tile budget exceeded ({self.cap})'
        self.tiles.append(t)
        self.index[key] = idx
        return idx

    def bank(self, frame=0):
        out = bytearray()
        for t in self.tiles:
            out += tile_to_chr(t[frame] if self.frames > 1 else t)
        out += b'\0' * (self.cap * 16 - len(out))
        return bytes(out)


def cut_tiles(img, x0, y0):
    return [[img[y0 + r][x0 + c] for c in range(8)] for r in range(8)]

# ---------------------------------------------------------------- stage bands
STAGE_W = 512


def paint_stars(frames=4, h=64, seed=0x51):
    """One star max per 8x8 cell, at canonical sub-positions, so the unique
    (4-frame) tile count stays small while density stays high."""
    rng = random.Random(seed)
    canv = [[[0] * STAGE_W for _ in range(h)] for _ in range(frames)]
    twinkle = {1: [1, 1, 2, 1], 2: [2, 1, 2, 3], 3: [3, 2, 3, 3]}
    subpos = [(2, 3), (5, 1), (3, 5)]
    cells = [(cx, cy) for cx in range(STAGE_W // 8) for cy in range(h // 8)]
    rng.shuffle(cells)
    for (cx, cy) in cells[:120]:
        b = rng.choice([1, 1, 1, 2, 2, 3])
        sy, sx = (3, 3) if b == 3 else rng.choice(subpos)
        x, y = cx * 8 + sx, cy * 8 + sy
        ph = rng.randrange(4)
        for f in range(frames):
            c = twinkle[b][(f + ph) % 4]
            canv[f][y][x] = c
            if b == 3:  # bright star: diffraction cross (kept inside the cell)
                for d in (1, 2) if c == 3 else (1,):
                    canv[f][y][x + d] = max(canv[f][y][x + d], c - 1)
                    canv[f][y][x - d] = max(canv[f][y][x - d], c - 1)
                    canv[f][y - d][x] = max(canv[f][y - d][x], c - 1)
                    canv[f][y + d][x] = max(canv[f][y + d][x], c - 1)
    return canv


def paint_nebula(h=64, seed=0x42):
    rng = random.Random(seed)
    tw, th = STAGE_W // 8, h // 8
    lat = [[rng.uniform(0, 6.5) for _ in range(tw)] for _ in range(th + 1)]
    for _ in range(2):  # smooth, wrapping horizontally
        lat = [[(lat[j][i] * 2 + lat[j][(i - 1) % tw] + lat[j][(i + 1) % tw]
                 + lat[max(0, j - 1)][i] + lat[min(th, j + 1)][i]) / 6
                for i in range(tw)] for j in range(th + 1)]
    env = [math.sin(math.pi * j / th) ** 0.7 for j in range(th + 1)]
    corners = [[round(min(4, lat[j][i] * env[j] * 1.1)) for i in range(tw)]
               for j in range(th + 1)]
    img = [[0] * STAGE_W for _ in range(h)]
    for ty in range(th):
        for tx in range(tw):
            c00 = corners[ty][tx]
            c10 = corners[ty][(tx + 1) % tw]
            c01 = corners[ty + 1][tx]
            c11 = corners[ty + 1][(tx + 1) % tw]
            for r in range(8):
                for c in range(8):
                    fx, fy = c / 8.0, r / 8.0
                    v = (c00 * (1 - fx) * (1 - fy) + c10 * fx * (1 - fy)
                         + c01 * (1 - fx) * fy + c11 * fx * fy)
                    lvl = v / 4.0 * 3.6 - BAYER4[r % 4][c % 4] / 16.0 * 1.4
                    img[ty * 8 + r][tx * 8 + c] = max(0, min(3, int(lvl + 0.5)))
    return img


def paint_terrain(h=80, seed=0x77):
    rng = random.Random(seed)
    img = [[0] * STAGE_W for _ in range(h)]
    deck_y = h - 16
    # deck
    for x in range(STAGE_W):
        img[deck_y][x] = 2
        img[deck_y + 1][x] = 2 if x % 4 < 2 else 1
        for y in range(deck_y + 2, h):
            img[y][x] = 1
        if x % 16 == 0:
            for y in range(deck_y + 2, h):
                img[y][x] = 2
        if (x % 4 == 1) and ((x // 4) % 3 == 0):
            img[h - 2][x] = 0
    # towers
    x = 0
    while x < STAGE_W:
        w = rng.choice([16, 24, 32, 40, 48])
        if x + w > STAGE_W:
            w = STAGE_W - x
        if rng.random() < 0.25 or w < 16:
            x += w  # gap
            continue
        th_ = rng.choice([16, 24, 32, 40, 48, 56])
        top = deck_y - th_
        for cx in range(x, x + w):
            img[top][cx] = 2
            img[top + 1][cx] = 2
            for y in range(top + 2, deck_y):
                img[y][cx] = 1
        # lit window grid (8px aligned)
        for wy in range(top + 8, deck_y - 4, 8):
            for wx in range(x + 8, x + w - 4, 8):
                if rng.random() < 0.6:
                    col = 3 if rng.random() < 0.7 else 2
                    for dy in (3, 4):
                        for dx in (2, 3):
                            img[wy + dy][wx + dx] = col
        # antenna on tall towers
        if th_ >= 40 and w >= 24:
            ax = x + w // 2
            for y in range(top - 12, top):
                if 0 <= y:
                    img[y][ax] = 1
            if top - 12 >= 0:
                img[top - 12][ax] = 3
        x += w
    return img

def paint_terrain_lava(h=80, seed=0x21):
    """Stage 2: jagged volcanic spires over glowing lava pools."""
    rng = random.Random(seed)
    img = [[0] * STAGE_W for _ in range(h)]
    deck_y = h - 16
    for x in range(STAGE_W):
        for y in range(deck_y, h):
            img[y][x] = 1
    # lava pools on the deck
    x = 0
    while x < STAGE_W:
        x += rng.choice([40, 48, 56])
        w = rng.choice([24, 32])
        if x + w > STAGE_W:
            break
        for px in range(x, x + w):
            img[deck_y + 2][px] = 2
            for y in range(deck_y + 3, deck_y + 10):
                img[y][px] = 3 if (px + y) % 3 else 2
        x += w
    # spires (8px columns, random-walk heights)
    hgt = 24
    for cx in range(0, STAGE_W, 8):
        hgt = max(8, min(56, hgt + rng.choice([-16, -8, 0, 8, 16])))
        top = deck_y - hgt
        for px in range(cx, cx + 8):
            img[top][px] = 2
            img[top + 1][px] = 2
            for y in range(top + 2, deck_y):
                img[y][px] = 1
        if hgt >= 32 and rng.random() < 0.5:   # glowing crack
            for y in range(top + 6, deck_y - 2, 3):
                img[y][cx + 3] = 2
    return img


def paint_terrain_organic(h=80, seed=0x33):
    """Stage 3: alien fungus domes and stalks."""
    rng = random.Random(seed)
    img = [[0] * STAGE_W for _ in range(h)]
    deck_y = h - 12
    for x in range(STAGE_W):
        img[deck_y][x] = 2
        for y in range(deck_y + 1, h):
            img[y][x] = 1
    for cx in range(16, STAGE_W - 32, 48):
        r = rng.choice([12, 24])
        cy = deck_y - r - 8
        # stalk
        for y in range(cy, deck_y):
            for px in range(cx - 3, cx + 4):
                img[y][px] = 1
        # cap (semicircle)
        for y in range(cy - r, cy + 3):
            for px in range(cx - r, cx + r + 1):
                if 0 <= px < STAGE_W:
                    d = ((px - cx) ** 2 + (y - cy) ** 2) ** 0.5
                    if d <= r:
                        img[y][px] = 1
                        if d >= r - 3 and y < cy - r // 3:
                            img[y][px] = 2       # rim light
                        elif (px % 8 in (2, 3)) and (y % 8 in (4, 5)) and d < r - 4:
                            img[y][px] = 3       # spores
    return img


def paint_terrain_ice(h=80, seed=0x44):
    """Stage 4: crystal spikes and snow deck."""
    rng = random.Random(seed)
    img = [[0] * STAGE_W for _ in range(h)]
    deck_y = h - 12
    for x in range(STAGE_W):
        img[deck_y][x] = 2
        img[deck_y + 1][x] = 2
        for y in range(deck_y + 2, h):
            img[y][x] = 1
    x = 0
    while x < STAGE_W - 64:
        x += rng.choice([16, 24, 32])
        hgt = rng.choice([24, 32, 40, 48])
        # triangle spike, 2px per row each side
        for i in range(hgt):
            y = deck_y - hgt + i
            half = i // 2 + 1
            for px in range(x - half, x + half):
                if 0 <= px < STAGE_W:
                    img[y][px] = 1
            img[y][max(0, x - half)] = 2         # lit left edge
        if rng.random() < 0.6:
            img[deck_y - hgt + 2][x] = 3         # sparkle
        x += hgt // 2 + 8
    return img


def paint_terrain_fortress(h=80, seed=0x55):
    """Stage 5: enemy fortress wall with turrets and warning lights."""
    rng = random.Random(seed)
    img = [[0] * STAGE_W for _ in range(h)]
    deck_y = h - 8
    hgt = 32
    for cx in range(0, STAGE_W, 16):
        hgt = max(16, min(64, hgt + rng.choice([-16, -8, 0, 0, 8, 16])))
        top = deck_y - hgt
        for px in range(cx, cx + 16):
            crenel = 8 if ((px // 8) % 2 == 0) else 0
            t = top - (8 if crenel and hgt >= 24 else 0)
            for y in range(max(0, t), h):
                img[y][px] = 1
            img[max(0, t)][px] = 2
        # pipe lines
        for y in range(top + 8, deck_y, 16):
            for px in range(cx, cx + 16):
                img[y][px] = 2
        # warning light
        if hgt >= 32:
            img[top + 12][cx + 4] = 3
            img[top + 12][cx + 5] = 3
    for x in range(STAGE_W):
        for y in range(deck_y, h):
            img[y][x] = 1
        img[deck_y][x] = 2
    return img

# ---------------------------------------------------------------- stage NTs
HUD_SCORE_COL, HUD_HI_COL, HUD_REST_COL = 8, 20, 7


def build_stage(anim_ts, static_ts):
    grid = [[0] * 64 for _ in range(30)]

    def text(row, col, s):
        for i, ch in enumerate(s):
            if ch != ' ':
                grid[row][col + i] = 0x80 + static_ts.add(latin_tile(ch))

    text(1, 2, 'SCORE')
    text(1, HUD_SCORE_COL, '0000000')
    text(1, 17, 'HI')
    text(1, HUD_HI_COL, '0000000')
    text(1, 28, 'S1')
    text(2, 2, 'REST')
    text(2, HUD_REST_COL, '3')
    line = [[0] * 8 for _ in range(8)]
    for c in range(8):
        line[4][c] = 2
        line[5][c] = 1
    lt = 0x80 + static_ts.add(line)
    for c in range(64):
        grid[3][c] = lt

    stars = paint_stars()
    for ty in range(8):
        for tx in range(64):
            frames = [cut_tiles(stars[f], tx * 8, ty * 8) for f in range(4)]
            grid[4 + ty][tx] = anim_ts.add(frames)

    neb = paint_nebula()
    for ty in range(8):
        for tx in range(64):
            t = cut_tiles(neb, tx * 8, ty * 8)
            grid[12 + ty][tx] = anim_ts.add([t, t, t, t])

    n_base = len(static_ts.tiles)   # tiles shared by every stage bank (font/HUD)

    ter = paint_terrain()
    for ty in range(10):
        for tx in range(64):
            grid[20 + ty][tx] = 0x80 + static_ts.add(cut_tiles(ter, tx * 8, ty * 8))

    # attributes: bands by row
    zone_rows = [0] * 2 + [1] * 4 + [2] * 4 + [3] * 5   # 15 cell-rows
    out = bytearray()
    for half in range(2):
        for r in range(30):
            out += bytes(grid[r][half * 32:half * 32 + 32])
        for ay in range(8):
            for ax in range(8):
                tl = zone_rows[min(14, ay * 2)]
                bl = zone_rows[min(14, ay * 2 + 1)]
                out.append(tl | (tl << 2) | (bl << 4) | (bl << 6))
    return bytes(out), grid, n_base

# ---------------------------------------------------------------- title
STAR_TILES = []
for pat in [[(3, 3, 2)], [(4, 2, 3)], [(3, 3, 3), (2, 3, 2), (4, 3, 2), (3, 2, 2), (3, 4, 2)]]:
    t = [[0] * 8 for _ in range(8)]
    for (r, c, v) in pat:
        t[r][c] = v
    STAR_TILES.append(t)


def paint_planet(w=72, h=64):
    img = [[0] * w for _ in range(h)]
    cx, cy, rad = 36.0, 30.0, 24.0
    for y in range(h):
        for x in range(w):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d < rad:
                lum = 0.5 - (dx * 0.55 + dy * 0.65) / rad * 0.5  # 0..1
                band = 0.18 * math.sin(y * 0.45 + x * 0.05)
                v = max(0.0, min(1.0, lum + band))
                lvl = v * 3.2 - BAYER4[y % 4][x % 4] / 16.0 * 1.1
                img[y][x] = max(1, min(3, int(lvl + 0.5)))
    # ring: in front below center, hidden behind planet above
    for y in range(h):
        for x in range(w):
            dx, dy = x - cx, (y - cy) * 3.4
            e = math.hypot(dx * 0.78, dy)
            if 24.5 < e < 31 and (y > cy or math.hypot(x - cx, y - cy) > rad):
                img[y][x] = 3 if 26 < e < 29 else 2
    return img


def build_title(tlow, thigh):
    grid = [[0] * 32 for _ in range(30)]
    zone = [[0] * 16 for _ in range(15)]

    rng = random.Random(7)
    for _ in range(46):
        r, c = rng.randrange(0, 29), rng.randrange(32)
        if grid[r][c] == 0:
            grid[r][c] = tlow.add(STAR_TILES[rng.choice([0, 0, 0, 1, 1, 2])])

    planet = paint_planet()
    for ty in range(8):
        for tx in range(9):
            t = cut_tiles(planet, tx * 8, ty * 8)
            if tkey(t) != tkey(BLANK):
                grid[2 + ty][21 + tx] = 0x80 + thigh.add(t)
                zone[(2 + ty) // 2][(21 + tx) // 2] = 3

    # logo lines: 16x16 kana, white top / cyan bottom / navy drop shadow
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
            for q, (oy, ox) in enumerate([(0, 0), (0, 8), (8, 0), (8, 8)]):
                t = cut_tiles(big, ox, oy)
                gr, gc = row + oy // 8, col + gi * 2 + ox // 8
                grid[gr][gc] = tlow.add(t)
            for cy in (row // 2, (row + 1) // 2):
                for cxx in range((col + gi * 2) // 2, (col + gi * 2 + 2) // 2 + 1):
                    if cxx < 16:
                        zone[cy][cxx] = 2

    push = 'PUSH START'
    push_tiles = []
    for i, ch in enumerate(push):
        ti = 0 if ch == ' ' else 0x80 + thigh.add(latin_tile(ch))
        push_tiles.append(ti)
        grid[21][11 + i] = ti

    foot = '2026 CLAUDE FABLE'
    for i, ch in enumerate(foot):
        if ch != ' ':
            grid[27][(32 - len(foot)) // 2 + i] = 0x80 + thigh.add(latin_tile(ch))

    out = bytearray()
    for r in range(30):
        out += bytes(grid[r])
    for ay in range(8):
        for ax in range(8):
            def z(cy, cx):
                return zone[min(14, cy)][min(15, cx)]
            out.append(z(ay * 2, ax * 2) | (z(ay * 2, ax * 2 + 1) << 2)
                       | (z(ay * 2 + 1, ax * 2) << 4) | (z(ay * 2 + 1, ax * 2 + 1) << 6))
    return bytes(out), grid, push_tiles

# ---------------------------------------------------------------- png writer

def write_png(path, w, h, pix):
    raw = b''.join(b'\0' + bytes(v for p in row for v in p) for row in pix)
    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


def render_nt(grid, w_tiles, get_tile, attr_lookup, bg_pal):
    img = [[(0, 0, 0)] * (w_tiles * 8) for _ in range(240)]
    for r in range(30):
        for c in range(w_tiles):
            t = get_tile(grid[r][c])
            pal = attr_lookup(r, c)
            for y in range(8):
                for x in range(8):
                    v = t[y][x]
                    ci = bg_pal[pal * 4 + v] if v else bg_pal[0]
                    img[r * 8 + y][c * 8 + x] = NESPAL[ci & 0x3F]
    return img

# ---------------------------------------------------------------- main

def main():
    anim_ts = TileSet('stage-anim', 128, frames=4)
    static_ts = TileSet('stage-static', 128)
    for d in '0123456789':  # digits pinned at $80+: $80 is blank... seed first
        pass
    # NOTE: index 0 of static set is blank; digits must start at fixed offset.
    digit_base = None
    for d in '0123456789':
        i = static_ts.add(latin_tile(d))
        if digit_base is None:
            digit_base = 0x80 + i
    stage_nam, stage_grid, n_base = build_stage(anim_ts, static_ts)

    # ---- per-stage terrain banks + nametable row blocks (rows 20-29)
    def rows_block(grid_rows):
        out = bytearray()
        for half in range(2):
            for r in grid_rows:
                out += bytes(r[half * 32:half * 32 + 32])
        return bytes(out)

    terr_blocks = [rows_block(stage_grid[20:30])]
    stage_banks = [static_ts]
    terr_imgs = [paint_terrain()]
    for name, painter in [('lava', paint_terrain_lava), ('organic', paint_terrain_organic),
                          ('ice', paint_terrain_ice), ('fortress', paint_terrain_fortress)]:
        ts = TileSet(f'terr-{name}', 128)
        ts.tiles = list(static_ts.tiles[:n_base])
        ts.index = {tkey(t): i for i, t in enumerate(ts.tiles)}
        img = painter()
        rows = [[0x80 + ts.add(cut_tiles(img, tx * 8, ty * 8)) for tx in range(64)]
                for ty in range(10)]
        terr_blocks.append(rows_block(rows))
        stage_banks.append(ts)
        terr_imgs.append(img)
        print(f'  terr-{name}: {len(ts.tiles)} tiles')

    # terrain preview strip (all 5 stages, own palettes)
    tp = [[(0, 0, 0)] * 512 for _ in range(5 * 84)]
    for s, img in enumerate(terr_imgs):
        pal = STAGE_BG_PALS[s][12:16]
        for y in range(80):
            for x in range(512):
                v = img[y][x]
                tp[s * 84 + y][x] = NESPAL[pal[v] & 0x3F] if v else (10, 10, 20)
    write_png(os.path.join(BUILD, 'preview_terrains.png'), 512, 5 * 84, tp)

    tlow = TileSet('title-low', 128)
    thigh = TileSet('title-high', 128)
    title_nam, title_grid, push_tiles = build_title(tlow, thigh)

    sprite_tiles, metasprites = art.build()

    print(f'tiles: stage-anim={len(anim_ts.tiles)} stage-static={len(static_ts.tiles)} '
          f'title-low={len(tlow.tiles)} title-high={len(thigh.tiles)} '
          f'sprites={len(sprite_tiles)}')

    # ---- chr.bin (32KB)
    chr_data = bytearray(0x8000)
    for f in range(4):
        chr_data[f * 0x800:f * 0x800 + 0x800] = anim_ts.bank(f)
    chr_data[0x2000:0x2800] = static_ts.bank()
    chr_data[0x2800:0x3000] = tlow.bank()
    chr_data[0x3000:0x3800] = thigh.bank()
    for idx, t in sprite_tiles.items():
        chr_data[0x4000 + idx * 16:0x4000 + idx * 16 + 16] = tile_to_chr(t)
    for i, ts in enumerate(stage_banks[1:]):        # stages 2-5 at 1KB units 20..27
        off = 0x5000 + i * 0x800
        chr_data[off:off + 0x800] = ts.bank()
    with open(os.path.join(BUILD, 'chr.bin'), 'wb') as f:
        f.write(chr_data)

    with open(os.path.join(BUILD, 'stage.nam'), 'wb') as f:
        f.write(stage_nam)
    with open(os.path.join(BUILD, 'title.nam'), 'wb') as f:
        f.write(title_nam)
    with open(os.path.join(BUILD, 'terrain.bin'), 'wb') as f:
        for blk in terr_blocks:
            f.write(blk)

    # ---- pal.inc / gfx.inc
    with open(os.path.join(BUILD, 'pal.inc'), 'w') as f:
        f.write('; generated\nstage_bg_pal:\n  .byte ' +
                ','.join(f'${v:02X}' for v in STAGE_BG_PAL) + '\n')
        f.write('title_bg_pal:\n  .byte ' + ','.join(f'${v:02X}' for v in TITLE_BG_PAL) + '\n')
        f.write('spr_pal:\n  .byte ' + ','.join(f'${v:02X}' for v in SPR_PAL) + '\n')
        f.write('stage_bg_pals:\n')
        for p in STAGE_BG_PALS:
            f.write('  .byte ' + ','.join(f'${v:02X}' for v in p) + '\n')
        f.write('stage_spr_pals:\n')
        for p in STAGE_SPR_PALS:
            f.write('  .byte ' + ','.join(f'${v:02X}' for v in p) + '\n')

    with open(os.path.join(BUILD, 'gfx.inc'), 'w') as f:
        f.write('; generated\n')
        f.write(f'DIGIT_BASE      = ${digit_base:02X}\n')
        f.write('HUD_SCORE_ADDR  = $2028\n')
        f.write('HUD_HI_ADDR     = $2034\n')
        f.write('HUD_REST_ADDR   = $2047\n')
        f.write('HUD_STAGE_ADDR  = $203D\n')
        f.write('stage_chr_hi:\n  .byte 8,20,22,24,26\n')
        f.write('PUSHSTART_ADDR  = $22AB\n')
        f.write('PUSHSTART_LEN   = 10\n')
        f.write('; CHR 1KB bank numbers\n')
        f.write('CHRBANK_GAME_HI = 8\nCHRBANK_TITLE_LO = 10\nCHRBANK_TITLE_HI = 12\n')
        f.write('CHRBANK_SPR     = 16\n')
        f.write('pushstart_tiles:\n  .byte ' + ','.join(f'${t:02X}' for t in push_tiles) + '\n')
        sine = [round(24 * math.sin(2 * math.pi * i / 32)) for i in range(32)]
        f.write('sine24:\n  .byte ' + ','.join(f'${v & 0xFF:02X}' for v in sine) + '\n')

    with open(os.path.join(BUILD, 'metasprites.inc'), 'w') as f:
        f.write('; generated: .byte count, then dy,tile,attr,dx per sprite\n')
        for name, ents in metasprites:
            f.write(f'{name}:\n  .byte {len(ents)}\n')
            for (dy, tile, attrb, dx) in ents:
                f.write(f'  .byte ${dy & 0xFF:02X},${tile:02X},${attrb:02X},${dx & 0xFF:02X}\n')

    music.write_music_inc(os.path.join(BUILD, 'music.inc'))

    # ---- previews
    def stage_attr(r, c):
        return [0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3][min(14, r // 2)]

    def stage_tile(i):
        if i < 0x80:
            e = anim_ts.tiles[i]
            return e[0]
        return static_ts.tiles[i - 0x80]

    write_png(os.path.join(BUILD, 'preview_stage.png'), 512, 240,
              render_nt(stage_grid, 64, stage_tile, stage_attr, STAGE_BG_PAL))

    title_attr_map = {}
    def title_tile(i):
        return tlow.tiles[i] if i < 0x80 else thigh.tiles[i - 0x80]
    # recompute zones from attr bytes in title_nam
    tattr = title_nam[960:1024]
    def title_attr(r, c):
        b = tattr[(r // 4) * 8 + c // 4]
        sh = ((r % 4) // 2) * 4 + ((c % 4) // 2) * 2
        return (b >> sh) & 3
    write_png(os.path.join(BUILD, 'preview_title.png'), 256, 240,
              render_nt(title_grid, 32, title_tile, title_attr, TITLE_BG_PAL))

    # sprite sheet preview
    def spr_palette(idx):
        if idx < 0x04: return 0
        if idx < 0x06: return 3
        if idx < 0x18: return 1
        if idx < 0x28: return 2
        if idx < 0x40: return 3
        if idx < 0x70: return 2
        return 0
    sheet = [[(20, 20, 30)] * (16 * 9) for _ in range(16 * 9)]
    for idx, t in sprite_tiles.items():
        bx, by = (idx % 16) * 9, (idx // 16) * 9
        p = spr_palette(idx)
        for y in range(8):
            for x in range(8):
                v = t[y][x]
                if v:
                    sheet[by + y][bx + x] = NESPAL[SPR_PAL[p * 4 + v] & 0x3F]
    write_png(os.path.join(BUILD, 'preview_sprites.png'), 16 * 9, 16 * 9, sheet)
    print('OK: wrote build/ data + previews')


if __name__ == '__main__':
    main()
