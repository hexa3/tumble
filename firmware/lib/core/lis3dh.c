#include "lis3dh.h"

#define R_WHO_AM_I 0x0F
#define R_CTRL1 0x20
#define R_CTRL2 0x21
#define R_CTRL3 0x22
#define R_CTRL4 0x23
#define R_CTRL5 0x24
#define R_REFERENCE 0x26
#define R_OUT_X_L 0x28
#define R_INT1_CFG 0x30
#define R_INT1_SRC 0x31
#define R_INT1_THS 0x32
#define R_INT1_DUR 0x33
#define R_CLICK_CFG 0x38
#define R_CLICK_SRC 0x39
#define R_CLICK_THS 0x3A
#define R_TIME_LIMIT 0x3B
#define R_TIME_LATENCY 0x3C
#define R_TIME_WINDOW 0x3D
#define AUTO_INC 0x80

static int wr(const i2c_bus_t *b, uint8_t r, uint8_t v) { return i2c_reg8(b, ACC_ADDR, r, v); }

static int awake(const i2c_bus_t *b)
{
    int e = wr(b, R_CTRL1, 0x67);          /* 200 Hz, normal/HR, X Y Z on */
    e |= wr(b, R_CTRL4, 0x98);             /* BDU, +-4 g, high resolution: 2 mg/digit */
    e |= wr(b, R_CTRL2, 0x00);
    e |= wr(b, R_CTRL5, 0x00);
    e |= wr(b, R_INT1_CFG, 0x00);
    e |= wr(b, R_CLICK_CFG, 0x20);         /* double click on Z: knock on the face */
    e |= wr(b, R_CLICK_THS, 62);           /* 62 x 32 mg = 2 g (tune on hardware) */
    e |= wr(b, R_TIME_LIMIT, 10);          /* 50 ms at 200 Hz */
    e |= wr(b, R_TIME_LATENCY, 20);        /* 100 ms */
    e |= wr(b, R_TIME_WINDOW, 50);         /* 250 ms */
    e |= wr(b, R_CTRL3, 0x80);             /* click on INT1 */
    return e;
}

int acc_init(const i2c_bus_t *b)
{
    uint8_t id = 0;
    if (b->read(b->ctx, ACC_ADDR, R_WHO_AM_I, &id, 1) || id != ACC_WHO_AM_I) return -1;
    return awake(b);
}

int acc_read(const i2c_bus_t *b, float g[3])
{
    uint8_t d[6];
    if (b->read(b->ctx, ACC_ADDR, R_OUT_X_L | AUTO_INC, d, 6)) return -1;
    for (int i = 0; i < 3; i++) g[i] = (int16_t)(d[2 * i] | d[2 * i + 1] << 8) / 16 * 0.002f;   /* 12-bit, left-justified */
    return 0;
}

int acc_double_tap(const i2c_bus_t *b)
{
    uint8_t src = 0;
    if (b->read(b->ctx, ACC_ADDR, R_CLICK_SRC, &src, 1)) return 0;
    return (src & 0x40) && (src & 0x20);   /* IA and DCLICK */
}
