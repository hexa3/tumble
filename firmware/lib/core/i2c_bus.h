/* The only thing the chip drivers know about the hardware.  Return 0 on success. */
#ifndef I2C_BUS_H
#define I2C_BUS_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    int (*write)(void *ctx, uint8_t addr, const uint8_t *buf, size_t n);          /* buf[0] = register */
    int (*read)(void *ctx, uint8_t addr, uint8_t reg, uint8_t *buf, size_t n);
    void (*delay_ms)(void *ctx, uint32_t ms);
    void *ctx;
} i2c_bus_t;

static inline int i2c_reg8(const i2c_bus_t *b, uint8_t addr, uint8_t reg, uint8_t v)
{
    uint8_t buf[2] = {reg, v};
    return b->write(b->ctx, addr, buf, 2);
}
#endif
