"""Offline WL82 diagnostic/application link; optional UAC, no packaging or flashing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NES=HERE.parent/'nes'
sys.path.insert(0,str(NES))
from build_env import SDK,SDK_PIN,CORE,TC,MAKE,make_list,sdk_path
from audit_boot import audit
import vendor_overlay
from embed_rom50 import generate,rom_path,ROMS,select_rom

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--controller',type=int,choices=(0,),required=True,
                   help='Only USB0 has a reviewed link contract; connector routing is still unverified')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--peripheral-tests',action='store_true')
    p.add_argument('--usb-audio',action='store_true',help='MDX-derived UAC1 duplex with CDC; requires NES audio priority')
    p.add_argument('--nes-player','--nes-smb1',dest='nes_smb1',action='store_true',help='Autostart a caller-supplied iNES ROM; legacy profile name retained internally')
    p.add_argument('--rom',type=Path,help='Local ROM to embed; never downloaded')
    p.add_argument('--rom-sha256',help='Required expected SHA256 for --rom')
    p.add_argument('--nes-auto-skip',action='store_true',help='Opt-in bounded LCD-only automatic frame skipping; requires --nes-smb1')
    p.add_argument('--nes-audio-priority',action='store_true',help='DAC queue pacing, prefill and bounded LCD skipping; requires --nes-smb1')
    p.add_argument('--nes-live-fx',action='store_true',help='Live encoder VCF/LFO effects; requires --keyscan-irq and --nes-audio-priority')
    p.add_argument('--nes-channel-fx',action='store_true',help='Independent pulse1/pulse2/triangle/noise/master effects; requires --nes-live-fx')
    p.add_argument('--nes-render-skip',action='store_true',help='Skip hidden-frame pixels, retaining sprite-zero/CPU/APU; requires NES audio priority')
    p.add_argument('--nes-profile',action='store_true',help='Exclusive wall-time profiling; requires --nes-render-skip')
    p.add_argument('--nes-tiles',action='store_true',help='RAM bitplane lookup and eight-pixel tile rows; requires --nes-render-skip')
    p.add_argument('--nes-volume',action='store_true',help='PB6 ADC4 digital volume; requires paced scanner and audio priority')
    p.add_argument('--lcd-async',action='store_true',help='Double-buffered SPI1 IRQ display; requires --nes-render-skip')
    p.add_argument('--lcd-spi15',action='store_true',help='Bench test: idle SPI1 BAUD3 after stock init, requires async and 60MHz LSB')
    p.add_argument('--lcd-spi30',action='store_true',help='Bench test: idle SPI1 BAUD1 after stock init, requires async and 60MHz LSB')
    p.add_argument('--lcd-rgb444',action='store_true',help='Packed 12-bit LCD pixels after stock RGB565 startup; requires async')
    p.add_argument('--lcd-direct',action='store_true',help='Fuse native scaling and RGB444 packing directly into owned DMA frame; requires RGB444')
    p.add_argument('--keyscan-dma2',action='store_true',help='Opt-in stock-order two-byte SPI2 DMA with polled completion; requires --nes-smb1')
    p.add_argument('--keyscan-irq',action='store_true',help='NES-only interrupt DMA scanner; requires DMA2 and input recovery')
    p.add_argument('--keyscan-paced',action='store_true',help='One IRQ scan burst per 1ms; requires --keyscan-irq')
    p.add_argument('--nes-no-keys',action='store_true',help='NES isolation: skip physical scanner and supply neutral input; requires --nes-smb1')
    p.add_argument('--nes-input-recovery',action='store_true',help='Contain NES scanner faults; three spaced retries, held-key continuity and bounded stale input')
    p.add_argument('--lcd-stock-fill',action='store_true',help='Replay the stock initial-fill window and continuous white stream')
    p.add_argument('--lcd-stock-dma',action='store_true',help='Stock setup-before-delay, DMA parameters, fixed register snapshots; requires --lcd-stock-fill')
    p.add_argument('--lcd-stock-sequence',action='store_true',help='Stock PA2/GPIO setup, scheduler delays and 40-byte DMA black first fill; requires --lcd-stock-dma')
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    if a.usb_audio and not (a.nes_audio_priority and a.nes_volume):p.error('--usb-audio requires --nes-audio-priority and --nes-volume')
    if a.nes_smb1 and (not a.rom or not a.rom_sha256):p.error('NES player requires --rom and --rom-sha256')
    if a.rom and not a.nes_smb1:p.error('--rom requires --nes-player')
    if a.nes_smb1:select_rom(a.rom,a.rom_sha256)
    if a.lcd_stock_fill and not a.peripheral_tests:p.error('--lcd-stock-fill requires --peripheral-tests')
    if a.lcd_stock_dma and not a.lcd_stock_fill:p.error('--lcd-stock-dma requires --lcd-stock-fill')
    if a.lcd_stock_sequence and not a.lcd_stock_dma:p.error('--lcd-stock-sequence requires --lcd-stock-dma')
    if a.nes_smb1 and not a.lcd_stock_sequence:p.error('--nes-smb1 requires --lcd-stock-sequence')
    if a.nes_auto_skip and not a.nes_smb1:p.error('--nes-auto-skip requires --nes-smb1')
    if a.nes_audio_priority and not a.nes_smb1:p.error('--nes-audio-priority requires --nes-smb1')
    if a.nes_live_fx and (not a.keyscan_irq or not a.nes_audio_priority):p.error('--nes-live-fx requires --keyscan-irq and --nes-audio-priority')
    if a.nes_channel_fx and not a.nes_live_fx:p.error('--nes-channel-fx requires --nes-live-fx')
    if a.nes_render_skip and not a.nes_audio_priority:p.error('--nes-render-skip requires --nes-audio-priority')
    if a.nes_profile and not a.nes_render_skip:p.error('--nes-profile requires --nes-render-skip')
    if a.nes_tiles and not a.nes_render_skip:p.error('--nes-tiles requires --nes-render-skip')
    if a.nes_volume and not (a.keyscan_paced and a.nes_audio_priority):p.error('--nes-volume requires paced scanner and audio priority')
    if a.lcd_async and not a.nes_render_skip:p.error('--lcd-async requires --nes-render-skip')
    if a.lcd_spi15 and not a.lcd_async:p.error('--lcd-spi15 requires --lcd-async')
    if a.lcd_spi30 and not a.lcd_async:p.error('--lcd-spi30 requires --lcd-async')
    if a.lcd_spi30 and a.lcd_spi15:p.error('Select only one LCD SPI clock experiment')
    if a.lcd_rgb444 and not a.lcd_async:p.error('--lcd-rgb444 requires --lcd-async')
    if a.lcd_direct and not a.lcd_rgb444:p.error('--lcd-direct requires --lcd-rgb444')
    if a.keyscan_dma2 and not a.nes_smb1:p.error('--keyscan-dma2 requires --nes-smb1')
    if a.keyscan_irq and (not a.keyscan_dma2 or not a.nes_input_recovery):p.error('--keyscan-irq requires --keyscan-dma2 and --nes-input-recovery')
    if a.keyscan_paced and not a.keyscan_irq:p.error('--keyscan-paced requires --keyscan-irq')
    if a.nes_no_keys and not a.nes_smb1:p.error('--nes-no-keys requires --nes-smb1')
    if a.nes_input_recovery and (not a.nes_smb1 or a.nes_no_keys):p.error('--nes-input-recovery requires --nes-smb1 and physical keys')
    manifest=out/'build-manifest.json'
    manifest.write_text(json.dumps({'status':'BUILDING_OR_FAILED','flashable':False})+'\n')
    log=(out/'build.log').open('w',encoding='utf-8')
    def run(args):
        result=subprocess.run(list(map(str,args)),cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        log.write(' '.join(map(str,args))+'\n'+result.stdout);log.flush()
        if result.returncode:
            print(result.stdout[-9000:]);raise RuntimeError('Build failed; see '+str(out/'build.log'))
        return result.stdout
    if run(['git','-C',SDK,'rev-parse','HEAD']).strip()!=SDK_PIN:raise ValueError('SDK pin changed')
    if run(['git','-C',SDK,'status','--porcelain']).strip():raise ValueError('SDK is dirty')
    # No stock dump is shipped or required. Compiled power-init parameters,
    # instruction hash and relocations remain audited below.
    power={'source':'reviewed board power implementation',
           'stock_dump_rechecked':False,'compiled_power_audit_required':True}
    text=MAKE.read_text(encoding='utf-8');flags=make_list(text,'CFLAGS')
    defines=make_list(text,'DEFINES')+['-DFM1_USB_CONTROLLER='+str(a.controller)]
    if a.usb_audio:defines+=['-DFM1_USB_AUDIO=1']
    if a.peripheral_tests:defines+=['-DFM1_PERIPHERAL_TESTS=1']
    if a.lcd_stock_fill:defines+=['-DFM1_LCD_STOCK_FILL=1']
    if a.lcd_stock_dma:defines+=['-DFM1_LCD_STOCK_DMA=1']
    if a.lcd_stock_sequence:defines+=['-DFM1_LCD_STOCK_SEQUENCE=1']
    if a.nes_smb1:defines+=['-DFM1_NES_PLAYER=1','-DFM1_TARGET_PI32V2=1']
    if a.nes_auto_skip:defines+=['-DFM1_NES_AUTO_SKIP=1']
    if a.nes_audio_priority:defines+=['-DFM1_NES_AUDIO_PRIORITY=1']
    if a.nes_live_fx:defines+=['-DFM1_NES_LIVE_FX=1']
    if a.nes_channel_fx:defines+=['-DFM1_NES_CHANNEL_FX=1']
    if a.nes_profile:defines+=['-DFM1_NES_PROFILE=1']
    if a.nes_volume:defines+=['-DFM1_NES_VOLUME=1']
    if a.lcd_async:defines+=['-DFM1_LCD_ASYNC=1']
    if a.lcd_spi15:defines+=['-DFM1_LCD_SPI15=1']
    if a.lcd_spi30:defines+=['-DFM1_LCD_SPI30=1']
    if a.lcd_rgb444:defines+=['-DFM1_LCD_RGB444=1']
    if a.lcd_direct:defines+=['-DFM1_LCD_DIRECT=1']
    if a.keyscan_dma2:defines+=['-DFM1_KEYSCAN_DMA2=1']
    if a.keyscan_irq:defines+=['-DFM1_KEYSCAN_IRQ=1']
    if a.keyscan_paced:defines+=['-DFM1_KEYSCAN_PACED=1']
    if a.nes_no_keys:defines+=['-DFM1_NES_NO_KEYS=1']
    if a.nes_input_recovery:defines+=['-DFM1_NES_INPUT_RECOVERY=1']
    includes=['-I'+str(x) for x in (HERE,NES/'boot',NES/'include',SDK/'apps/common',SDK/'apps/common/usb',SDK/'apps/common/usb/device')]
    includes+=['-I'+str(sdk_path(x[2:])) for x in make_list(text,'INCLUDES')]
    if a.usb_audio:includes+=['-I'+str(HERE.parent/'usb-audio')]
    sources=[sdk_path(x) for name in ('c_SRC_FILES','S_SRC_FILES') for x in make_list(text,name)]
    sources=[s for s in sources if s.name not in ('app_main.c','board.c','cpp_run_init.c')]
    sources += [NES/'boot'/n for n in ('board.c','boot_compat.c','boot_trace.c','board_power.c')]
    sources += [HERE/n for n in ('app_main.c','protocol.c','descriptors.c','usb_policy.c','dma.c','rx_channel.c','boot_entry.c','packet.c')]
    if a.peripheral_tests:
        sources += [HERE/n for n in ('peripherals.c','peripheral_logic.c')]
        sources += [NES/'boot/display_test.c',NES/'src/fm1_wl82_keyscan.c',NES/'src/fm1_stock_keys.c']
    speed_sources=set()
    if a.usb_audio:
        audio_sources=[HERE.parent/'usb-audio'/n for n in ('bridge.c','profile.c','target.c')]
        sources+=audio_sources;speed_sources.update(audio_sources)
    if a.nes_smb1:
        core=CORE
        if run(['git','-C',core,'rev-parse','HEAD']).strip()!='68bdfc8de570264c0e84f73766f1a1ed3591066f':raise ValueError('NES core pin changed')
        if run(['git','-C',core,'status','--porcelain']).strip():raise ValueError('NES core is dirty')
        includes=['-I'+str(NES/'port'),'-I'+str(core/'inc')]+includes
        generated=out/'generated/fm1_rom50.c';generate(rom_path('smb1'),generated,'smb1')
        sources += [NES/'src'/n for n in ('fm1_nes.c','fm1_nes_target.c','fm1_board.c','fm1_audio_queue.c')]
        sources += [core/'src'/n for n in ('nes.c','nes_cpu.c','nes_ppu.c','nes_apu.c')]+[generated]
        # Optimize emulation/conversion for speed, retaining SDK/boot flags.
        speed_sources.update(NES/'src'/n for n in ('fm1_nes.c','fm1_board.c','fm1_audio_queue.c'))
        speed_sources.update(core/'src'/n for n in ('nes.c','nes_cpu.c','nes_ppu.c','nes_apu.c'))
        if a.nes_volume:
            sources += [NES/'src/fm1_volume.c']
            speed_sources.add(NES/'src/fm1_volume.c')
        if a.lcd_direct:
            sources += [NES/'src/fm1_lcd_pack.c']
            speed_sources.add(NES/'src/fm1_lcd_pack.c')
        if a.nes_profile:
            sources += [NES/'src/fm1_profile.c']
            speed_sources.add(NES/'src/fm1_profile.c')
        if a.nes_live_fx:
            sources += [NES/'src/fm1_nes_fx.c']
            speed_sources.add(NES/'src/fm1_nes_fx.c')
        if a.nes_channel_fx:
            sources += [NES/'src/fm1_channel_fx.c']
            speed_sources.add(NES/'src/fm1_channel_fx.c')
    sources.append(SDK/'apps/common/usb/usb_config.c')
    overlays={}
    if a.nes_smb1:
        original=core/'src/nes_cpu.c';target=out/'fm1-nes_cpu.c'
        target.write_text(vendor_overlay.nes_microphone(original.read_text(encoding='utf-8')),encoding='utf-8')
        sources[sources.index(original)]=target
        speed_sources.remove(original);speed_sources.add(target)
        overlays[str(original)]=hashlib.sha256(original.read_bytes()).hexdigest()
    if a.nes_render_skip:
        original=core/'src/nes.c';target=out/'fm1-nes.c'
        transformed=vendor_overlay.nes_render_skip(original.read_text(encoding='utf-8'))
        if a.nes_tiles:transformed=vendor_overlay.nes_tiles(transformed)
        if a.nes_profile:transformed=vendor_overlay.nes_profile(transformed)
        target.write_text(transformed,encoding='utf-8')
        sources[sources.index(original)]=target
        speed_sources.remove(original);speed_sources.add(target)
        overlays[str(original)]=hashlib.sha256(original.read_bytes()).hexdigest()
    if a.nes_channel_fx:
        original=core/'src/nes_apu.c';target=out/'fm1-nes_apu.c'
        target.write_text(vendor_overlay.nes_apu(original.read_text(encoding='utf-8')),encoding='utf-8')
        sources[sources.index(original)]=target
        speed_sources.remove(original);speed_sources.add(target)
        overlays[str(original)]=hashlib.sha256(original.read_bytes()).hexdigest()
    for name,transform in (('cdc.c',vendor_overlay.cdc),('usb_device.c',vendor_overlay.device),('msd_upgrade.c',vendor_overlay.boot_entry)):
        original=SDK/'apps/common/usb/device'/name
        target=out/('fm1-'+name);target.write_text(transform(original.read_text(encoding='utf-8')),encoding='utf-8')
        sources.append(target);overlays[str(original)]=hashlib.sha256(original.read_bytes()).hexdigest()
    for source,name in ((SDK/'cpu/wl82/sdk_ld.c','sdk.ld'),(SDK/'cpu/wl82/sdk_used_list.c','sdk.used')):
        run([TC/'clang.exe',*flags,*defines,*includes,'-D__LD__','-E','-P',source,'-o',out/name])
    used=out/'sdk.used';used.write_text(used.read_text()+'\nmemory_init\nfm1_usb_task\ncdc_read_data\ncdc_write_data\nfm1_cdc_ready\nfm1_diag_feed\nfm1_usb_device_descriptor\nfm1_usb_config_descriptor\n')
    used.write_text(used.read_text()+'fm1_usb_rx_irq\ngo_mask_usb_updata\nnvram_set_boot_state\n')
    if a.nes_smb1:used.write_text(used.read_text()+'fm1_board_run\nfm1_display_write\nfm1_audio_startup_process24\nfm1_nes_run\n')
    if a.usb_audio:used.write_text(used.read_text()+'fm1_usb_audio_dac\nfm1_usb_audio_stop\nfm1_uac_desc_config\nfm1_uac_descriptor\nfm1_usb_audio_mic_bits\n')
    ld=(out/'sdk.ld').read_text()
    for old,new in (('*(.data)','*(.data .data.*)'),('*(.bss)','*(.bss .bss.*)')):
        ld=vendor_overlay.once(ld,old,new)
    for section in ('.syscfg.2.ops','.syscfg.1.ops'):
        ld=vendor_overlay.once(ld,'*('+section+')','/* no persistent cfg repair */')
    ld+='\nSECTIONS { /DISCARD/ : { *(.syscfg.2.ops) *(.syscfg.1.ops) } }\n'
    (out/'sdk.ld').write_text(ld)
    objects=[]
    for i,source in enumerate(sources):
        obj=out/(str(i)+'-'+source.name+'.o');objects.append(obj)
        source_flags=flags
        if source in speed_sources:
            source_flags=[f for f in flags if f not in ('-O0','-O1','-O2','-O3','-Os','-Oz','-Ofast')]+['-O2']
        run([TC/'clang.exe',*source_flags,*defines,*includes,'-c',source,'-o',obj])
    libs=[SDK/'include_lib/newlib/pi32v2-lib'/n for n in ('libm.a','libc.a','libcompiler_rt.a')]
    libs += [SDK/'cpu/wl82/liba'/n for n in ('cpu.a','event.a','system.a','cfg_tool.a','fs.a','common_lib.a','update.a')]
    elf=out/'fm1-usb-diag.elf'
    run([TC/'pi32v2-lto-wrapper.exe','-o',elf,*objects,'--start-group',*libs,'--end-group',
         '-T'+str(out/'sdk.ld'),'-M='+str(out/'fm1-usb-diag.map'),'--wrap=boot_info_init','--wrap=memory_init',
         '--undefined=memory_init','--plugin-opt=mcpu=r3','--plugin-opt=-mattr=+fprev1',
         '--plugin-opt=-pi32v2-large-program=true','--plugin-opt=-used-symbol-file='+str(used)])
    parts=[]
    for section in ('.text','.data','.dynamic_data','.ram0_data','.cache_ram_data'):
        file=out/(section[1:]+'.bin');run([TC/'llvm-objcopy.exe','-O','binary','-j',section,elf,file]);parts.append(file.read_bytes())
    app=out/'fm1-usb-diag.app.bin';app.write_bytes(b''.join(parts))
    (out/'symbols.txt').write_text(run([TC/'llvm-nm.exe','-n','-S',elf]))
    (out/'disassembly.asm').write_text(run([TC/'llvm-objdump.exe','-d','-mcpu=r3',elf]))
    report=audit(elf.read_bytes(),app.read_bytes(),usb_only=True,usb_peripheral_tests=a.peripheral_tests,usb_nes=a.nes_smb1,usb_audio=a.usb_audio,rom='smb1' if a.nes_smb1 else 'rom50',require_boot_trace=True,require_board_power=True)
    (out/'static-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    result={'status':'LINKED_USB_DIAGNOSTIC_UNTESTED','flashable':False,'usb_controller_candidate':a.controller,
            'controller_routing_verified':False,'sdk_commit':SDK_PIN,'application_bytes':app.stat().st_size,
            'application_sha256':hashlib.sha256(app.read_bytes()).hexdigest(),
            'update_transport':'CDC UBOOT entry; external app-only jltool wrapper; CDC payload verify-only',
            'flash_commit':'external explicit approval only','usb_audio':a.usb_audio,
            'device_operations_performed':False,'static_audit':report,'power_evidence':power,
            'peripheral_tests':a.peripheral_tests,'serial_uboot':'implemented; transition not hardware-qualified',
            'nes_smb1':a.nes_smb1,'cartridge_sha256':ROMS['smb1'][2] if a.nes_smb1 else None,
            'nes_auto_skip':a.nes_auto_skip,
            'nes_audio_priority':a.nes_audio_priority,
            'nes_live_fx':a.nes_live_fx,
            'nes_channel_fx':a.nes_channel_fx,
            'nes_render_skip':a.nes_render_skip,
            'nes_profile':a.nes_profile,
            'nes_tiles':a.nes_tiles,
            'nes_volume':a.nes_volume,
            'lcd_async':a.lcd_async,
            'lcd_spi15':a.lcd_spi15,
            'lcd_spi30':a.lcd_spi30,
            'lcd_rgb444':a.lcd_rgb444,
            'lcd_direct':a.lcd_direct,
            'keyscan_dma2':a.keyscan_dma2,
            'keyscan_irq':a.keyscan_irq,
            'keyscan_paced':a.keyscan_paced,
            'nes_no_keys':a.nes_no_keys,
            'nes_input_recovery':a.nes_input_recovery,
            'speed_optimization':{'level':'-O2','sources':sorted(str(s) for s in speed_sources)},
            'encoder_scanner':'250us semaphore-wakeup, stock stable-two filter; hardware retest pending',
            'lcd_test':'stock-pa2-gpio-dma40-sequence' if a.lcd_stock_sequence else ('stock-dma-params-registers' if a.lcd_stock_dma else ('stock-window-continuous-white' if a.lcd_stock_fill else 'row-addressed-rgb')),
            'vendor_overlay_sources':overlays,
            'source_sha256':{str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources+list(HERE.glob('*.h'))+list(HERE.glob('*.py'))+
                [NES/n for n in ('audit_boot.py','audit_power.py','audit_pre_os.py','audit_usb_packet.py','build_env.py','embed_rom50.py')]+list((NES/'include').glob('*.h'))+list((NES/'boot').glob('*.h'))+(list((HERE.parent/'usb-audio').glob('*.h')) if a.usb_audio else [])},
            'archive_sha256':{str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in libs}}
    manifest.write_text(json.dumps(result,indent=2)+'\n');log.close()
    print(json.dumps({k:v for k,v in result.items() if k not in ('static_audit','source_sha256','archive_sha256','power_evidence','vendor_overlay_sources')},indent=2))

if __name__=='__main__':main()
