# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Keitark. Maintainer-authored, Claude Code-assisted game.
# Published with maintainer authorization; see examples/fablenes/README.md.
"""Sprite artwork: player ship, enemies, boss, bullets, explosions.

Art is authored as ASCII grids ('.'=transparent, '1'..'3' = palette colors)
or generated procedurally. Exports SPRITE_TILES {tile_index: 8x8 tile} and
METASPRITES [(name, [(dy, tile, attr, dx), ...])].
"""
import math
import random
from fontdata import FONT5X7, latin_tile

PLAYER = [
    "................",
    ".......33.......",
    ".......233......",
    ".......2233.....",
    ".1....22223.....",
    ".11..2222233....",
    ".112222222233...",
    ".12222222222333.",
    ".12222222222333.",
    ".112222222233...",
    ".11..2222233....",
    ".1....22223.....",
    ".......2233.....",
    ".......233......",
    ".......33.......",
    "................",
]

FLAME0 = [
    "........",
    "......1.",
    "...1221.",
    "..12331.",
    "..12331.",
    "...1221.",
    "......1.",
    "........",
]
FLAME1 = [
    "........",
    "........",
    "....121.",
    "...1231.",
    "...1231.",
    "....121.",
    "........",
    "........",
]

PBULLET = [
    "........",
    "........",
    "..233333",
    ".2333333",
    ".2333333",
    "..233333",
    "........",
    "........",
]

OPTION0 = [
    "........",
    "..111...",
    ".12221..",
    ".12321..",
    ".12221..",
    "..111...",
    "........",
    "........",
]
OPTION1 = [
    "........",
    "..121...",
    ".12321..",
    ".23332..",
    ".12321..",
    "..121...",
    "........",
    "........",
]

EBULLET0 = [
    "........",
    "...22...",
    "..2332..",
    "..2332..",
    "...22...",
    "........",
    "........",
    "........",
]
EBULLET1 = [
    "........",
    "...2....",
    "..232...",
    ".23332..",
    "..232...",
    "...2....",
    "........",
    "........",
]

ENEMY_A0 = [
    "................",
    "....1......1....",
    "...11......11...",
    "...111....111...",
    "....11111111....",
    "...1122222211...",
    "..112233332211..",
    ".11223333332211.",
    ".11223333332211.",
    "..112233332211..",
    "...1122222211...",
    "....11111111....",
    "...111....111...",
    "...11......11...",
    "....1......1....",
    "................",
]
ENEMY_A1 = [
    "................",
    "................",
    "....1......1....",
    "...111....111...",
    "....11111111....",
    "...1122222211...",
    "..112233332211..",
    ".11223333332211.",
    ".11223333332211.",
    "..112233332211..",
    "...1122222211...",
    "....11111111....",
    "...111....111...",
    "....1......1....",
    "................",
    "................",
]

ENEMY_B0 = [
    "................",
    "................",
    "......3333......",
    ".....322223.....",
    "....32222223....",
    "...1111111111...",
    "..112222222211..",
    ".11222233222211.",
    ".11222233222211.",
    "..112222222211..",
    "...1111111111...",
    ".....1....1.....",
    "....1......1....",
    "................",
    "................",
    "................",
]
ENEMY_B1 = [
    "................",
    "................",
    "......3333......",
    ".....322223.....",
    "....32222223....",
    "...1111111111...",
    "..112222222211..",
    ".11223322332211.",
    ".11223322332211.",
    "..112222222211..",
    "...1111111111...",
    "....1......1....",
    ".....1....1.....",
    "................",
    "................",
    "................",
]

# stage 2+: fast dart missile (flies left)
DART0 = [
    "................",
    "................",
    "................",
    "................",
    "............1...",
    "......11111111..",
    "..13332222222211",
    ".133333222222221",
    ".133333222222221",
    "..13332222222211",
    "......11111111..",
    "............1...",
    "................",
    "................",
    "................",
    "................",
]
DART1 = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "......111111.1..",
    "..13332222222211",
    ".133333222222221",
    ".133333222222221",
    "..13332222222211",
    "......111111.1..",
    "................",
    "................",
    "................",
    "................",
    "................",
]

