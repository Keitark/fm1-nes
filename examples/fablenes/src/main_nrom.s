; SPDX-License-Identifier: Apache-2.0
; Copyright 2026 Keitark. Maintainer-authored, Claude Code-assisted game.
; Published with maintainer authorization; see examples/fablenes/README.md.
; ============================================================================
; ぼくがかんがえたさいきょうのファミコンゲーム — NROM (mapper 0) edition
;
; Runs on literally any NES, including boards/flashcarts with real read-only
; CHR-ROM (no SRAM to write into) - CHR is 100% static from power-on, baked
; into the .nes file, never touched by PPUDATA writes. No mapper chip, no
; bank switching, no scanline IRQ. Same gameplay/engine as the MMC3 original
; (src/main.s); the graphics pipeline is reworked to fit the constraints:
;   - Fixed CHR-ROM (8KB = 256 BG tiles + 256 sprite tiles): title + all 5
;     stages share ONE background tile atlas (stars/nebula generated once
;     and reused via palette-only reskinning; each stage's terrain is
;     cropped to a narrow strip and tiled to bound its unique-tile cost).
;     Only the nametable + palette differ per scene (both are ordinary
;     writable PPU RAM regardless of mapper) - reloaded during the same
;     screen-off window every scene transition already used.
;   - HUD (score/hi/rest/stage) is drawn with sprites, not BG tiles, since a
;     fixed HUD band under a scrolling world normally needs a mid-frame
;     split (MMC3 IRQ or sprite-0-hit polling); sprites sidestep that
;     entirely by being screen-position-fixed regardless of BG scroll.
;   - Parallax is a single scroll speed (no 3-band split) and the starfield
;     is static (no CHR-bank-swap twinkle) - both relied on hardware this
;     board doesn't have.
; Built with ca65.
; ============================================================================

PPUCTRL   = $2000
PPUMASK   = $2001
PPUSTATUS = $2002
OAMADDR   = $2003
PPUSCROLL = $2005
PPUADDR   = $2006
PPUDATA   = $2007
OAMDMA    = $4014

PAD_A      = $80
PAD_B      = $40
PAD_SELECT = $20
PAD_START  = $10
PAD_UP     = $08
PAD_DOWN   = $04
PAD_LEFT   = $02
PAD_RIGHT  = $01

; PPUCTRL base: NMI on, sprites $1000, BG $0000, inc +1
CTRL_BASE = $88

BOSS_AT_HI = >3000      ; frames until boss
BOSS_AT_LO = <3000

NUM_ENEMIES  = 6
NUM_PBULLETS = 8
NUM_EBULLETS = 8
NUM_EXPL     = 4

oam = $0200

; ---------------------------------------------------------------- zeropage
.zeropage
frame_flag: .res 1
nmis:       .res 1
pad:        .res 1
padp:       .res 1
padn:       .res 1
gstate:     .res 1      ; 0 title, 1 play, 2 dying, 3 gameover, 4 pause, 5 intro
gtimer:     .res 1
blink:      .res 1

scroll_sub: .res 1      ; single-band scroll, 8.8 + 9th bit (no parallax split)
scroll_lo:  .res 1
scroll_hi:  .res 1
scroll_speed_lo: .res 1 ; current stage's scroll speed (8.8/frame)
scroll_speed_hi: .res 1

oamp:       .res 1
oam_full:   .res 1
ms_ptr:     .res 2
sx:         .res 1
sy:         .res 1
t0:         .res 1
t1:         .res 1
t2:         .res 1
t3:         .res 1
t4:         .res 1
t5:         .res 1
t6:         .res 1
t7:         .res 1

px:         .res 1      ; player (ship left edge)
py:         .res 1
pinv:       .res 1
lives:      .res 1
shotcd:     .res 1

rng0:       .res 1
rng1:       .res 1

sptimer:    .res 1
st_lo:      .res 1      ; stage frame counter
st_hi:      .res 1
difficulty: .res 1

b_act:      .res 1      ; boss: 0 none, 1 enter, 2 fight, 3 dying
bx:         .res 1
by:         .res 1
bhp:        .res 1
bph:        .res 1
btimer:     .res 1
bflash:     .res 1

music_on:   .res 1
ch:         .res 1
np0:        .res 1      ; NMI-context ptr (sound)
np1:        .res 1
nt0:        .res 1
sfx_sq2:    .res 1
sfx_noi:    .res 1
sfx_kind:   .res 1
sfx_p:      .res 1

p0:         .res 1      ; main-context ptr
p1:         .res 1
q0:         .res 1      ; sprite palette ptr
q1:         .res 1

pspeed:     .res 1      ; player speed (2, or 3 when powered)
opt_on:     .res 1      ; konami power-up: options + rapid fire
kidx:       .res 1      ; konami code progress

stage:      .res 1      ; 1..5
do_next:    .res 1      ; flag: advance stage next frame
bsub:       .res 1      ; boss sub-state (dash phases etc.)
bt2:        .res 1      ; boss secondary timer
wp:         .res 1      ; wind phase (stage 3)
gk_t:       .res 1      ; gimmick timer (stage 2 meteors)
vx_p:       .res 1      ; player velocity, quarter-px (ice stage)
vy_p:       .res 1
pxs:        .res 1      ; player subpixel accumulators
pys:        .res 1

; ---------------------------------------------------------------- BSS
.bss
score:      .res 7
hisc:       .res 7

s_ptrl:     .res 4
s_ptrh:     .res 4
s_strl:     .res 4
s_strh:     .res 4
s_dur:      .res 4

pb_act:     .res NUM_PBULLETS
pb_x:       .res NUM_PBULLETS
pb_y:       .res NUM_PBULLETS

e_act:      .res NUM_ENEMIES    ; 0 = off, else type+1
e_x:        .res NUM_ENEMIES
e_xs:       .res NUM_ENEMIES
e_y:        .res NUM_ENEMIES
e_y0:       .res NUM_ENEMIES
e_hp:       .res NUM_ENEMIES
e_tim:      .res NUM_ENEMIES
e_ph:       .res NUM_ENEMIES

eb_kind:    .res NUM_EBULLETS   ; 0 = bullet, 1 = meteor
eb_act:     .res NUM_EBULLETS
eb_x:       .res NUM_EBULLETS
eb_xs:      .res NUM_EBULLETS
eb_y:       .res NUM_EBULLETS
eb_ys:      .res NUM_EBULLETS
eb_vxl:     .res NUM_EBULLETS
eb_vxh:     .res NUM_EBULLETS
eb_vyl:     .res NUM_EBULLETS
eb_vyh:     .res NUM_EBULLETS

ex_act:     .res NUM_EXPL
ex_x:       .res NUM_EXPL
ex_y:       .res NUM_EXPL
ex_t:       .res NUM_EXPL

; ---------------------------------------------------------------- header
; Mapper 0 (NROM-256): 32KB PRG, 8KB real CHR-ROM baked into the file. Some
; NROM boards (including WiFi-loader flashcarts) only have CHR-ROM silicon,
; not SRAM - this edition never writes to $0000-$1FFF, so it works on those
; too. No mapper nibble, no submapper trickery - the most compatible
; possible .nes file.
.segment "HEADER"
.byte "NES", $1A
.byte 2                 ; 2 x 16KB PRG
.byte 1                 ; 1 x 8KB CHR-ROM (real, read-only)
.byte $01                ; mapper 0 lo nibble = 0, vertical mirroring (bit0=1)
.byte $00
.res 8, 0

; ---------------------------------------------------------------- RODATA
.segment "RODATA"
.include "metasprites.inc"
.include "music.inc"
.include "nrom_data.inc"

; NROM has no scanline-IRQ parallax, so this is only used by boss/enemy
; sine movement (unlike the MMC3 edition it does not drive background scroll).
sine24: .byte $00,$0C,$17,$21,$29,$2F,$33,$35,$35,$33,$2F,$29,$21,$17,$0C,$00
        .byte $00,$F4,$E9,$DF,$D7,$D1,$CD,$CB,$CB,$CD,$D1,$D7,$DF,$E9,$F4,$00

; per-stage enemy mix (4 weighted entries each, indexed by rand&3)
stage_mix: .byte 0,1,2,0,  0,1,3,3,  1,2,4,4,  2,3,5,4,  3,4,5,5

