/* Execute the actual peripheral DAC adapter, with existing hardware fakes. */
#define main legacy_lifecycle_main
#include "../usb-diag/tests/peripheral_runtime_tests.c"
#undef main
#include "bridge.h"
static fm1_uac_bridge usb_bridge;
void fm1_usb_audio_dac(int32_t *p,unsigned n){fm1_uac_dac(&usb_bridge,p,n);}
void fm1_usb_audio_status(char *p,size_t n){snprintf(p,n,"USB AUDIO fake\n");}
void fm1_usb_audio_transport_status(char *p,size_t n){snprintf(p,n,"USB TRANSPORT fake\n");}
int main(void) {
    int16_t source[64];int32_t pcm[128];uint8_t input[192],capture[192];unsigned i,j;
    reset(0);CHECK(!usb_audio_owner_start());CHECK(opens==1 && audio_enabled);
    fm1_uac_stream(&usb_bridge,0,1);fm1_uac_stream(&usb_bridge,1,1);
    for(i=0;i<48;i++){input[i*4]=0x70;input[i*4+1]=0x17;input[i*4+2]=0x90;input[i*4+3]=0xe8;}
    for(i=0;i<8;i++)fm1_uac_receive(&usb_bridge,input,192);
    /* Idle converter works without DTR and without NES. */
    ready=0;volume_sample=1023;nes_envelope.frames_left=0;
    for(i=0;i<180;i++)audio_output(0,(u8 *)pcm,512,3);
    CHECK(nes_volume.valid && nes_volume.target==127 && nes_envelope.gain_q7==127);
    for(i=0;i<8;i++)fm1_uac_receive(&usb_bridge,input,192);
    audio_output(0,(u8 *)pcm,512,3);CHECK(pcm[126]>0 && pcm[127]<0);
    fm1_uac_stream(&usb_bridge,1,1); /* Separate capture epoch from idle silence. */
    audio_nes=1;for(i=0;i<64;i++)source[i]=10000;
    for(i=0;i<FM1_AUDIO_PRIME/64+2;i++)CHECK(!fm1_audio_queue_push(&nes_queue,source,64));
    volume_sample=0;nes_volume.target=nes_volume.accepted=0;
    nes_envelope.target_q7=0;nes_envelope.gain_q7=0;
    for(j=0;j<10;j++) {
        CHECK(!fm1_audio_queue_push(&nes_queue,source,64));
        audio_output(0,(u8 *)pcm,512,3);
        for(i=0;i<128;i++)CHECK(!pcm[i]); /* muted DAC, not muted capture */
        CHECK(fm1_uac_transmit(&usb_bridge,capture,192)==192);
    }
    CHECK((int16_t)(capture[0]|capture[1]<<8)==10000);
    CHECK((int16_t)(capture[2]|capture[3]<<8)==10000); /* not PC return */
    audio_nes=0;audio_output(0,(u8 *)pcm,512,3);CHECK(audio_enabled && opens==1 && !closes);
    fm1_peripheral_usb_audio_stop();CHECK(!audio_enabled && closes==1 && irq_off==1);
    fm1_peripheral_usb_audio_stop();CHECK(closes==1); /* idempotent */
    CHECK(!usb_audio_owner_start());fm1_peripheral_usb_audio_quiesce();
    CHECK(!audio_enabled && closes==1); /* IRQ teardown doesn't close SDK */
    puts("PASS NES capture pre-volume/no-PC-loopback, persistent idle playback, single DAC owner and IRQ quiesce");return 0;
}