# stage 3+: bouncing jelly
BOUNCE0 = [
    "................",
    ".....222222.....",
    "....22233222....",
    "...2223332222...",
    "..222333322222..",
    "..222233222222..",
    "..222222222222..",
    "...2222222222...",
    "....22222222....",
    "....1.1..1.1....",
    "...1..1..1..1...",
    "...1..1..1..1...",
    "....1..1...1....",
    "....1..1...1....",
    "................",
    "................",
]
BOUNCE1 = [
    "................",
    ".....222222.....",
    "....22233222....",
    "...2223332222...",
    "..222333322222..",
    "..222233222222..",
    "..222222222222..",
    "...2222222222...",
    "....22222222....",
    "....1..1.1.1....",
    "....1.1..1..1...",
    "...1..1...1..1..",
    "...1...1..1..1..",
    "..1....1...1....",
    "................",
    "................",
]

# stage 4+: spinning guardian gear
SPIN0 = [
    ".......11.......",
    ".......11.......",
    ".......11.......",
    "...1...22...1...",
    "....1122221o....".replace('o', '1'),
    ".....122221.....",
    "...11223322211..",
    "1112223333222111",
    "1112223333222111",
    "...11223322211..",
    ".....122221.....",
    "....11222211....",
    "...1...22...1...",
    ".......11.......",
    ".......11.......",
    ".......11.......",
]
SPIN1 = [
    "1..............1",
    ".1............1.",
    "..1....22....1..",
    "...1..2222..1...",
    "....112222111...",
    ".....122221.....",
    "..1..223322..1..",
    "...122333322 1..".replace(' ', '2'),
    "..12223333222...",
    "..1..223322..1..",
    ".....122221.....",
    "....11222211....",
    "...1..2222..1...",
    "..1....22....1..",
    ".1............1.",
    "1..............1",
]

METEOR0 = [
    "..122...",
    ".12221..",
    "1222221.",
    "1232221.",
    ".122211.",
    "..1211..",
    "...1....",
    "........",
]
METEOR1 = [
    "...121..",
    "..12221.",
    ".1222221",
    ".1232221",
    "..12221.",
    "...121..",
    "........",
    "........",
]

ENEMY_C = [
    ".......11.......",
    ".......11.......",
    "..11...11...11..",
    "...11.1221.11...",
    "....11222211....",
    "....12222221....",
    ".....1233221....",
    "11111233332211 11".replace(" ", "")[:16],
    "1111123333221111",
    ".....1233221....",
    "....12222221....",
    "....11222211....",
    "...11.1221.11...",
    "..11...11...11..",
    ".......11.......",
    ".......11.......",
]


def grid_to_tiles16(grid):
    """16x16 ascii grid -> 4 tiles (TL, TR, BL, BR)."""
    g = [[0 if c == '.' else int(c) for c in row] for row in grid]
    tiles = []
    for ty in (0, 8):
        for tx in (0, 8):
            tiles.append([[g[ty + r][tx + c] for c in range(8)] for r in range(8)])
    # order TL,TR,BL,BR
    return [tiles[0], tiles[1], tiles[2], tiles[3]]


def grid_to_tile8(grid):
    return [[0 if c == '.' else int(c) for c in row] for row in grid]


def gen_explosion_frames():
    """4 frames of 16x16 explosion."""
    rng = random.Random(0xE5)
    frames = []
    params = [(3.0, 3), (5.5, 2), (7.2, 1), (7.8, 0)]  # radius, core color boost
    for f, (rad, boost) in enumerate(params):
        g = [[0] * 16 for _ in range(16)]
        for y in range(16):
            for x in range(16):
                dx, dy = x - 7.5, y - 7.5
                d = math.hypot(dx, dy) + rng.uniform(-1.2, 1.2)
                if d < rad:
                    t = d / rad
                    if t < 0.35:
                        c = 3
                    elif t < 0.7:
                        c = 2
                    else:
                        c = 1
                    if f == 3 and rng.random() < 0.6:
                        c = 0  # dissipating
                    g[y][x] = c
        frames.append([''.join('.123'[v] for v in row) for row in g])
    return frames