; per-stage data
stage_song:   .byte 1, 1, 1, 2, 2
stage_bosshp: .byte 40, 56, 72, 88, 120
boss_ms_l:    .byte <ms_boss, <ms_boss2, <ms_boss, <ms_boss2, <ms_boss2
boss_ms_h:    .byte >ms_boss, >ms_boss2, >ms_boss, >ms_boss2, >ms_boss2

; single scroll speed per stage (8.8/frame) - no parallax split on NROM
stage_scroll_lo: .byte $60, $70, $80, $90, $C0
stage_scroll_hi: .byte $00, $00, $00, $00, $00

; boss volley vy offsets (8.8 pairs lo,hi)
volley3_tbl: .byte $00,$00, $60,$00, $A0,$FF
volley5_tbl: .byte $00,$00, $60,$00, $A0,$FF, $C0,$00, $40,$FF
volley_twin_tbl: .byte $C0,$FF, $40,$00
; 8-direction ring (vx lo,hi, vy lo,hi)
ring_tbl:
    .byte $80,$01, $00,$00
    .byte $10,$01, $F0,$FE
    .byte $00,$00, $80,$FE
    .byte $F0,$FE, $F0,$FE
    .byte $80,$FE, $00,$00
    .byte $F0,$FE, $10,$01
    .byte $00,$00, $80,$01
    .byte $10,$01, $10,$01

; STAGE letters (sprite tiles)
stage_text: .byte $79,$7A,$71,$70,$73    ; S,T,A,G,E

; enemy metasprites: type*2 + animframe (types 0-5, 12 contiguous entries)
ms_enemy_l: .byte <ms_enemyA0, <ms_enemyA1, <ms_enemyB0, <ms_enemyB1, <ms_enemyC0, <ms_enemyC1
            .byte <ms_dart0, <ms_dart1, <ms_bounce0, <ms_bounce1, <ms_spin0, <ms_spin1
ms_enemy_h: .byte >ms_enemyA0, >ms_enemyA1, >ms_enemyB0, >ms_enemyB1, >ms_enemyC0, >ms_enemyC1
            .byte >ms_dart0, >ms_dart1, >ms_bounce0, >ms_bounce1, >ms_spin0, >ms_spin1
ms_expl_l:  .byte <ms_expl0, <ms_expl1, <ms_expl2, <ms_expl3
ms_expl_h:  .byte >ms_expl0, >ms_expl1, >ms_expl2, >ms_expl3

enemy_hp_tbl:  .byte 1, 2, 3, 1, 2, 4
drum_env: .byte $26, $24, $21       ; kick, snare, hat (halt | decay rate)
drum_per: .byte $0C, $06, $02

song_tbl_sq1l: .byte <song_title_sq1, <song_stage_sq1, <song_tense_sq1
song_tbl_sq1h: .byte >song_title_sq1, >song_stage_sq1, >song_tense_sq1
song_tbl_sq2l: .byte <song_title_sq2, <song_stage_sq2, <song_tense_sq2
song_tbl_sq2h: .byte >song_title_sq2, >song_stage_sq2, >song_tense_sq2
song_tbl_tril: .byte <song_title_tri, <song_stage_tri, <song_tense_tri
song_tbl_trih: .byte >song_title_tri, >song_stage_tri, >song_tense_tri
song_tbl_noil: .byte <song_title_noi, <song_stage_noi, <song_tense_noi
song_tbl_noih: .byte >song_title_noi, >song_stage_noi, >song_tense_noi

go_text: .byte $70,$71,$72,$73,$00,$74,$75,$73,$76   ; GAME OVER
pause_text: .byte $77,$71,$78,$79,$73                ; PAUSE
; PUSH START: P,U,S,H,(gap),S,T,A,R,T - H comes from the extra 'CHI' letters
push_text: .byte $77,$78,$79,$AB, $79,$7A,$71,$76,$7A
konami_seq: .byte PAD_UP,PAD_UP,PAD_DOWN,PAD_DOWN,PAD_LEFT,PAD_RIGHT,PAD_LEFT,PAD_RIGHT,PAD_B,PAD_A
shotcd_tbl: .byte 9, 6                               ; normal / powered

; ---------------------------------------------------------------- CODE
.segment "CODE"

; ======================================================================
reset:
    sei
    cld
    ldx #$40
    stx $4017
    ldx #$FF
    txs
    inx
    stx PPUCTRL
    stx PPUMASK
    stx $4010
    bit PPUSTATUS
:   bit PPUSTATUS
    bpl :-
    ; clear RAM
    lda #0
    tax
:   sta $0000,x
    sta $0100,x
    sta $0200,x
    sta $0300,x
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne :-
:   bit PPUSTATUS
    bpl :-
    ; APU
    lda #$0F
    sta $4015
    lda #$30
    sta $4000
    sta $4004
    sta $400C
    lda #$80
    sta $4008
    ; rng seed
    lda #$A7
    sta rng0
    lda #$1D
    sta rng1
    ; CHR is real ROM now - nothing to upload, it's already wired to the PPU
    jsr go_title
    cli

main_loop:
    lda frame_flag
    beq main_loop
    lda #0
    sta frame_flag
    jsr read_pad
    lda gstate
    cmp #1
    beq @play
    cmp #2
    beq @dying
    cmp #3
    beq @gameover
    cmp #4
    beq @pause
    cmp #5
    beq @intro
    jsr st_title
    jmp main_loop
@intro:
    jsr st_intro
    jmp main_loop
@play:
    jsr st_play
    jmp main_loop
@dying:
    jsr st_dying
    jmp main_loop
@gameover:
    jsr st_gameover
    jmp main_loop
@pause:
    jsr st_pause
    jmp main_loop

; ======================================================================
; NMI - no MMC3 registers, no IRQ chain; single scroll value only
; ======================================================================
nmi:
    pha
    txa
    pha
    tya
    pha
    lda #0
    sta OAMADDR
    lda #>oam
    sta OAMDMA
    bit PPUSTATUS
    lda scroll_lo
    sta PPUSCROLL
    lda #0
    sta PPUSCROLL
    lda scroll_hi
    and #1
    ora #CTRL_BASE
    sta PPUCTRL
    jsr sound_update
    inc nmis
    lda #1
    sta frame_flag
    pla
    tay
    pla
    tax
    pla
    rti

; IRQ should never fire (no mapper IRQ, frame-counter IRQ disabled at boot),
; but keep a safe landing pad just in case.
irq:
    rti

; ======================================================================
; controller
; ======================================================================
read_pad:
    lda #1
    sta $4016
    lda #0
    sta $4016
    ldx #8
@l:
    lda $4016
    lsr
    rol pad
    dex
    bne @l
    lda padp
    eor #$FF
    and pad
    sta padn
    lda pad
    sta padp
    rts

; ======================================================================
; random
; ======================================================================
rand:
    ldy #8
    lda rng0
@l:
    asl
    rol rng1
    bcc :+
    eor #$39
:   dey
    bne @l
    sta rng0
    rts

; ======================================================================
; metasprite draw: ms_ptr, sx, sy
; ======================================================================
draw_ms:
    ldy #0
    lda (ms_ptr),y
    sta t0
    iny
@loop:
    lda oam_full
    bne @done
    lda (ms_ptr),y      ; dy
    iny
    clc
    adc sy
    sta t1
    lda (ms_ptr),y      ; tile
    iny
    sta t2
    lda (ms_ptr),y      ; attr
    iny
    sta t3
    lda (ms_ptr),y      ; dx
    iny
    clc
    adc sx
    bcs @skip           ; clipped off right
    ldx oamp
    sta oam+3,x
    lda t1
    sta oam+0,x
    lda t2
    sta oam+1,x
    lda t3
    sta oam+2,x
    inx
    inx
    inx
    inx
    stx oamp
    bne @skip
    lda #1
    sta oam_full
@skip:
    dec t0
    bne @loop
@done:
    rts

hide_rest:
    lda oam_full
    bne @rts
    ldx oamp
    lda #$F0
@l:
    sta oam,x
    inx
    inx
    inx
    inx
    bne @l
@rts:
    rts

