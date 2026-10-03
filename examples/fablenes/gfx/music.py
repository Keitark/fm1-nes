# SPDX-License-Identifier: MIT
# Copyright 2026 Keitark. Maintainer-authored, Claude Code-assisted game.
# Published with maintainer authorization; see examples/fablenes/README.md.
"""Generate build/music.inc: APU period tables and song stream data.

Stream format (square/triangle channels):
  note_byte dur_byte ...   note: 0..$5F = semitones above C2, $60 = rest
  $FF = loop to start of stream
Noise stream: note_byte is a drum id (0=kick 1=snare 2=hat), $60 = rest.
"""

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
REST = 0x60


def note(name):
    """'A4' -> semitone index above C2."""
    if name is None:
        return REST
    pitch = name[:-1]
    octv = int(name[-1])
    return (octv - 2) * 12 + NAMES.index(pitch)


def periods():
    out = []
    f0 = 65.40639  # C2
    for i in range(0x60):
        f = f0 * (2 ** (i / 12.0))
        p = round(1789773.0 / (16.0 * f)) - 1
        out.append(max(0, min(0x7FF, p)))
    return out


def stream(pairs):
    """pairs: list of (note_name_or_None_or_drumid, frames)."""
    b = []
    for n, d in pairs:
        if isinstance(n, int):
            b.append(n)
        else:
            b.append(note(n))
        b.append(d)
    b.append(0xFF)
    return b


E = 12      # eighth note (stage tempo)
S = 6       # sixteenth
Q = 24      # quarter
H = 48

# ---------------- stage tune: driving A-minor loop, 4 bars ----------------
stage_lead = stream([
    # bar 1 (Am)
    ('A4', E), ('C5', E), ('E5', E), ('C5', E), ('D5', E), ('E5', E), ('C5', Q),
    # bar 2 (Am)
    ('A4', E), ('E5', E), ('D5', E), ('C5', E), ('B4', E), ('C5', E), ('A4', Q),
    # bar 3 (F)
    ('F4', E), ('A4', E), ('C5', E), ('A4', E), ('F5', E), ('E5', E), ('D5', Q),
    # bar 4 (G)
    ('G4', E), ('B4', E), ('D5', E), ('B4', E), ('E5', E), ('D5', E), ('B4', Q),
])

stage_harm = stream([
    # 16th arps per bar
    *[p for _ in range(2) for p in [('A3', S), ('E4', S), ('A4', S), ('E4', S),
                                    ('C4', S), ('E4', S), ('A4', S), ('E4', S)]],
    *[p for _ in range(2) for p in [('A3', S), ('E4', S), ('A4', S), ('E4', S),
                                    ('C4', S), ('E4', S), ('A4', S), ('E4', S)]],
    *[p for _ in range(2) for p in [('F3', S), ('C4', S), ('F4', S), ('C4', S),
                                    ('A3', S), ('C4', S), ('F4', S), ('C4', S)]],
    *[p for _ in range(2) for p in [('G3', S), ('D4', S), ('G4', S), ('D4', S),
                                    ('B3', S), ('D4', S), ('G4', S), ('D4', S)]],
])

stage_bass = stream([
    # pumping octaves
    *[('A2', E), ('A2', E), ('A3', E), ('A2', E)] * 2,
    *[('A2', E), ('A2', E), ('A3', E), ('A2', E)] * 2,
    *[('F2', E), ('F2', E), ('F3', E), ('F2', E)] * 2,
    *[('G2', E), ('G2', E), ('G3', E), ('G2', E)] * 2,
])

KICK, SNARE, HAT = 0, 1, 2
stage_noise = stream([
    *[(KICK, E), (HAT, E), (SNARE, E), (HAT, E)] * 8,
])

