#include "peripheral_logic.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);exit(1);}} while(0)
static void contact(uint8_t rows[11],unsigned index,unsigned value) {
    unsigned a=fm1_encoder_contacts[2*index],b=fm1_encoder_contacts[2*index+1];
    rows[a>>4]=(rows[a>>4]|(1u<<(a&15)))&~((value&1)<<(a&15));
    rows[b>>4]=(rows[b>>4]|(1u<<(b&15)))&~(((value>>1)&1)<<(b&15));
}
static void stable(fm1_encoders *s,uint8_t rows[11],unsigned i,unsigned value) {
    contact(rows,i,value);fm1_encoders_sample(s,rows);fm1_encoders_sample(s,rows);
}
int main(void) {
    fm1_encoders s={0};uint8_t rows[11];unsigned i,j;int32_t peak=0;int64_t sum=0;
    memset(rows,0x3f,sizeof(rows));fm1_encoders_sample(&s,rows);
    for(i=0;i<7;i++) {
        const unsigned forward[]={2,3,1,0},reverse[]={1,3,2,0};
        for(j=0;j<4;j++)stable(&s,rows,i,forward[j]);
        CHECK(s.count[i]==4 && !s.invalid[i]);
        for(j=0;j<4;j++)stable(&s,rows,i,reverse[j]);
        CHECK(!s.count[i]);
        stable(&s,rows,i,3);CHECK(s.invalid[i]==1 && !s.count[i]);
        fm1_encoders_sample(&s,rows);CHECK(s.invalid[i]==1);
        stable(&s,rows,i,0);
    }
    CHECK(!strcmp(fm1_encoder_names[0],"SELECT") && !strcmp(fm1_encoder_names[6],"PRESETS"));
    CHECK(!strcmp(fm1_encoder_names[1],"ALGORITHM") && !strcmp(fm1_encoder_names[5],"KNOB4"));
    /* One-scan glitches never advance the accepted state or hide a stable
       illegal two-bit transition. Qualify all four starting phases. */
    for(i=0;i<7;i++)for(j=0;j<4;j++) {
        unsigned k;fm1_encoders t={0};
        memset(rows,0x3f,sizeof(rows));contact(rows,i,j);fm1_encoders_sample(&t,rows);
        for(k=0;k<4;k++) {
            contact(rows,i,k);fm1_encoders_sample(&t,rows);
            contact(rows,i,j);fm1_encoders_sample(&t,rows);fm1_encoders_sample(&t,rows);
            CHECK(t.previous[i]==j && !t.count[i] && !t.invalid[i]);
        }
        stable(&t,rows,i,j^3);CHECK(t.invalid[i]==1 && t.count[i]==0);
    }
    /* Twenty detents each way, every AB phase held for two scans; equal travel
       returns to zero. A 10 ms sampler of 2 ms phases instead misses states. */
    {
        fm1_encoders fast={0},slow={0};unsigned tick;
        const unsigned phases[]={0,2,3,1};
        memset(rows,0x3f,sizeof(rows));fm1_encoders_sample(&fast,rows);fm1_encoders_sample(&slow,rows);
        for(tick=1;tick<=640;tick++) {
            contact(rows,0,phases[(tick/8)%4]);
            fm1_encoders_sample(&fast,rows);
            if(tick%40==0)fm1_encoders_sample(&slow,rows);
        }
        fm1_encoders_sample(&fast,rows);
        CHECK(fast.count[0]==80 && fast.invalid[0]==0 && slow.count[0]!=80);
        for(tick=1;tick<=640;tick++) {
            contact(rows,0,phases[(4-(tick/8)%4)%4]);fm1_encoders_sample(&fast,rows);
        }
        fm1_encoders_sample(&fast,rows);CHECK(fast.count[0]==0 && !fast.invalid[0]);
        fast.count[0]=2147483647;stable(&fast,rows,0,2);CHECK(fast.count[0]==2147483647);
        fast.count[0]=(-2147483647-1);stable(&fast,rows,0,0);CHECK(fast.count[0]==(-2147483647-1));
    }
    for(i=0;i<FM1_TONE_FRAMES+1000;i++) {
        int32_t sample=fm1_test_sample(i);
        CHECK(sample>=-65536 && sample<=65536);
        if(i<44100 || i>=FM1_TONE_FRAMES)CHECK(sample==0);
        if(abs(sample)>peak)peak=abs(sample);
        sum+=sample;
    }
    CHECK(peak==65536 && fm1_test_sample(44100)==0 && fm1_test_sample(FM1_TONE_FRAMES-1)==0);
    CHECK(fm1_test_sample(0xffffffffu)==0);
    /* Envelope boundaries need not contain an integral number of periods.
     * Mean DC stays below two low-24-bit sample units over the tone. */
    CHECK(sum>-(int64_t)88200*2 && sum<(int64_t)88200*2);
    puts("PASS seven encoder mappings, stock stable-two filter, glitches, illegal transitions, fast/slow sampling, count saturation, bounded tone");return 0;
}