; ======================================================================
; VRAM / CHR-RAM helpers (rendering + NMI must be off)
; ======================================================================
; p0/p1 = src, A = dest hi byte, X = page count. Dest lo byte is always 0.
vram_copy:
    bit PPUSTATUS
    sta PPUADDR
    lda #0
    sta PPUADDR
    ldy #0
@l:
    lda (p0),y
    sta PPUDATA
    iny
    bne @l
    inc p1
    dex
    bne @l
    rts

; p0/p1 = 16-byte BG palette, q0/q1 = 16-byte sprite palette
load_pal:
    bit PPUSTATUS
    lda #$3F
    sta PPUADDR
    lda #0
    sta PPUADDR
    ldy #0
@bg:
    lda (p0),y
    sta PPUDATA
    iny
    cpy #16
    bne @bg
    ldy #0
@sp:
    lda (q0),y
    sta PPUDATA
    iny
    cpy #16
    bne @sp
    bit PPUSTATUS
    lda #0
    sta PPUADDR
    sta PPUADDR
    rts

screen_off:
    lda #$08            ; NMI off
    sta PPUCTRL
    lda #0
    sta PPUMASK
    rts

screen_on:
    bit PPUSTATUS
    lda #0
    sta PPUSCROLL
    sta PPUSCROLL
    lda #CTRL_BASE
    sta PPUCTRL
    lda #$1E
    sta PPUMASK
    rts

; ======================================================================
; screen transitions - reload CHR-RAM + nametable + palette for a scene
; ======================================================================
go_title:
    jsr screen_off
    lda #<nrom_title_nam
    sta p0
    lda #>nrom_title_nam
    sta p1
    lda #$20
    ldx #4
    jsr vram_copy
    lda #<nrom_title_pal
    sta p0
    lda #>nrom_title_pal
    sta p1
    lda #<nrom_title_spr_pal
    sta q0
    lda #>nrom_title_spr_pal
    sta q1
    jsr load_pal
    lda #0
    sta scroll_sub
    sta scroll_lo
    sta scroll_hi
    sta gstate
    lda #$FF
    sta blink
    ldx #0              ; title song
    jsr music_play
    lda #0
    sta oamp
    sta oam_full
    jsr hide_rest
    jmp screen_on

start_game:
    jsr screen_off
    ; reset game state
    ldx #0
    lda #0
@z:
    sta score,x
    inx
    cpx #7
    bne @z
    ldx #0
@z2:
    sta e_act,x
    sta eb_act,x
    sta eb_kind,x
    cpx #NUM_PBULLETS
    bcs :+
    sta pb_act,x
:   cpx #NUM_EXPL
    bcs :+
    sta ex_act,x
:   inx
    cpx #NUM_EBULLETS
    bne @z2
    sta b_act
    sta st_lo
    sta st_hi
    sta difficulty
    sta pinv
    sta shotcd
    sta do_next
    sta wp
    sta gk_t
    sta bsub
    sta bt2
    sta vx_p
    sta vy_p
    sta pxs
    sta pys
    sta scroll_sub
    sta scroll_lo
    sta scroll_hi
    lda #3
    sta lives
    lda #24
    sta px
    lda #120
    sta py
    lda #2
    sta pspeed
    lda #0
    sta opt_on
    sta kidx
    lda #60
    sta sptimer
    lda #1
    sta stage
    jsr stage_apply
    lda #5              ; stage intro
    sta gstate
    lda #100
    sta gtimer
    ldx #1              ; stage 1 song
    jsr music_play
    jmp screen_on

; ----------------------------------------------------------------------
; apply per-stage look & feel (rendering + NMI must be OFF)
; ----------------------------------------------------------------------
stage_apply:
    ldx stage
    dex
    stx t7                      ; t7 = stage index 0..4, survives X-clobbers
    ; nametable: same 1KB pattern copied into BOTH physical nametables
    lda nrom_stage_nam_l,x
    sta p0
    lda nrom_stage_nam_h,x
    sta p1
    lda #$20
    ldx #4
    jsr vram_copy
    ldx t7
    lda nrom_stage_nam_l,x
    sta p0
    lda nrom_stage_nam_h,x
    sta p1
    lda #$24
    ldx #4
    jsr vram_copy
    ; CHR is fixed ROM now, shared by every stage - nothing to upload here
    ; palettes: BG + sprite, both tables indexed by stage*16
    lda t7
    asl
    asl
    asl
    asl                          ; t6 = stage_index * 16
    sta t6
    lda #<nrom_stage_pals
    clc
    adc t6
    sta p0
    lda #>nrom_stage_pals
    adc #0
    sta p1
    lda #<nrom_stage_spr_pals
    clc
    adc t6
    sta q0
    lda #>nrom_stage_spr_pals
    adc #0
    sta q1
    jsr load_pal
    ; single scroll speed for this stage
    ldx t7
    lda stage_scroll_lo,x
    sta scroll_speed_lo
    lda stage_scroll_hi,x
    sta scroll_speed_hi
    rts

; ----------------------------------------------------------------------
; advance to the next stage (called between frames from st_play)
; ----------------------------------------------------------------------
next_stage:
    inc stage
    lda stage
    cmp #6
    bcc @ok
    lda #1
    sta stage
    lda difficulty
    cmp #5
    bcs @ok
    inc difficulty
@ok:
    ; clear world objects (keep player bullets in flight)
    ldx #NUM_EBULLETS-1
    lda #0
@c:
    sta eb_act,x
    sta eb_kind,x
    cpx #NUM_ENEMIES
    bcs :+
    sta e_act,x
:   cpx #NUM_EXPL
    bcs :+
    sta ex_act,x
:   dex
    bpl @c
    sta st_lo
    sta st_hi
    sta b_act
    sta wp
    sta gk_t
    sta bsub
    sta bt2
    sta vx_p
    sta vy_p
    lda #60
    sta sptimer
    jsr screen_off
    jsr stage_apply
    jsr screen_on
    lda #5
    sta gstate
    lda #100
    sta gtimer
    ldx stage
    dex
    lda stage_song,x
    tax
    jsr music_play
    rts

; ======================================================================
; HUD (sprites) - always drawn FIRST in a frame's OAM fill, so it has
; priority over gameplay sprites if the 64-sprite budget runs out.
; ======================================================================
; A = tile; t5 = fixed Y row; t1 = running X (auto +8 after each call).
hud_emit:
    ldx oamp
    sta oam+1,x
    lda t5
    sta oam+0,x
    lda #0
    sta oam+2,x
    lda t1
    sta oam+3,x
    inx
    inx
    inx
    inx
    stx oamp
    lda t1
    clc
    adc #8
    sta t1
    rts

draw_hud:
    lda #0
    sta t5
    lda #8
    sta t1
    ldy #0
@lbl:
    lda hud_score_lbl,y
    jsr hud_emit
    iny
    cpy #5
    bne @lbl
    lda #8
    sta t5
    lda #8
    sta t1
    ldy #0
@sd:
    lda score,y
    clc
    adc #SPRITE_DIGIT_BASE
    jsr hud_emit
    iny
    cpy #7
    bne @sd
    lda #16
    sta t5
    lda #8
    sta t1
    lda hud_hi_lbl+0
    jsr hud_emit
    lda hud_hi_lbl+1
    jsr hud_emit
    lda #40
    sta t1
    lda hud_stage_lbl
    jsr hud_emit
    lda stage
    clc
    adc #SPRITE_DIGIT_BASE
    jsr hud_emit
    lda #24
    sta t5
    lda #8
    sta t1
    ldy #0
@hd:
    lda hisc,y
    clc
    adc #SPRITE_DIGIT_BASE
    jsr hud_emit
    iny
    cpy #7
    bne @hd
    lda #32
    sta t5
    lda #8
    sta t1
    ldy #0
@rl:
    lda hud_rest_lbl,y
    jsr hud_emit
    iny
    cpy #4
    bne @rl
    lda lives
    clc
    adc #SPRITE_DIGIT_BASE
    jmp hud_emit

; ======================================================================
; game states
; ======================================================================
st_title:
    lda #0
    sta oamp
    sta oam_full
    lda nmis
    and #$20
    beq @skip
    lda #180
    sta t5
    lda #92
    sta t1
    ldy #0
