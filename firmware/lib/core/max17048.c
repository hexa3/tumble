#include "max17048.h"

static int rd16(const i2c_bus_t *b, uint8_t reg, uint16_t *v)
{
    uint8_t d[2];
    if (b->read(b->ctx, GAUGE_ADDR, reg, d, 2)) return -1;
    *v = (uint16_t)(d[0] << 8 | d[1]);
    return 0;
}

int gauge_read(const i2c_bus_t *b, gauge_t *g)
{
    uint16_t vc, soc, cr;
    if (rd16(b, 0x02, &vc) || rd16(b, 0x04, &soc) || rd16(b, 0x16, &cr)) return -1;
    g->mv = (uint16_t)((uint32_t)vc * 78125u / 1000000u);
    g->soc = (uint8_t)((soc >> 8) > 100 ? 100 : (soc >> 8));
    g->crate_x10 = (int16_t)((int32_t)(int16_t)cr * 208 / 100);
    return 0;
}
