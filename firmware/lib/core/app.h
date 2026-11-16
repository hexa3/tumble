/* Everything TinyDie Tumble does, without any hardware: fed accelerometer samples at 200 Hz, it
 * returns an LED frame, a haptic amplitude, whether it wants noise samples, and whether to sleep.
 * The STM32 main loop (src/main.c) and the host simulator (test/host) both drive it. */
#ifndef APP_H
#define APP_H
#include <stdint.h>
#include "entropy.h"
#include "physics.h"
#include "render.h"

#define APP_HZ 200

typedef enum { ST_SHOW, ST_TUMBLE, ST_SETTLE, ST_MODE, ST_FADE, ST_SLEEP } app_state_t;

typedef struct {
    float g[3];           /* specific force, g, board axes (z out of the face) */
    int double_tap;       /* from the accelerometer's tap engine */
    int low_battery;
} app_in_t;

typedef struct {
    uint8_t frame[NPIX];
    uint8_t haptic;       /* 0..127 RTP amplitude for this tick */
    int want_noise;       /* turn the avalanche source on and feed ent_add_noise() */
    int sleep;            /* go to STOP2 now */
} app_out_t;

typedef struct {
    app_state_t st;
    world_t w;
    ent_t ent;
    uint32_t t, t_motion, t_state, t_haptic;
    float lp[3];          /* low-passed specific force: the gravity estimate */
    int mode;             /* index into APP_SIDES */
    uint32_t result, rolls;
    uint8_t hap_amp;
    uint16_t hap_left;
    float bright;
} app_t;

extern const uint8_t APP_SIDES[];
extern const int APP_MODES;

void app_init(app_t *a, uint32_t seed);
void app_step(app_t *a, const app_in_t *in, app_out_t *out);
void app_wake(app_t *a);
#endif