@pl:
    lda push_text,y
    jsr hud_emit
    iny
    cpy #9
    bne @pl
@skip:
    jsr hide_rest
    lda padn
    and #PAD_START
    beq @rts
    jmp start_game
@rts:
    rts

st_play:
    lda do_next
    beq :+
    lda #0
    sta do_next
    jmp next_stage
:   lda padn
    and #PAD_START
    beq :+
    lda #4              ; pause
    sta gstate
    lda #0
    sta kidx
    rts
:   jsr update_player
    jsr update_world
    jsr coll_pb
    lda pinv
    bne @noc
    jsr coll_player
@noc:
    lda #0
    sta oamp
    sta oam_full
    jsr draw_hud
    jsr draw_player
    jsr draw_world
    jmp hide_rest

st_dying:
    jsr update_world
    jsr coll_pb
    lda #0
    sta oamp
    sta oam_full
    jsr draw_hud
    jsr draw_world
    jsr hide_rest
    dec gtimer
    bne @rts
    lda lives
    beq @gameover
    lda #24
    sta px
    lda #120
    sta py
    lda #120
    sta pinv
    lda #1
    sta gstate
    rts
@gameover:
    lda #3
    sta gstate
    lda #240
    sta gtimer
    jsr music_stop
@rts:
    rts

st_gameover:
    jsr update_world
    lda #0
    sta oamp
    sta oam_full
    jsr draw_hud
    ; GAME OVER letters
    lda #92
    sta t5
    lda #96
    sta t1
    ldy #0
@gl:
    lda go_text,y
    beq @adv
    lda go_text,y
    jsr hud_emit
    jmp @adv2
@adv:
    lda t1
    clc
    adc #8
    sta t1
@adv2:
    iny
    cpy #9
    bne @gl
    jsr draw_world
    jsr hide_rest
    dec gtimer
    bne @rts
    jmp go_title
@rts:
    rts

st_intro:
    jsr update_bands
    lda #0
    sta oamp
    sta oam_full
    jsr draw_hud
    ; "STAGE n" banner
    lda #112
    sta t5
    lda #100
    sta t1
    ldy #0
@sl:
    lda stage_text,y
    jsr hud_emit
    iny
    cpy #5
    bne @sl
    lda #4
    clc
    adc t1
    sta t1
    lda stage
    clc
    adc #$7A            ; digit sprite tiles '1'..'5' at $7B-$7F
    jsr hud_emit
    jsr draw_player
    jsr hide_rest
    dec gtimer
    bne @rts
    lda #1
    sta gstate
@rts:
    rts

st_pause:
    lda padn
    beq @draw
    and #PAD_START
    beq @code
    lda #1              ; resume
    sta gstate
    jmp @draw
@code:
    ldy kidx
    lda padn
    cmp konami_seq,y
    beq @ok
    lda #0              ; wrong button: start over
    sta kidx
    jmp @draw
@ok:
    iny
    sty kidx
    cpy #10
    bne @draw
    ; コナミコマンド成立！ options + speed + rapid fire
    lda #1
    sta opt_on
    lda #3
    sta pspeed
    lda #0
    sta kidx
    lda #2
    jsr sfx_play
@draw:
    lda #0
    sta oamp
    sta oam_full
    jsr draw_hud
    ; blinking PAUSE text
    lda nmis
    and #$10
    beq @world
    lda #108
    sta t5
    lda #112
    sta t1
    ldy #0
@pl:
    lda pause_text,y
    jsr hud_emit
    iny
    cpy #5
    bne @pl
@world:
    jsr draw_player
    jsr draw_world
    jmp hide_rest

; ======================================================================
; player
; ======================================================================
update_player:
    lda pinv
    beq :+
    dec pinv
:   ; stage 3 gimmick: wind currents push the ship
    lda stage
    cmp #3
    bne @nowind
    inc wp
    lda wp
    and #7
    bne @nowind
    lda wp
    lsr
    lsr
    lsr
    and #31
    tay
    lda sine24,y
    bmi @wup
    cmp #12
    bcc @nowind
    lda py
    cmp #214
    bcs @nowind
    inc py
    jmp @nowind
@wup:
    cmp #$F5
    bcs @nowind
    lda py
    cmp #40
    bcc @nowind
    dec py
@nowind:
    ; stage 4 gimmick: ice inertia
    lda stage
    cmp #4
    bne @norm
    jsr ice_move
    jmp @fire
@norm:
    lda pad
    and #PAD_LEFT
    beq :+
    lda px
    sec
    sbc pspeed
    cmp #8
    bcc :+
    sta px
:   lda pad
    and #PAD_RIGHT
    beq :+
    lda px
    clc
    adc pspeed
    cmp #168
    bcs :+
    sta px
:   lda pad
    and #PAD_UP
    beq :+
    lda py
    sec
    sbc pspeed
    cmp #38
    bcc :+
    sta py
:   lda pad
    and #PAD_DOWN
    beq :+
    lda py
    clc
    adc pspeed
    cmp #216
    bcs :+
    sta py
:
@fire:
    ; shooting
    lda shotcd
    beq :+
    dec shotcd
:   lda pad
    and #PAD_A
    beq @rts
    lda shotcd
    bne @rts
    lda px
    clc
    adc #14
    sta t0
    lda py
    clc
    adc #5
    sta t1
    jsr spawn_pbullet
    lda opt_on
    beq @cd
    ; options fire too (top / bottom orbs)
    lda px
    clc
    adc #10
    sta t0
    lda py
    sec
    sbc #11
    cmp #34
    bcs :+
    lda #34             ; keep out of the HUD rows
:   sta t1
    jsr spawn_pbullet
    lda px
    clc
    adc #10
    sta t0
    lda py
    clc
    adc #23
    sta t1
    jsr spawn_pbullet
@cd:
    ldy opt_on
    lda shotcd_tbl,y
    sta shotcd
    lda #0
    jsr sfx_play
@rts:
    rts

; stage 4: slippery velocity-based movement (quarter-px velocity units)
ice_move:
    lda pad
    and #PAD_LEFT
    beq :+
    lda vx_p
    cmp #$F6            ; -10 cap
    beq :+
    dec vx_p
:   lda pad
    and #PAD_RIGHT
    beq :+
    lda vx_p
    cmp #10
    beq :+
    inc vx_p
:   lda pad
    and #PAD_UP
    beq :+
    lda vy_p
    cmp #$F6
    beq :+
    dec vy_p
:   lda pad
    and #PAD_DOWN
    beq :+
    lda vy_p
    cmp #10
    beq :+
    inc vy_p
:   ; px += vx * 64 (8.8)
    ldx #0
    lda vx_p
    bpl :+
    ldx #$FF
:   sta t0
    stx t1
    ldx #6
@shx:
    asl t0
    rol t1
    dex
    bne @shx
    lda pxs
    clc
    adc t0
    sta pxs
    lda px
    adc t1
    sta t2
    lda t1
    bmi @xleft
    lda t2
    cmp #168
    bcc @xok
    lda #167
    sta t2
    ldx #0
    stx vx_p
    beq @xok
@xleft:
    lda t2
    cmp #8
    bcc @xclamp
    cmp #168
    bcc @xok
@xclamp:
    lda #8
    sta t2
    ldx #0
    stx vx_p
@xok:
    lda t2
    sta px
    ; py += vy * 64
    ldx #0
    lda vy_p
    bpl :+
    ldx #$FF
:   sta t0
    stx t1
    ldx #6
@shy:
    asl t0
    rol t1
    dex
    bne @shy
    lda pys
    clc
    adc t0
    sta pys
    lda py
    adc t1
    sta t2
    lda t1
    bmi @yup
    lda t2
    cmp #216
    bcc @yok
    lda #215
    sta t2
    ldx #0
    stx vy_p
    beq @yok
@yup:
    lda t2
    cmp #38
    bcc @yclamp
    cmp #216
    bcc @yok
@yclamp:
    lda #38
    sta t2
    ldx #0
    stx vy_p
@yok:
    lda t2
    sta py
    rts

; t0 = x, t1 = y
spawn_pbullet:
    ldx #NUM_PBULLETS-1
@f:
    lda pb_act,x
    beq @go
    dex
    bpl @f
    rts
