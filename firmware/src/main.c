/* TinyDie Tumble bring-up: tilt the board and the pips roll around. */
#include "hw.h"
#include "is31fl3733.h"
#include "lis3dh.h"
#include "physics.h"
#include "render.h"
#include "stm32g0xx.h"

static world_t world;
static is31_t led;

int main(void)
{
    hw_init();
    hw_delay_ms(5);
    acc_init(&hw_i2c);
    is31_init(&led, &hw_i2c, IS31_GCC_DEFAULT);
    world_init(&world, 1);

    float lp[3] = {0, 0, 1};
    uint8_t frame[NPIX];
    uint32_t next = hw_ms, tick = 0;
    for (;;) {
        while ((int32_t)(hw_ms - next) < 0) __WFI();
        next += 5;              /* 200 Hz */
        tick++;
        float g[3], a[2];
        acc_read(&hw_i2c, g);
        for (int i = 0; i < 3; i++) lp[i] += (g[i] - lp[i]) * 0.04f;
        physics_accel(g, lp, a);
        world_step(&world, a[0], a[1], 0.005f);
        if (tick % 4 == 0) {          /* 50 frames per second */
            render_world(&world, 1.0f, frame);
            is31_show(&led, frame);
        }
    }
}
