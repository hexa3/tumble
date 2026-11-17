/* DRV2605L haptic driver (SLOS854D) for the Vybronics VG0832022D LRA (235 Hz, 1.8 Vrms), real-time
 * playback: the firmware writes an amplitude, waits, writes zero. */
#ifndef DRV2605L_H
#define DRV2605L_H
#include "i2c_bus.h"

#define DRV_ADDR 0x5A

/* RATED_VOLTAGE = Vrms * sqrt(1 - (4 * 300 us + 300 us) * 235 Hz) / 20.58 mV = 70  (SLOS854D eq. 5)
 * OD_CLAMP for 2.0 Vrms open-loop: 2.0 / (21.32 mV * sqrt(1 - 235 Hz * 800 us)) = 104   (eq. 7)
 * DRIVE_TIME: half the LRA period (2.13 ms) = 0.5 ms + 0.1 ms * 16                       */
#define DRV_RATED_VOLTAGE 70
#define DRV_OD_CLAMP 104          /* verify against the LRA's maximum drive voltage */
#define DRV_DRIVE_TIME 16

int drv_init(const i2c_bus_t *bus, int calibrate);     /* returns -2 if auto-calibration reports a fault */
int drv_rtp(const i2c_bus_t *bus, uint8_t amplitude);  /* 0 = stop, 127 = full (signed RTP format) */
int drv_standby(const i2c_bus_t *bus, int standby);
#endif