@go:
    lda #1
    sta pb_act,x
    lda t0
    sta pb_x,x
    lda t1
    sta pb_y,x
    rts

draw_player:
    lda pinv
    beq @solid
    lda nmis
    and #$02
    bne @rts            ; blink while invincible
@solid:
    lda nmis
    and #$04
    bne @f1
    lda #<ms_player0
    sta ms_ptr
    lda #>ms_player0
    sta ms_ptr+1
    jmp @go
@f1:
    lda #<ms_player1
    sta ms_ptr
    lda #>ms_player1
    sta ms_ptr+1
@go:
    lda px
    sec
    sbc #7              ; metasprite origin = flame left
    sta sx
    lda py
    sta sy
    jsr draw_ms
    ; option orbs (konami power-up)
    lda opt_on
    beq @rts
    lda nmis
    lsr
    lsr
    lsr
    and #1
    beq @o0
    lda #<ms_option1
    sta ms_ptr
    lda #>ms_option1
    sta ms_ptr+1
    jmp @od
@o0:
    lda #<ms_option0
    sta ms_ptr
    lda #>ms_option0
    sta ms_ptr+1
@od:
    lda px
    clc
    adc #1
    sta sx
    lda py
    sec
    sbc #13
    sta sy
    jsr draw_ms
    lda px
    clc
    adc #1
    sta sx
    lda py
    clc
    adc #21
    sta sy
    jmp draw_ms
@rts:
    rts

player_die:
    lda px
    clc
    adc #4
    sta t4
    lda py
    sta t5
    jsr spawn_expl
    lda #1
    jsr sfx_play
    lda #0              ; lose konami power-ups
    sta opt_on
    lda #2
    sta pspeed
    dec lives
    lda #2
    sta gstate
    lda #70
    sta gtimer
    rts

; ======================================================================
; world update (runs in play / dying / gameover)
; ======================================================================
update_bands:
    lda scroll_sub
    clc
    adc scroll_speed_lo
    sta scroll_sub
    lda scroll_lo
    adc scroll_speed_hi
    sta scroll_lo
    lda scroll_hi
    adc #0
    and #1
    sta scroll_hi
    rts

update_world:
    jsr update_bands
    jsr update_gimmicks
    jsr update_pbullets
    jsr update_spawner
    jsr update_enemies
    jsr update_ebullets
    jsr update_expl
    jmp update_boss

; per-stage ambient hazards
update_gimmicks:
    lda stage
    cmp #2
    bne @rts            ; stage 2: meteor shower
    lda b_act
    bne @rts
    lda gk_t
    beq @spawn
    dec gk_t
@rts:
    rts
@spawn:
    lda #30
    sta gk_t
    ldx #NUM_EBULLETS-1
@f:
    lda eb_act,x
    beq @go
    dex
    bpl @f
    rts
@go:
    lda #1
    sta eb_act,x
    sta eb_kind,x
    lda #1
    sta eb_vyh,x
    jsr rand
    and #$7F
    clc
    adc #112
    sta eb_x,x
    lda #40
    sta eb_y,x
    lda #0
    sta eb_xs,x
    sta eb_ys,x
    lda #$40
    sta eb_vxl,x
    lda #$FF
    sta eb_vxh,x        ; drift left -0.75
    jsr rand
    and #$3F
    clc
    adc #$40
    sta eb_vyl,x        ; fall 1.25 - 1.5
    rts

update_pbullets:
    ldx #NUM_PBULLETS-1
@l:
    lda pb_act,x
    beq @next
    lda pb_x,x
    clc
    adc #4
    sta pb_x,x
    cmp #$F0
    bcc @next
    lda #0
    sta pb_act,x
@next:
    dex
    bpl @l
    rts

update_spawner:
    lda gstate
    cmp #1
    bne @rts            ; only spawn while playing
    lda b_act
    bne @rts            ; not during boss
    ; stage clock
    inc st_lo
    bne :+
    inc st_hi
:   lda st_hi
    cmp #BOSS_AT_HI
    bcc @waves
    lda st_lo
    cmp #BOSS_AT_LO
    bcc @waves
    jmp spawn_boss
@waves:
    dec sptimer
    bne @rts
    ; reset timer: 84 - difficulty*12, floor 32
    lda difficulty
    asl
    asl
    sta t0
    asl
    clc                 ; t0*1.5... difficulty*12
    adc t0
    sta t0
    lda #84
    sec
    sbc t0
    cmp #32
    bcs :+
    lda #32
:   sta sptimer
    ; find free slot
    ldx #NUM_ENEMIES-1
@fs:
    lda e_act,x
    beq @spawn
    dex
    bpl @fs
@rts:
    rts
@spawn:
    jmp spawn_enemy_slot

; fill enemy slot X with a stage-appropriate enemy
spawn_enemy_slot:
    jsr rand
    and #3
    sta t0
    lda stage
    sec
    sbc #1
    asl
    asl
    clc
    adc t0
    tay
    lda stage_mix,y
    sta t0              ; type 0-5
    tay
    lda enemy_hp_tbl,y
    sta e_hp,x
    lda t0
    clc
    adc #1
    sta e_act,x
    lda #239
    sta e_x,x
    lda #0
    sta e_xs,x
    jsr rand
    and #$7F
    clc
    adc #48
    cmp #200
    bcc :+
    sbc #80
:   sta e_y,x
    sta e_y0,x
    jsr rand
    sta e_ph,x
    and #$3F
    clc
    adc #50
    sta e_tim,x
    ; per-type fixups
    lda t0
    cmp #3
    bne @notdart
    lda #0
    sta e_ph,x          ; dart: default flies left
    lda stage
    cmp #5
    bne @done
    jsr rand
    and #1
    beq @done
    lda #1
    sta e_ph,x          ; stage 5: ambush from behind!
    lda #6
    sta e_x,x
    rts
@notdart:
    cmp #4
    bne @done
    lda e_ph,x
    and #1
    sta e_ph,x          ; bouncer: keep direction bit only
@done:
    rts

update_enemies:
    ldx #NUM_ENEMIES-1
@l:
    lda e_act,x
    bne @on
    jmp @next
@on:
    cmp #2
    bne :+
    jmp @sine
:   cmp #3
    bne :+
    jmp @turret
:   cmp #4
    bne :+
    jmp @dart
:   cmp #5
    bne :+
    jmp @bounce
:   cmp #6
    bne :+
    jmp @spin
:   ; type 0 straight: -1.5 px/f
    lda e_xs,x
    clc
    adc #$80
    sta e_xs,x
    lda e_x,x
    adc #$FE
    sta e_x,x
    jmp @bounds
@sine:
    lda e_x,x           ; -1.0 px/f
    clc
    adc #$FF
    sta e_x,x
    lda e_ph,x
    clc
    adc #2
    sta e_ph,x
    lsr
    lsr
    lsr
    and #31
    tay
    lda sine24,y
    clc
    adc e_y0,x
    sta e_y,x
    jmp @bounds
@turret:
    lda e_xs,x          ; -0.5 px/f
    clc
    adc #$80
    sta e_xs,x
    lda e_x,x
    adc #$FF
    sta e_x,x
    jmp @bounds
@dart:
    lda e_ph,x
    bne @dright
    lda e_x,x
    sec
    sbc #3
    sta e_x,x
    jmp @bounds
@dright:
    lda e_x,x
    clc
    adc #3
    sta e_x,x
    jmp @bounds
@bounce:
    lda e_x,x           ; -1.0 px/f
    clc
    adc #$FF
    sta e_x,x
    lda e_ph,x
    and #1
    bne @bup
    lda e_y0,x          ; dive 1.5 px/f
    clc
    adc #$80
    sta e_y0,x
    lda e_y,x
    adc #1
    sta e_y,x
    cmp #204
    bcc @bounds
    lda #1
    sta e_ph,x
    jmp @bounds
@bup:
    lda e_y0,x
    sec
    sbc #$80
    sta e_y0,x
    lda e_y,x
    sbc #1
    sta e_y,x
    cmp #44
    bcs @bounds
    lda #0
    sta e_ph,x
    jmp @bounds