# ---------------- title tune: slow dreamy arp, 4 bars (Am G F E) ----------
TQ = 32
TE = 16
title_lead = stream([
    ('A4', TQ), ('C5', TQ), ('E5', TQ), ('D5', TE), ('C5', TE),
    ('B4', TQ), ('D5', TQ), ('G5', TQ), ('D5', TQ),
    ('C5', TQ), ('A4', TQ), ('F5', TQ), ('E5', TQ),
    ('B4', TQ), ('G#4', TQ), ('E4', TQ * 2),
])
title_harm = stream([
    *[('A3', TE), ('C4', TE), ('E4', TE), ('C4', TE)] * 2,
    *[('G3', TE), ('B3', TE), ('D4', TE), ('B3', TE)] * 2,
    *[('F3', TE), ('A3', TE), ('C4', TE), ('A3', TE)] * 2,
    *[('E3', TE), ('G#3', TE), ('B3', TE), ('G#3', TE)] * 2,
])
title_bass = stream([
    ('A2', TQ * 4), ('G2', TQ * 4), ('F2', TQ * 4), ('E2', TQ * 4),
])
title_noise = stream([(None, 255)])  # silence

# ---------------- tense tune (stages 4-5): faster E-minor drive ----------
TS = 5   # sixteenth
TE2 = 10  # eighth
tense_lead = stream([
    # bar 1 (Em)
    ('E5', TE2), ('B4', TS), ('E5', TS), ('G5', TE2), ('F#5', TE2),
    ('E5', TE2), ('D5', TE2), ('B4', TE2 * 2),
    # bar 2 (Em)
    ('E5', TE2), ('G5', TS), ('A5', TS), ('B5', TE2), ('A5', TE2),
    ('G5', TE2), ('F#5', TE2), ('E5', TE2 * 2),
    # bar 3 (C)
    ('C5', TE2), ('E5', TS), ('G5', TS), ('E5', TE2), ('C5', TE2),
    ('D5', TE2), ('E5', TE2), ('C5', TE2 * 2),
    # bar 4 (B)
    ('B4', TE2), ('D#5', TS), ('F#5', TS), ('B5', TE2), ('A5', TE2),
    ('F#5', TE2), ('D#5', TE2), ('B4', TE2 * 2),
])
tense_harm = stream([
    *[('E3', TS), ('B3', TS), ('E4', TS), ('B3', TS)] * 4,
    *[('E3', TS), ('B3', TS), ('E4', TS), ('B3', TS)] * 4,
    *[('C3', TS), ('G3', TS), ('C4', TS), ('G3', TS)] * 4,
    *[('B2', TS), ('F#3', TS), ('B3', TS), ('F#3', TS)] * 4,
])
tense_bass = stream([
    *[('E2', TE2), ('E2', TS), ('E3', TS)] * 4,
    *[('E2', TE2), ('E2', TS), ('E3', TS)] * 4,
    *[('C2', TE2), ('C2', TS), ('C3', TS)] * 4,
    *[('B2', TE2), ('B2', TS), ('B3', TS)] * 4,
])
KICK2, SNARE2, HAT2 = 0, 1, 2
tense_noise = stream([
    *[(KICK2, TE2), (HAT2, TS), (HAT2, TS), (SNARE2, TE2), (HAT2, TE2)] * 8,
])


def emit_bytes(f, label, data):
    f.write(f'{label}:\n')
    for i in range(0, len(data), 16):
        f.write('  .byte ' + ','.join(f'${b:02X}' for b in data[i:i + 16]) + '\n')


def write_music_inc(path):
    per = periods()
    with open(path, 'w') as f:
        f.write('; generated by music.py - do not edit\n')
        f.write('note_period_lo:\n')
        for i in range(0, 0x60, 12):
            f.write('  .byte ' + ','.join(f'${p & 0xFF:02X}' for p in per[i:i + 12]) + '\n')
        f.write('note_period_hi:\n')
        for i in range(0, 0x60, 12):
            f.write('  .byte ' + ','.join(f'${(p >> 8) & 0x07:02X}' for p in per[i:i + 12]) + '\n')
        for lbl, data in [('song_stage_sq1', stage_lead), ('song_stage_sq2', stage_harm),
                          ('song_stage_tri', stage_bass), ('song_stage_noi', stage_noise),
                          ('song_title_sq1', title_lead), ('song_title_sq2', title_harm),
                          ('song_title_tri', title_bass), ('song_title_noi', title_noise),
                          ('song_tense_sq1', tense_lead), ('song_tense_sq2', tense_harm),
                          ('song_tense_tri', tense_bass), ('song_tense_noi', tense_noise)]:
            emit_bytes(f, lbl, data)
