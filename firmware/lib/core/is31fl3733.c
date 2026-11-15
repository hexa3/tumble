#include "is31fl3733.h"
#include <string.h>

#define REG_PAGE 0xFD
#define REG_UNLOCK 0xFE
#define UNLOCK_KEY 0xC5
#define PG_ONOFF 0
#define PG_PWM 1
#define PG_ABM 2
#define PG_FUNC 3
#define F_CONFIG 0x00               /* SSD = bit 0 (1 = normal), PFS bits 5:3 (000 = 8.4 kHz) */
#define F_GCC 0x01
#define F_SW_PULLUP 0x0F
#define F_CS_PULLDOWN 0x10

static int page(const is31_t *d, uint8_t p)
{
    /* the page register is locked after every write and must be unlocked each time */
    int e = i2c_reg8(d->bus, IS31_ADDR, REG_UNLOCK, UNLOCK_KEY);
    return e | i2c_reg8(d->bus, IS31_ADDR, REG_PAGE, p);
}

int is31_init(is31_t *d, const i2c_bus_t *bus, uint8_t gcc)
{
    d->bus = bus;
    int e = page(d, PG_FUNC);
    e |= i2c_reg8(bus, IS31_ADDR, F_CONFIG, 0x00);          /* shut down while configuring */
    e |= i2c_reg8(bus, IS31_ADDR, F_GCC, gcc);
    e |= i2c_reg8(bus, IS31_ADDR, F_SW_PULLUP, 0x01);       /* de-ghosting: 0.5k in tNOL (tune on hardware) */
    e |= i2c_reg8(bus, IS31_ADDR, F_CS_PULLDOWN, 0x01);
    uint8_t onoff[1 + 24];
    memset(onoff, 0, sizeof onoff);
    for (int k = 0; k < 121; k++) {                         /* only the LEDs that exist */
        uint8_t r = PIXEL_REG[k];
        onoff[1 + (r >> 4) * 2 + ((r & 15) >> 3)] |= (uint8_t)(1u << (r & 7));
    }
    e |= page(d, PG_ONOFF);
    e |= bus->write(bus->ctx, IS31_ADDR, onoff, sizeof onoff);
    uint8_t zero[1 + 192];
    memset(zero, 0, sizeof zero);
    e |= page(d, PG_ABM);                                   /* PWM mode for every dot */
    e |= bus->write(bus->ctx, IS31_ADDR, zero, sizeof zero);
    e |= page(d, PG_PWM);
    e |= bus->write(bus->ctx, IS31_ADDR, zero, sizeof zero);
    e |= page(d, PG_FUNC);
    e |= i2c_reg8(bus, IS31_ADDR, F_CONFIG, 0x01);          /* normal operation */
    return e;
}

int is31_show(is31_t *d, const uint8_t *level)
{
    uint8_t buf[1 + 192];
    memset(buf, 0, sizeof buf);
    for (int k = 0; k < 121; k++) buf[1 + PIXEL_REG[k]] = level[k];
    int e = page(d, PG_PWM);
    return e | d->bus->write(d->bus->ctx, IS31_ADDR, buf, sizeof buf);
}