@spin:
    lda e_xs,x          ; -0.75 px/f
    clc
    adc #$40
    sta e_xs,x
    lda e_x,x
    adc #$FF
    sta e_x,x
    lda e_ph,x
    clc
    adc #2
    sta e_ph,x
    lsr
    lsr
    lsr
    and #31
    tay
    lda sine24,y
    clc
    adc e_y0,x
    sta e_y,x
@bounds:
    lda e_x,x
    cmp #$F8
    bcs @kill
    cmp #4
    bcc @kill
    ; firing (darts never fire)
    lda e_act,x
    cmp #4
    beq @next
    dec e_tim,x
    bne @next
    lda difficulty
    asl
    asl
    sta t0
    lda #110
    sec
    sbc t0
    sta e_tim,x
    jsr enemy_fire
@next:
    dex
    bmi @done
    jmp @l
@done:
    rts
@kill:
    lda #0
    sta e_act,x
    jmp @next

; X = enemy index
enemy_fire:
    lda e_x,x
    cmp #230
    bcs @rts            ; wait until fully on screen
    ; find free eb slot -> Y
    ldy #NUM_EBULLETS-1
@f:
    lda eb_act,y
    beq @go
    dey
    bpl @f
@rts:
    rts
@go:
    lda #1
    sta eb_act,y
    lda #0
    sta eb_kind,y
    lda e_x,x
    clc
    adc #4
    sta eb_x,y
    lda e_y,x
    clc
    adc #4
    sta eb_y,y
    lda #0
    sta eb_xs,y
    sta eb_ys,y
    lda e_act,x
    cmp #3              ; turret aims
    beq @aimed
    cmp #6              ; spinner aims too
    beq @aimed
    lda #0
    sta eb_vxl,y
    sta eb_vyl,y
    sta eb_vyh,y
    lda #$FE            ; -2.0 px/f straight
    sta eb_vxh,y
    rts
@aimed:
    jsr aim_at_player   ; uses t4..t7, X = enemy
    lda t6
    sta eb_vxl,y
    lda t4
    sta eb_vxh,y
    lda t7
    sta eb_vyl,y
    lda t5
    sta eb_vyh,y
    rts

; compute aimed velocity (8.8) from enemy X toward player -> t4:t6, t5:t7
aim_at_player:
    lda px
    clc
    adc #8
    lsr
    sta t0
    lda e_x,x
    clc
    adc #8
    lsr
    sta t1
    lda t0
    sec
    sbc t1
    sta t4              ; dx (halved)
    lda py
    clc
    adc #8
    lsr
    sta t0
    lda e_y,x
    clc
    adc #8
    lsr
    sta t1
    lda t0
    sec
    sbc t1
    sta t5              ; dy (halved)
; t4/t5 = halved deltas -> t4:t6 / t5:t7 = 8.8 velocity (max ~2 px/f)
aim_core:
    lda #0
    sta t6
    sta t7
@chk:
    lda t4
    jsr abs8
    cmp #2
    bcs @shift
    lda t5
    jsr abs8
    cmp #2
    bcc @done
@shift:
    lda t4
    cmp #$80
    ror t4
    ror t6
    lda t5
    cmp #$80
    ror t5
    ror t7
    jmp @chk
@done:
    lda t4
    ora t5
    ora t6
    ora t7
    bne @rts
    lda #$FF            ; degenerate: straight left
    sta t4
@rts:
    rts

abs8:
    cmp #$80
    bcc @rts
    eor #$FF
    clc
    adc #1
@rts:
    rts

update_ebullets:
    ldx #NUM_EBULLETS-1
@l:
    lda eb_act,x
    beq @next
    lda eb_xs,x
    clc
    adc eb_vxl,x
    sta eb_xs,x
    lda eb_x,x
    adc eb_vxh,x
    sta eb_x,x
    cmp #$F8
    bcs @kill
    cmp #4
    bcc @kill
    lda eb_ys,x
    clc
    adc eb_vyl,x
    sta eb_ys,x
    lda eb_y,x
    adc eb_vyh,x
    sta eb_y,x
    cmp #36
    bcc @kill
    cmp #228
    bcs @kill
@next:
    dex
    bpl @l
    rts
@kill:
    lda #0
    sta eb_act,x
    jmp @next

; t4 = x, t5 = y
spawn_expl:
    ldx #NUM_EXPL-1
@f:
    lda ex_act,x
    beq @go
    dex
    bpl @f
    ldx #0              ; steal slot 0
@go:
    lda #1
    sta ex_act,x
    lda t4
    sta ex_x,x
    lda t5
    sta ex_y,x
    lda #0
    sta ex_t,x
    rts

update_expl:
    ldx #NUM_EXPL-1
@l:
    lda ex_act,x
    beq @next
    inc ex_t,x
    lda ex_t,x
    cmp #16
    bcc @next
    lda #0
    sta ex_act,x
@next:
    dex
    bpl @l
    rts

; ======================================================================
; boss
; ======================================================================
spawn_boss:
    lda #1
    sta b_act
    lda #232
    sta bx
    lda #104
    sta by
    lda difficulty
    asl
    asl
    asl
    asl
    sta t0
    ldx stage
    dex
    lda stage_bosshp,x
    clc
    adc t0
    bcs @cap
    cmp #200
    bcc :+
@cap:
    lda #200
:   sta bhp
    lda #0
    sta bph
    sta bflash
    sta bsub
    sta bt2
    lda #60
    sta btimer
    rts

update_boss:
    lda b_act
    bne :+
    rts
:   lda bflash
    beq :+
    dec bflash
:   lda b_act
    cmp #1
    beq @enter
    cmp #2
    beq @fight
    ; dying
    dec btimer
    lda btimer
    and #7
    bne @dchk
    jsr rand
    and #15
    clc
    adc bx
    sta t4
    jsr rand
    and #31
    clc
    adc by
    sta t5
    jsr spawn_expl
    lda #1
    jsr sfx_play
@dchk:
    lda btimer
    bne @rts
    lda #0
    sta b_act
    lda #5              ; +5000
    ldx #3
    jsr add_score
    lda #1
    sta do_next         ; advance to the next stage
@rts:
    rts
@enter:
    dec bx
    lda bx
    cmp #192
    bne @rts
    lda #2
    sta b_act
    rts
@fight:
    lda stage
    cmp #2
    bne :+
    jmp boss_f2
:   cmp #3
    bne :+
    jmp boss_f3
:   cmp #4
    bne :+
    jmp boss_f4
:   cmp #5
    bne :+
    jmp boss_f5
    ; --- stage 1: slow sine + 3-way spread ---
:   jsr boss_sine
    dec btimer
    bne @rts
    jsr boss_reset_timer
    lda #<volley3_tbl
    sta p0
    lda #>volley3_tbl
    sta p1
    ldy #3
    jmp boss_volley

; --- stage 2: fast linear bounce + twin shots ---
boss_f2:
    lda bsub
    and #1
    bne @up
    lda by
    clc
    adc #2
    cmp #150
    bcc :+
    inc bsub
:   sta by
    jmp @shoot
@up:
    lda by
    sec
    sbc #2
    cmp #58
    bcs :+
    inc bsub
:   sta by
@shoot:
    dec btimer
    bne @rts
    jsr boss_reset_timer
    lda #<volley_twin_tbl
    sta p0
    lda #>volley_twin_tbl
    sta p1
    ldy #2
    jmp boss_volley
@rts:
    rts

; --- stage 3: charger — hover, dash in, unleash a ring, back off ---
boss_f3:
    lda bsub
    beq @hover
    cmp #1
    beq @dash
    cmp #2
    beq @pause
    lda bx              ; return
    clc
    adc #2
    sta bx
    cmp #192
    bcc @rts
    lda #0
    sta bsub
    lda #120
    sta btimer
@rts:
    rts
@hover:
    jsr boss_sine
    dec btimer
    bne @rts
    inc bsub
    rts
@dash:
    lda bx
    sec
    sbc #3
    sta bx
    cmp #72
    bcs @rts
    inc bsub
    jsr boss_ring
    lda #30
    sta btimer
    rts
@pause:
    dec btimer
    bne @rts
    inc bsub
    rts

