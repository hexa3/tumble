/* LIS3DH accelerometer over I2C (SA0 low: 0x18).  Awake: 200 Hz, +-4 g high resolution, double-click
 * on INT1.  Asleep: 10 Hz low-power, any-axis motion above ~160 mg on INT1 (latched) wakes the MCU.
 * Register map and the asleep settings are the ones the TinyDie Cube firmware used. */
#ifndef LIS3DH_H
#define LIS3DH_H
#include "i2c_bus.h"

#define ACC_ADDR 0x18
#define ACC_WHO_AM_I 0x33

int acc_init(const i2c_bus_t *bus);
int acc_read(const i2c_bus_t *bus, float g[3]);       /* specific force in g, board axes */
int acc_double_tap(const i2c_bus_t *bus);            /* 1 if a double click happened (reads CLICK_SRC) */
int acc_sleep_mode(const i2c_bus_t *bus, int sleep);
#endif
