/* TinyDie Tumble main loop: 200 Hz tick; the behaviour lives in lib/core (app.c). */
#include <string.h>
#include "app.h"
#include "cli.h"
#include "drv2605l.h"
#include "hw.h"
#include "is31fl3733.h"
#include "lis3dh.h"
#include "max17048.h"
#include "stm32g0xx.h"

#define SWD_WINDOW_MS 2000      /* pins 7/8 stay SWD this long after reset so a probe can attach */
#define LOW_BATTERY_PCT 5

static app_t app;
static is31_t led;
static cli_t cli;

static void cli_puts(void *ctx, const char *s) { (void)ctx; hw_uart_puts(s); }
static void cli_noise(void *ctx, uint16_t *b, size_t n) { (void)ctx; hw_noise(1); hw_noise_samples(b, n); }
static void cli_trng(void *ctx, uint32_t *w, size_t n) { (void)ctx; hw_trng(w, n); }

static void peripherals_on(void)
{
    is31_sleep(&led, 0);
    drv_standby(&hw_i2c, 0);
    acc_sleep_mode(&hw_i2c, 0);
}

static void peripherals_off(void)
{
    uint8_t dark[NPIX] = {0};
    is31_show(&led, dark);
    is31_sleep(&led, 1);              /* software shutdown: SDB is pulled up on the core */
    drv_standby(&hw_i2c, 1);          /* EN is tied high; STANDBY is the low-power state */
    hw_noise(0);
    acc_sleep_mode(&hw_i2c, 1);
}

int main(void)
{
    hw_init();
    hw_delay_ms(5);
    acc_init(&hw_i2c);
    drv_init(&hw_i2c, 1);             /* LRA auto-calibration on power-up */
    is31_init(&led, &hw_i2c, IS31_GCC_DEFAULT);
    uint32_t seed[2];
    hw_trng(seed, 2);
    app_init(&app, seed[0]);
    ent_add_trng(&app.ent, seed, 2);
    cli = (cli_t){cli_puts, cli_noise, cli_trng, 0, 0, &app.ent, {0}, 0};

    uint32_t next = hw_ms, tick = 0, noise_since = 0;
    int swd = 1, low = 0;
    for (;;) {
        while ((int32_t)(hw_ms - next) < 0) __WFI();
        next += 1000 / APP_HZ;
        tick++;
        if (swd && hw_ms > SWD_WINDOW_MS) { hw_release_swd(); swd = 0; }

        for (int c; (c = hw_uart_getc()) >= 0;) cli_char(&cli, (char)c);

        app_in_t in = {{0, 0, 1}, 0, low};
        acc_read(&hw_i2c, in.g);
        ent_add_aux(&app.ent, in.g, sizeof in.g);           /* mixed in, never credited */
        if (!swd && hw_acc_int()) in.double_tap = acc_double_tap(&hw_i2c);
        if (tick % APP_HZ == 0) {
            gauge_t g;
            if (!gauge_read(&hw_i2c, &g)) low = in.low_battery = g.soc < LOW_BATTERY_PCT;
        }

        app_out_t out;
        app_step(&app, &in, &out);

        if (out.want_noise && !swd) {
            if (!noise_since) { hw_noise(1); noise_since = hw_ms; }
            else if (hw_ms - noise_since > 50) {             /* let the boost rail settle */
                uint16_t s[48];
                uint32_t w;
                hw_noise_samples(s, 48);
                ent_add_noise(&app.ent, s, 48);
                hw_trng(&w, 1);
                ent_add_trng(&app.ent, &w, 1);
            }
        } else if (noise_since) {
            hw_noise(0);
            noise_since = 0;
        } else if (out.want_noise) {                          /* inside the SWD window: TRNG only */
            uint32_t w[4];
            hw_trng(w, 4);
            ent_add_aux(&app.ent, w, sizeof w);
        }
        static uint8_t last_hap;
        if (out.haptic != last_hap) { drv_rtp(&hw_i2c, out.haptic); last_hap = out.haptic; }
        if (tick % 4 == 0) is31_show(&led, out.frame);       /* 50 frames per second */

        if (out.sleep) {
            if (hw_usb_present() || swd) { app_wake(&app); continue; }   /* stay up on USB */
            peripherals_off();
            hw_sleep();
            peripherals_on();
            app_wake(&app);
            next = hw_ms;
        }
    }
}
