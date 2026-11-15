/* IS31FL3733B 12 x 16 matrix LED driver (datasheet Rev. E, 2024), ADDR1 = ADDR2 = GND: 0x50.
 * Rows of the face are CS lines (anodes), columns are SW lines (cathodes). */
#ifndef IS31FL3733_H
#define IS31FL3733_H
#include "i2c_bus.h"

#define IS31_ADDR 0x50
#define IS31_GCC_DEFAULT 96          /* I_OUT = 840 / 20k * 96 / 256 = 15.8 mA peak per LED */

typedef struct {
    const i2c_bus_t *bus;
} is31_t;

int is31_init(is31_t *d, const i2c_bus_t *bus, uint8_t gcc);
int is31_show(is31_t *d, const uint8_t *level);      /* 121 levels, row-major */
/* PWM register (0..191) of each pixel, from the board's netlist: (SW - 1) * 16 + (CS - 1) */
extern const uint8_t PIXEL_REG[121];
#endif