def gen_boss():
    """32x48 boss: armored core station with central eye. Colors 1..3."""
    W, H = 32, 48
    g = [[0] * W for _ in range(H)]
    cx, cy = 18, 23.5
    for y in range(H):
        for x in range(W):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy * 0.72)
            if d < 15.5:
                g[y][x] = 1                      # hull
            if d < 13.0:
                g[y][x] = 2 if ((x + y) // 3) % 2 == 0 else 1  # plating stripes
            if d < 6.5:
                g[y][x] = 1                      # eye socket
            if d < 4.5:
                g[y][x] = 3                      # eye core
            if d < 1.8:
                g[y][x] = 1                      # pupil
    # front cannons (left side, facing player)
    for y in (8, 9, 38, 39):
        for x in range(0, 9):
            g[y][x] = 2
        g[y][0] = 3
    for y in (22, 23, 24, 25):
        for x in range(0, 6):
            g[y][x] = 1
    # rear armor fins
    for y in range(H):
        if 4 <= y <= 43 and (y % 8) < 5:
            for x in range(29, 32):
                g[y][x] = 1
            g[y][31] = 2
    return [''.join('.123'[v] for v in row) for row in g]


def gen_boss2():
    """32x48 boss B: angular twin-eyed war fortress."""
    W, H = 32, 48
    g = [[0] * W for _ in range(H)]
    cx, cy = 18, 23.5
    for y in range(H):
        for x in range(W):
            dx, dy = abs(x - cx), abs(y - cy)
            d = dx * 0.9 + dy * 0.62          # diamond metric
            if d < 16.5:
                g[y][x] = 1
            if d < 14.0:
                g[y][x] = 2 if (y // 3) % 2 == 0 else 1   # horizontal armor bands
    # twin eyes
    for (ey) in (14, 33):
        for y in range(ey - 3, ey + 4):
            for x in range(12, 22):
                dd = abs(x - 16.5) * 0.8 + abs(y - ey)
                if dd < 4.2:
                    g[y][x] = 3
                if dd < 1.4:
                    g[y][x] = 1
    # nose cannon
    for y in (22, 23, 24, 25):
        for x in range(0, 8):
            g[y][x] = 2
        g[y][0] = 3
    # rear spines
    for y in range(2, 46, 6):
        for x in range(28, 32):
            g[y][x] = 1
            g[y + 1][x] = 2
    return [''.join('.123'[v] for v in row) for row in g]


def big_grid_to_tiles(grid, w_tiles, h_tiles):
    g = [[0 if c == '.' else int(c) for c in row] for row in grid]
    tiles = []
    for ty in range(h_tiles):
        for tx in range(w_tiles):
            tiles.append([[g[ty * 8 + r][tx * 8 + c] for c in range(8)] for r in range(8)])
    return tiles


def build():
    sprite_tiles = {}
    metasprites = []

    def put16(base, grid):
        for i, t in enumerate(grid_to_tiles16(grid)):
            sprite_tiles[base + i] = t

    def ms16(base, attr, with_flame=None):
        if with_flame is not None:
            # origin = flame left edge; ship body at +7 (all dx >= 0 so the
            # asm can clip on carry). Draw at player_x - 7.
            return [(4, with_flame, 0x03, 0),
                    (0, base + 0, attr, 7), (0, base + 1, attr, 15),
                    (8, base + 2, attr, 7), (8, base + 3, attr, 15)]
        return [(0, base + 0, attr, 0), (0, base + 1, attr, 8),
                (8, base + 2, attr, 0), (8, base + 3, attr, 8)]

    # player ship: tiles $00-$03, flames $04/$05
    put16(0x00, PLAYER)
    sprite_tiles[0x04] = grid_to_tile8(FLAME0)
    sprite_tiles[0x05] = grid_to_tile8(FLAME1)
    sprite_tiles[0x06] = grid_to_tile8(PBULLET)
    sprite_tiles[0x08] = grid_to_tile8(EBULLET0)
    sprite_tiles[0x09] = grid_to_tile8(EBULLET1)
    sprite_tiles[0x0A] = grid_to_tile8(OPTION0)
    sprite_tiles[0x0B] = grid_to_tile8(OPTION1)
    metasprites.append(('ms_player0', ms16(0x00, 0x00, with_flame=0x04)))
    metasprites.append(('ms_player1', ms16(0x00, 0x00, with_flame=0x05)))
    metasprites.append(('ms_pbullet', [(0, 0x06, 0x01, 0)]))
    metasprites.append(('ms_ebullet0', [(0, 0x08, 0x01, 0)]))
    metasprites.append(('ms_ebullet1', [(0, 0x09, 0x01, 0)]))
    metasprites.append(('ms_option0', [(0, 0x0A, 0x03, 0)]))
    metasprites.append(('ms_option1', [(0, 0x0B, 0x03, 0)]))

    put16(0x10, ENEMY_A0)
    put16(0x14, ENEMY_A1)
    put16(0x18, ENEMY_B0)
    put16(0x1C, ENEMY_B1)
    put16(0x20, ENEMY_C)
    metasprites.append(('ms_enemyA0', ms16(0x10, 0x01)))
    metasprites.append(('ms_enemyA1', ms16(0x14, 0x01)))
    metasprites.append(('ms_enemyB0', ms16(0x18, 0x02)))
    metasprites.append(('ms_enemyB1', ms16(0x1C, 0x02)))
    metasprites.append(('ms_enemyC0', ms16(0x20, 0x02)))
    metasprites.append(('ms_enemyC1', ms16(0x20, 0x02)))  # static, same frame

    # stage 2-5 enemies
    put16(0x58, DART0)
    put16(0x5C, DART1)
    put16(0x60, BOUNCE0)
    put16(0x64, BOUNCE1)
    put16(0x68, SPIN0)
    put16(0x6C, SPIN1)
    metasprites.append(('ms_dart0', ms16(0x58, 0x01)))
    metasprites.append(('ms_dart1', ms16(0x5C, 0x01)))
    metasprites.append(('ms_bounce0', ms16(0x60, 0x02)))
    metasprites.append(('ms_bounce1', ms16(0x64, 0x02)))
    metasprites.append(('ms_spin0', ms16(0x68, 0x02)))
    metasprites.append(('ms_spin1', ms16(0x6C, 0x02)))
    sprite_tiles[0x98] = grid_to_tile8(METEOR0)
    sprite_tiles[0x99] = grid_to_tile8(METEOR1)
    metasprites.append(('ms_meteor0', [(0, 0x98, 0x03, 0)]))
    metasprites.append(('ms_meteor1', [(0, 0x99, 0x03, 0)]))

    for f, frame in enumerate(gen_explosion_frames()):
        put16(0x28 + f * 4, frame)
        metasprites.append((f'ms_expl{f}', ms16(0x28 + f * 4, 0x03)))

    # bosses: 4x6 tiles at $40 (A) and $80 (B)
    for base, gen in [(0x40, gen_boss), (0x80, gen_boss2)]:
        boss_tiles = big_grid_to_tiles(gen(), 4, 6)
        ent = []
        for ty in range(6):
            for tx in range(4):
                sprite_tiles[base + ty * 4 + tx] = boss_tiles[ty * 4 + tx]
                ent.append((ty * 8, base + ty * 4 + tx, 0x02, tx * 8))
        metasprites.append(('ms_boss' if base == 0x40 else 'ms_boss2', ent))

    # GAME OVER / PAUSE / STAGE letter tiles + digits 1-5
    for i, ch in enumerate('GAMEOVRPUST12345'):
        sprite_tiles[0x70 + i] = latin_tile(ch, color=2)

    # extra tiles for a sprite-rendered HUD (NROM edition): a full contiguous
    # 0-9 digit run (needed so "DIGIT_BASE + value" arithmetic works, unlike
    # the scattered '1'-'5' at $7B-$7F above) plus C,H,I letters.
    for i, ch in enumerate('0123456789'):
        sprite_tiles[0xA0 + i] = latin_tile(ch, color=2)
    for i, ch in enumerate('CHI'):
        sprite_tiles[0xAA + i] = latin_tile(ch, color=2)

    return sprite_tiles, metasprites
