#include "drv2605l.h"

#define R_STATUS 0x00
#define R_MODE 0x01
#define R_RTP 0x02
#define R_LIBRARY 0x03
#define R_GO 0x0C
#define R_RATED 0x16
#define R_CLAMP 0x17
#define R_FEEDBACK 0x1A
#define R_CONTROL1 0x1B
#define R_CONTROL2 0x1C
#define R_CONTROL3 0x1D
#define R_CONTROL4 0x1E

int drv_init(const i2c_bus_t *b, int calibrate)
{
    int e = i2c_reg8(b, DRV_ADDR, R_MODE, 0x00);                 /* out of standby */
    e |= i2c_reg8(b, DRV_ADDR, R_FEEDBACK, 0x80 | (2 << 4) | (2 << 2) | 2);   /* LRA, brake 2, loop 2, bemf 2 */
    e |= i2c_reg8(b, DRV_ADDR, R_RATED, DRV_RATED_VOLTAGE);
    e |= i2c_reg8(b, DRV_ADDR, R_CLAMP, DRV_OD_CLAMP);
    e |= i2c_reg8(b, DRV_ADDR, R_CONTROL1, 0x80 | DRV_DRIVE_TIME);            /* startup boost */
    e |= i2c_reg8(b, DRV_ADDR, R_CONTROL2, 0xF5);                /* defaults: sample 300 us, blank/idiss 1 */
    e |= i2c_reg8(b, DRV_ADDR, R_CONTROL4, 0x30); /* AUTO_CAL_TIME 3 */
    e |= i2c_reg8(b, DRV_ADDR, R_LIBRARY, 6); /* LRA library */
    if (e) return e;
    if (calibrate) {
        e |= i2c_reg8(b, DRV_ADDR, R_MODE, 0x07);
        e |= i2c_reg8(b, DRV_ADDR, R_GO, 1);
        uint8_t go = 1;
        for (int t = 0; t < 200 && go; t++) {          /* calibration takes ~1 s */
            b->delay_ms(b->ctx, 10);
            e |= b->read(b->ctx, DRV_ADDR, R_GO, &go, 1);
        }
        uint8_t st = 0;
        e |= b->read(b->ctx, DRV_ADDR, R_STATUS, &st, 1);
        if (e) return e;
        if (go || (st & 0x08)) return -2;               /* DIAG_RESULT */
    }
    e |= i2c_reg8(b, DRV_ADDR, R_CONTROL3, 0xA0);       /* defaults, signed RTP data */
    e |= i2c_reg8(b, DRV_ADDR, R_RTP, 0);
    e |= i2c_reg8(b,DRV_ADDR, R_MODE, 0x05); /* real-time playback */
    return e;
}

int drv_rtp(const i2c_bus_t *b, uint8_t amplitude)
{
    return i2c_reg8(b, DRV_ADDR, R_RTP, amplitude);
}

int drv_standby(const i2c_bus_t *b, int standby)
{
    return i2c_reg8(b, DRV_ADDR, R_MODE, standby ? 0x45 : 0x05);
}
