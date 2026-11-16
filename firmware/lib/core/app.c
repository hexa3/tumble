#include "app.h"
#include <math.h>
#include <string.h>

const uint8_t APP_SIDES[] = {6, 4, 8, 10, 12, 20, 100};
const int APP_MODES = sizeof APP_SIDES;

#define MS(x) ((uint32_t)((x) * APP_HZ / 1000))
#define SHAKE_G 0.35f          /* deviation from the gravity estimate that counts as a shake */
#define CALM_MS 350            /* quiet this long after a shake: the die lands */
#define SHOW_MS 8000           /* then fade and sleep */

static void set_state(app_t *a, app_state_t s) { a->st = s; a->t_state = a->t; }

void app_init(app_t *a, uint32_t seed)
{
    memset(a, 0, sizeof *a);
    world_init(&a->w, seed);
    ent_init(&a->ent);
    a->lp[2] = 1.0f;
    a->bright = 1.0f;
    a->result = 6;
    world_settle(&a->w, 6);
    set_state(a, ST_SHOW);
}

void app_wake(app_t *a)
{
    a->bright = 1.0f;
    a->t_motion = a->t;
    set_state(a, ST_SHOW);
}

void app_step(app_t *a, const app_in_t *in, app_out_t *out)
{
    const float dt = 1.0f / APP_HZ;
    a->t++;
    /* gravity estimate and shake detector */
    float dev = 0;
    for (int i = 0; i < 3; i++) {
        a->lp[i] += (in->g[i] - a->lp[i]) * 0.04f;
        dev += (in->g[i] - a->lp[i]) * (in->g[i] - a->lp[i]);
    }
    int shaking = sqrtf(dev) > SHAKE_G;
    if (shaking) a->t_motion = a->t;
    int sides = APP_SIDES[a->mode];
    memset(out, 0, sizeof *out);

    switch (a->st) {
    case ST_SHOW:
        if (shaking) {
            world_settle(&a->w, 0);
            set_state(a, ST_TUMBLE);
            break;
        }
        if (a->t - a->t_motion > MS(SHOW_MS)) set_state(a, ST_FADE);
        break;
    case ST_TUMBLE:
        if (a->t - a->t_motion > MS(CALM_MS) && a->w.energy < 4.0f && ent_ready(&a->ent)) {
            ent_reseed(&a->ent);
            a->result = ent_uniform(&a->ent, sides);
            a->rolls++;
            world_settle(&a->w, sides == 6 ? (int)a->result : 0);
            set_state(a, ST_SETTLE);
        }
        break;
    case ST_SETTLE:
        if (shaking) { world_settle(&a->w, 0); set_state(a, ST_TUMBLE); break; }
        if ((sides == 6 && world_settled(&a->w)) || (sides != 6 && a->t - a->t_state > MS(300))) {
            set_state(a, ST_SHOW);
        }
        break;
    case ST_MODE:                              /* no die switching yet */
        break;
    case ST_FADE:
        a->bright -= dt / 0.6f;
        if (shaking || in->double_tap) { app_wake(a); break; }
        if (a->bright <= 0) { a->bright = 0; set_state(a, ST_SLEEP); }
        break;
    case ST_SLEEP:
        out->sleep = 1;
        return;
    }

    /* physics runs in every awake state; in free mode the pips feel -f in the board plane */
    float acc[2];
    physics_accel(in->g, a->lp, acc);
    world_step(&a->w, acc[0], acc[1], dt);

    /* frame */
    render_world(&a->w, a->bright, out->frame);

    out->want_noise = a->st == ST_TUMBLE || !ent_ready(&a->ent);
}
