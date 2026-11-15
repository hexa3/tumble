#include "physics.h"
#include <math.h>
#include <string.h>

#define G_TILT 55.0f        /* px/s^2 per g of tilt: slow, deliberate drift */
#define G_SHAKE 3924.0f     /* px/s^2 per g of shake: true scale at 2.5 mm/px */
#define DRAG 0.8f           /* rolling drag, 1/s */
#define E_WALL 0.45f        /* restitution */
#define E_PIP 0.6f
#define K_SPRING 90.0f      /* settle spring, 1/s^2; damping is critical */
#define FADE 4.0f           /* alpha per second */
#define LO (-0.5f + PIP_R)
#define HI (FIELD - 0.5f - PIP_R)

void world_init(world_t *w, uint32_t seed)
{
    memset(w, 0, sizeof *w);
    /* the "7" arrangement of TinyDie Mk I: its seven LEDs */
    static const float mk1[PIPS][2] = {{2, 2}, {8, 2}, {2, 5}, {5, 5}, {8, 5}, {2, 8}, {8, 8}};
    for (int i = 0; i < PIPS; i++) {
        w->p[i].x = w->p[i].tx = mk1[i][0];
        w->p[i].y = w->p[i].ty = mk1[i][1];
        w->p[i].alpha = w->p[i].alpha_to = 1.0f;
        seed = seed * 1664525u + 1013904223u;          /* tiny nudge so pips never stack exactly */
        w->p[i].x += ((seed >> 16) & 0xff) / 2550.0f;
    }
}

static void wall(float *x, float *v, float *imp)
{
    if (*x < LO) { *x = LO; if (*v < 0) { float j = -*v * (1 + E_WALL); *v = -*v * E_WALL; if (j > *imp) *imp = j; } }
    if (*x > HI) { *x = HI; if (*v > 0) { float j = *v * (1 + E_WALL); *v = -*v * E_WALL; if (j > *imp) *imp = j; } }
}

void physics_accel(const float f[2], const float f_lp[2], float a[2])
{
    for (int i = 0; i < 2; i++) a[i] = -(f_lp[i] * G_TILT + (f[i] - f_lp[i]) * G_SHAKE);
}

static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

void world_step(world_t *w, float ax, float ay, float dt)
{
    float imp = 0.0f, en = 0.0f;
    float drag = 1.0f - DRAG * dt;
    for (int i = 0; i < PIPS; i++) {
        pip_t *p = &w->p[i];
        p->vx = (p->vx + ax * dt) * drag;
        p->vy = (p->vy + ay * dt) * drag;
        p->x += p->vx * dt;
        p->y += p->vy * dt;
        wall(&p->x, &p->vx, &imp);
        wall(&p->y, &p->vy, &imp);
        float da = p->alpha_to - p->alpha, step = FADE * dt;
        p->alpha += da > step ? step : (da < -step ? -step : da);
    }
    for (int i = 0; i < PIPS; i++) {
        w->p[i].x = clampf(w->p[i].x, LO, HI);
        w->p[i].y = clampf(w->p[i].y, LO, HI);
        en += w->p[i].vx * w->p[i].vx + w->p[i].vy * w->p[i].vy;
    }
    w->max_impulse = imp;
    w->energy = en / PIPS;
}
