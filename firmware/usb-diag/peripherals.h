#ifndef FM1_PERIPHERALS_H
#define FM1_PERIPHERALS_H
/* Protocol IDs: 1 STOP, 2 LCD, 3 AUDIO, 4 KEYS, 5 KNOBS, 6 STATUS. */
int fm1_peripheral_start_task(void);
int fm1_peripheral_request(unsigned command,unsigned generation);
void fm1_peripheral_cancel(void);
void fm1_peripheral_session_cancel(void);
int fm1_peripheral_idle(void);
int fm1_peripheral_event(char *out,unsigned size);
#ifdef FM1_USB_AUDIO
/* CPU0 control task only, after worker is idle; stops the persistent DAC. */
void fm1_peripheral_usb_audio_stop(void);
/* Confirmation IRQ only: mask the DAC vector, no SDK close/task calls. */
void fm1_peripheral_usb_audio_quiesce(void);
#endif
#endif