; --- stage 4: summoner — calls minions + aimed shots ---
boss_f4:
    jsr boss_sine
    inc bt2
    lda bt2
    cmp #130
    bcc @fire
    lda #0
    sta bt2
    ldx #NUM_ENEMIES-1
@f:
    lda e_act,x
    beq @call
    dex
    bpl @f
    bmi @fire
@call:
    jsr spawn_enemy_slot
@fire:
    dec btimer
    bne @rts
    jsr boss_reset_timer
    jmp boss_aim1
@rts:
    rts

; --- stage 5: final core — sine + 5-way + periodic rings ---
boss_f5:
    jsr boss_sine
    inc bt2
    lda bt2
    cmp #200
    bcc :+
    lda #0
    sta bt2
    jsr boss_ring
:   dec btimer
    bne @rts
    jsr boss_reset_timer
    lda #<volley5_tbl
    sta p0
    lda #>volley5_tbl
    sta p1
    ldy #5
    jmp boss_volley
@rts:
    rts

; ---------------- boss helpers ----------------
boss_sine:
    inc bph
    lda bph
    lsr
    lsr
    and #31
    tay
    lda sine24,y
    clc
    adc #104
    sta by
    rts

boss_reset_timer:
    lda difficulty
    asl
    asl
    sta t0
    lda stage
    asl
    clc
    adc t0
    sta t0
    lda #64
    sec
    sbc t0
    cmp #24
    bcs :+
    lda #24
:   sta btimer
    rts

; fire Y bullets leftward with vy offsets from table at p0 (pairs lo,hi)
boss_volley:
    sty t4
    lda #0
    sta t3
@v:
    ldx #NUM_EBULLETS-1
@f:
    lda eb_act,x
    beq @go
    dex
    bpl @f
    rts
@go:
    lda #1
    sta eb_act,x
    lda #0
    sta eb_kind,x
    sta eb_xs,x
    sta eb_ys,x
    lda bx
    sta eb_x,x
    lda by
    clc
    adc #22
    sta eb_y,x
    lda #$80
    sta eb_vxl,x
    lda #$FE
    sta eb_vxh,x        ; -1.5
    lda t3
    asl
    tay
    lda (p0),y
    sta eb_vyl,x
    iny
    lda (p0),y
    sta eb_vyh,x
    inc t3
    lda t3
    cmp t4
    bne @v
    rts

; 8 bullets in all directions from the boss core
boss_ring:
    lda #0
    sta t3
@r:
    ldx #NUM_EBULLETS-1
@f:
    lda eb_act,x
    beq @go
    dex
    bpl @f
    rts
@go:
    lda #1
    sta eb_act,x
    lda #0
    sta eb_kind,x
    sta eb_xs,x
    sta eb_ys,x
    lda bx
    clc
    adc #12
    sta eb_x,x
    lda by
    clc
    adc #22
    sta eb_y,x
    lda t3
    asl
    asl
    tay
    lda ring_tbl,y
    sta eb_vxl,x
    lda ring_tbl+1,y
    sta eb_vxh,x
    lda ring_tbl+2,y
    sta eb_vyl,x
    lda ring_tbl+3,y
    sta eb_vyh,x
    inc t3
    lda t3
    cmp #8
    bne @r
    rts

; single aimed shot from the boss cannon
boss_aim1:
    ldx #NUM_EBULLETS-1
@f:
    lda eb_act,x
    beq @go
    dex
    bpl @f
    rts
@go:
    lda px
    clc
    adc #8
    lsr
    sta t0
    lda bx
    clc
    adc #8
    lsr
    sta t1
    lda t0
    sec
    sbc t1
    sta t4
    lda py
    clc
    adc #8
    lsr
    sta t0
    lda by
    clc
    adc #22
    lsr
    sta t1
    lda t0
    sec
    sbc t1
    sta t5
    jsr aim_core
    lda #1
    sta eb_act,x
    lda #0
    sta eb_kind,x
    sta eb_xs,x
    sta eb_ys,x
    lda bx
    sta eb_x,x
    lda by
    clc
    adc #22
    sta eb_y,x
    lda t6
    sta eb_vxl,x
    lda t4
    sta eb_vxh,x
    lda t7
    sta eb_vyl,x
    lda t5
    sta eb_vyh,x
    rts

; ======================================================================
; collisions
; ======================================================================
coll_pb:
    ldy #NUM_PBULLETS-1
@pbl:
    lda pb_act,y
    bne :+
    jmp @pbn
:   ; vs enemies
    ldx #NUM_ENEMIES-1
@el:
    lda e_act,x
    beq @en
    lda pb_x,y
    sec
    sbc e_x,x
    clc
    adc #12
    cmp #26
    bcs @en
    lda pb_y,y
    sec
    sbc e_y,x
    clc
    adc #14
    cmp #26
    bcs @en
    ; hit enemy
    lda #0
    sta pb_act,y
    dec e_hp,x
    bne @hitsfx
    jsr kill_enemy
    jmp @pbn
@hitsfx:
    lda #2
    jsr sfx_play
    jmp @pbn
@en:
    dex
    bpl @el
    ; vs boss
    lda b_act
    cmp #2
    bne @pbn
    lda pb_x,y
    sec
    sbc bx
    clc
    adc #4
    cmp #40
    bcs @pbn
    lda pb_y,y
    sec
    sbc by
    clc
    adc #6
    cmp #58
    bcs @pbn
    lda #0
    sta pb_act,y
    lda #8
    sta bflash
    lda #2
    jsr sfx_play
    dec bhp
    bne @pbn
    lda #3              ; boss death
    sta b_act
    lda #64
    sta btimer
    lda #1
    jsr sfx_play
@pbn:
    dey
    bmi @rts
    jmp @pbl
@rts:
    rts

; X = enemy index (preserves Y)
kill_enemy:
    lda e_x,x
    sta t4
    lda e_y,x
    sta t5
    lda e_act,x
    sta t2              ; type+1 = score amount (100/200/300)
    lda #0
    sta e_act,x
    sty t3
    jsr spawn_expl      ; clobbers X
    lda #1
    jsr sfx_play
    lda t2
    ldx #4              ; hundreds digit
    jsr add_score
    ldy t3
    rts

coll_player:
    ; enemy bullets vs player
    ldx #NUM_EBULLETS-1
@ebl:
    lda eb_act,x
    beq @ebn
    lda eb_x,x
    sec
    sbc px
    clc
    adc #5
    cmp #18
    bcs @ebn
    lda eb_y,x
    sec
    sbc py
    clc
    adc #5
    cmp #18
    bcs @ebn
    lda #0
    sta eb_act,x
    jmp player_die
@ebn:
    dex
    bpl @ebl
    ; enemies vs player
    ldx #NUM_ENEMIES-1
@el:
    lda e_act,x
    beq @en
    lda e_x,x
    sec
    sbc px
    clc
    adc #12
    cmp #25
    bcs @en
    lda e_y,x
    sec
    sbc py
    clc
    adc #12
    cmp #25
    bcs @en
    lda #1
    sta e_hp,x
    dec e_hp,x          ; force kill
    jsr kill_enemy
    jmp player_die
@en:
    dex
    bpl @el
    ; boss vs player
    lda b_act
    cmp #2
    bne @rts
    lda bx
    sec
    sbc px
    clc
    adc #14
    cmp #44
    bcs @rts
    lda by
    sec
    sbc py
    clc
    adc #14
    cmp #60
    bcs @rts
    jmp player_die
@rts:
    rts

; ======================================================================
; scoring
; ======================================================================
; A = amount, X = digit index (0 msd .. 6 lsd)
add_score:
    clc
    adc score,x
    sta score,x
@norm:
    lda score,x
    cmp #10
    bcc @hi
    sbc #10
    sta score,x
    dex
    bmi @hi
    inc score,x
    jmp @norm
@hi:
    ; hi score?
    ldx #0
@cmp:
    lda hisc,x
    cmp score,x
    bcc @copy
    bne @rts
    inx
    cpx #7
    bne @cmp
    rts
@copy:
    ldx #0
@cl:
    lda score,x
    sta hisc,x
    inx
    cpx #7
    bne @cl
@rts:
    rts

; ======================================================================
; world drawing
; ======================================================================
draw_world:
    ; player bullets
    ldx #NUM_PBULLETS-1
