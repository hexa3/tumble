/* MAX17048 1-cell fuel gauge (I2C 0x36), on the base board.  Registers are 16-bit big-endian:
 * VCELL 0x02 (78.125 uV/LSB), SOC 0x04 (1/256 %), CRATE 0x16 (0.208 %/h per LSB, signed). */
#ifndef MAX17048_H
#define MAX17048_H
#include "i2c_bus.h"

#define GAUGE_ADDR 0x36

typedef struct {
    uint16_t mv;          /* cell voltage */
    uint8_t soc;          /* state of charge, % (clamped to 100) */
    int16_t crate_x10;    /* charge rate, 0.1 %/h; positive while charging */
} gauge_t;

int gauge_read(const i2c_bus_t *bus, gauge_t *g);
#endif
