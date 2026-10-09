/* SPDX-License-Identifier: Apache-2.0
 * Actual generated CPU + real USB PCM detector, not a copied joypad model. */
#include "bridge.h"
#include FM1_CPU_CORE_FILE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static fm1_uac_bridge usb;
unsigned fm1_usb_audio_mic_bits(void){return usb.mic_active?4u:0u;}
int main(void) {
    static nes_t n;uint8_t packet[192];int32_t pcm[2]={0};unsigned i,bit;
    fm1_uac_stream(&usb,0,1);
    /* Opposite-phase stereo above threshold; no application audio involved. */
    for(i=0;i<48;i++){packet[4*i]=0;packet[4*i+1]=8;packet[4*i+2]=0;packet[4*i+3]=0xf8;}
    for(i=0;i<8;i++)CHECK(!fm1_uac_receive(&usb,packet,192));
    fm1_uac_microphone(&usb,1);fm1_uac_dac(&usb,pcm,1);CHECK(usb.mic_active);
    n.nes_cpu.joypad.joypad=0xa55a;
    nes_write_joypad(&n,1);
    for(i=0;i<20;i++) {CHECK(nes_read_cpu(&n,0x4016)==5);CHECK(nes_read_cpu(&n,0x4017)==0);}
    nes_write_joypad(&n,1);nes_write_joypad(&n,0);
    for(i=0;i<16;i++) {
        bit=(0xa55au>>(15-(i&7)))&1;
        CHECK(nes_read_cpu(&n,0x4016)==(bit|4));
        CHECK(nes_read_cpu(&n,0x4017)==((0x5au>>(7-(i&7)))&1));
    }
    /* Disabling changes the immediate bit without resetting pad offsets. */
    i=n.nes_cpu.joypad.offset1;fm1_uac_microphone(&usb,0);
    CHECK(nes_read_cpu(&n,0x4016)==((0xa5u>>(7-(i&7)))&1));
    CHECK(n.nes_cpu.joypad.offset1==i+1);
    CHECK(!fm1_usb_audio_mic_bits());
    puts("PASS USB PCM to $4016 D2, never $4017; immediate strobe and unchanged serial pads");return 0;
}