@pbl:
    lda pb_act,x
    beq @pbn
    lda pb_x,x
    sta sx
    lda pb_y,x
    sta sy
    lda #<ms_pbullet
    sta ms_ptr
    lda #>ms_pbullet
    sta ms_ptr+1
    stx t7
    jsr draw_ms
    ldx t7
@pbn:
    dex
    bpl @pbl
    ; enemies (alternate order to spread flicker)
    lda nmis
    and #1
    bne @rev
    ldx #0
@efw:
    stx t7
    jsr draw_enemy
    ldx t7
    inx
    cpx #NUM_ENEMIES
    bne @efw
    jmp @eb
@rev:
    ldx #NUM_ENEMIES-1
@erv:
    stx t7
    jsr draw_enemy
    ldx t7
    dex
    bpl @erv
@eb:
    ; enemy bullets
    ldx #NUM_EBULLETS-1
@ebl:
    lda eb_act,x
    beq @ebn
    lda eb_x,x
    sta sx
    lda eb_y,x
    sta sy
    lda eb_kind,x
    bne @meteor
    lda nmis
    lsr
    lsr
    and #1
    beq @b0
    lda #<ms_ebullet1
    sta ms_ptr
    lda #>ms_ebullet1
    sta ms_ptr+1
    jmp @bd
@b0:
    lda #<ms_ebullet0
    sta ms_ptr
    lda #>ms_ebullet0
    sta ms_ptr+1
    jmp @bd
@meteor:
    lda nmis
    lsr
    lsr
    and #1
    beq @m0
    lda #<ms_meteor1
    sta ms_ptr
    lda #>ms_meteor1
    sta ms_ptr+1
    jmp @bd
@m0:
    lda #<ms_meteor0
    sta ms_ptr
    lda #>ms_meteor0
    sta ms_ptr+1
@bd:
    stx t7
    jsr draw_ms
    ldx t7
@ebn:
    dex
    bpl @ebl
    ; boss
    lda b_act
    beq @expl
    lda bflash
    beq @bdraw
    lda nmis
    and #1
    bne @expl
@bdraw:
    lda bx
    sta sx
    lda by
    sta sy
    ldx stage
    dex
    lda boss_ms_l,x
    sta ms_ptr
    lda boss_ms_h,x
    sta ms_ptr+1
    jsr draw_ms
@expl:
    ldx #NUM_EXPL-1
@exl:
    lda ex_act,x
    beq @exn
    lda ex_x,x
    sta sx
    lda ex_y,x
    sta sy
    lda ex_t,x
    lsr
    lsr
    tay
    lda ms_expl_l,y
    sta ms_ptr
    lda ms_expl_h,y
    sta ms_ptr+1
    stx t7
    jsr draw_ms
    ldx t7
@exn:
    dex
    bpl @exl
    rts

; X = enemy index
draw_enemy:
    lda e_act,x
    bne :+
    rts
:   sec
    sbc #1
    asl                 ; type*2
    sta t6
    lda nmis
    lsr
    lsr
    lsr
    and #1
    clc
    adc t6
    tay
    lda ms_enemy_l,y
    sta ms_ptr
    lda ms_enemy_h,y
    sta ms_ptr+1
    lda e_x,x
    sta sx
    lda e_y,x
    sta sy
    jmp draw_ms

; ======================================================================
; sound driver (runs in NMI) - identical to the MMC3 edition, mapper-agnostic
; ======================================================================
; X = song (0 title, 1 stage, 2 tense)
music_play:
    lda song_tbl_sq1l,x
    sta s_strl+0
    sta s_ptrl+0
    lda song_tbl_sq1h,x
    sta s_strh+0
    sta s_ptrh+0
    lda song_tbl_sq2l,x
    sta s_strl+1
    sta s_ptrl+1
    lda song_tbl_sq2h,x
    sta s_strh+1
    sta s_ptrh+1
    lda song_tbl_tril,x
    sta s_strl+2
    sta s_ptrl+2
    lda song_tbl_trih,x
    sta s_strh+2
    sta s_ptrh+2
    lda song_tbl_noil,x
    sta s_strl+3
    sta s_ptrl+3
    lda song_tbl_noih,x
    sta s_strh+3
    sta s_ptrh+3
    lda #1
    sta s_dur+0
    sta s_dur+1
    sta s_dur+2
    sta s_dur+3
    sta music_on
    rts

music_stop:
    lda #0
    sta music_on
    lda #$30
    sta $4000
    sta $4004
    sta $400C
    lda #$80
    sta $4008
    rts

; A = sfx id: 0 shot, 1 explosion, 2 hit
sfx_play:
    cmp #1
    beq @expl
    cmp #2
    beq @hit
    ; shot: falling pitch on sq2
    lda #8
    sta sfx_sq2
    lda #0
    sta sfx_kind
    lda #$79
    sta $4004
    lda #$50
    sta sfx_p
    sta $4006
    lda #$00
    sta $4007
    rts
@expl:
    lda #28
    sta sfx_noi
    lda #$26
    sta $400C
    lda #$0E
    sta $400E
    lda #$08
    sta $400F
    rts
@hit:
    lda #4
    sta sfx_sq2
    lda #1
    sta sfx_kind
    lda #$3C
    sta $4004
    lda #$20
    sta $4006
    lda #$00
    sta $4007
    rts

sound_update:
    ; sfx upkeep
    lda sfx_sq2
    beq @nosq
    lda sfx_kind
    bne :+
    lda sfx_p
    clc
    adc #$14
    sta sfx_p
    sta $4006
:   dec sfx_sq2
    bne @nosq
    lda #$30
    sta $4004
@nosq:
    lda sfx_noi
    beq @nonoi
    dec sfx_noi
    bne @nonoi
    lda #$30
    sta $400C
@nonoi:
    lda music_on
    bne :+
    rts
:   ; sq1
    ldx #0
    jsr fetch_ch
    lda nt0
    cmp #$80
    beq @c1
    cmp #$60
    beq @r0
    tay
    lda #$B8
    sta $4000
    lda note_period_lo,y
    sta $4002
    lda note_period_hi,y
    sta $4003
    jmp @c1
@r0:
    lda #$30
    sta $4000
@c1:
    ldx #1
    jsr fetch_ch
    lda sfx_sq2
    bne @c2
    lda nt0
    cmp #$80
    beq @c2
    cmp #$60
    beq @r1
    tay
    lda #$76
    sta $4004
    lda note_period_lo,y
    sta $4006
    lda note_period_hi,y
    sta $4007
    jmp @c2
@r1:
    lda #$30
    sta $4004
@c2:
    ldx #2
    jsr fetch_ch
    lda nt0
    cmp #$80
    beq @c3
    cmp #$60
    beq @r2
    tay
    lda #$FF
    sta $4008
    lda note_period_lo,y
    sta $400A
    lda note_period_hi,y
    sta $400B
    jmp @c3
@r2:
    lda #$80
    sta $4008
@c3:
    ldx #3
    jsr fetch_ch
    lda sfx_noi
    bne @c4
    lda nt0
    cmp #$80
    beq @c4
    cmp #$60
    beq @r3
    tay
    lda drum_env,y
    sta $400C
    lda drum_per,y
    sta $400E
    lda #$08
    sta $400F
    jmp @c4
@r3:
    lda #$30
    sta $400C
@c4:
    rts

; X = channel; result in nt0 ($80 = no event)
fetch_ch:
    lda #$80
    sta nt0
    dec s_dur,x
    bne @rts
    lda s_ptrl,x
    sta np0
    lda s_ptrh,x
    sta np1
    ldy #0
    lda (np0),y
    cmp #$FF
    bne :+
    lda s_strl,x
    sta np0
    sta s_ptrl,x
    lda s_strh,x
    sta np1
    sta s_ptrh,x
    lda (np0),y
:   sta nt0
    iny
    lda (np0),y
    sta s_dur,x
    lda s_ptrl,x
    clc
    adc #2
    sta s_ptrl,x
    bcc @rts
    inc s_ptrh,x
@rts:
    rts

; ---------------------------------------------------------------- vectors
.segment "VECTORS"
.addr nmi, reset, irq

.segment "CHARS"
.incbin "nrom_chrrom.bin"
