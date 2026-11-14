/* LIS3DH accelerometer over I2C (SA0 low: 0x18): 200 Hz, +-4 g high resolution.
 * Register map is the one the TinyDie Cube firmware used. */
#ifndef LIS3DH_H
#define LIS3DH_H
#include "i2c_bus.h"

#define ACC_ADDR 0x18
#define ACC_WHO_AM_I 0x33

int acc_init(const i2c_bus_t *bus);
int acc_read(const i2c_bus_t *bus, float g[3]);       /* specific force in g, board axes */
#endif
