#include "physics.h"
#include <math.h>
#include <string.h>

#define G_TILT 55.0f        /* px/s^2 per g of tilt: slow, deliberate drift */
#define G_SHAKE 1960.0f     /* px/s^2 per g of shake: half of true scale (3924), tuned by eye later */
#define DRAG 1.6f           /* rolling drag, 1/s */
#define E_WALL 0.45f        /* restitution */
#define E_PIP 0.6f
#define K_SPRING 90.0f      /* settle spring, 1/s^2; damping is critical */
#define FADE 4.0f           /* alpha per second */
#define LO (-0.5f + PIP_R)
#define HI (FIELD - 0.5f - PIP_R)

static const float FACE[7][6][2] = {
    {{0}},
    {{5, 5}},
    {{2, 2}, {8, 8}},
    {{2, 2}, {5, 5}, {8, 8}},
    {{2, 2}, {8, 2}, {2, 8}, {8, 8}},
    {{2, 2}, {8, 2}, {5, 5}, {2, 8}, {8, 8}},
    {{2, 2}, {8, 2}, {2, 5}, {8, 5}, {2, 8}, {8, 8}},
};

void face_points(int n, float out[][2])
{
    for (int i = 0; i < n; i++) { out[i][0] = FACE[n][i][0]; out[i][1] = FACE[n][i][1]; }
}

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
        if (w->settling) {
            float c = 2.0f * sqrtf(K_SPRING);
            p->vx += (K_SPRING * (p->tx - p->x) - c * p->vx) * dt;
            p->vy += (K_SPRING * (p->ty - p->y) - c * p->vy) * dt;
        } else {
            p->vx = (p->vx + ax * dt) * drag;
            p->vy = (p->vy + ay * dt) * drag;
        }
        p->x += p->vx * dt;
        p->y += p->vy * dt;
        wall(&p->x, &p->vx, &imp);
        wall(&p->y, &p->vy, &imp);
        float da = p->alpha_to - p->alpha, step = FADE * dt;
        p->alpha += da > step ? step : (da < -step ? -step : da);
    }
    if (!w->settling) {               /* pip-pip contacts, only among visible pips */
        for (int i = 0; i < PIPS; i++) {
            for (int j = i + 1; j < PIPS; j++) {
                pip_t *a = &w->p[i], *b = &w->p[j];
                if (a->alpha < 0.5f || b->alpha < 0.5f) continue;
                float dx = b->x - a->x, dy = b->y - a->y, d2 = dx * dx + dy * dy, r = 2 * PIP_R;
                if (d2 >= r * r || d2 < 1e-8f) continue;
                float d = sqrtf(d2), nx = dx / d, ny = dy / d;
                float push = (r - d) / 2;
                a->x -= nx * push; a->y -= ny * push;
                b->x += nx * push; b->y += ny * push;
                float vn = (b->vx - a->vx) * nx + (b->vy - a->vy) * ny;
                if (vn < 0) {
                    float j_ = -(1 + E_PIP) * vn / 2;
                    a->vx -= j_ * nx; a->vy -= j_ * ny;
                    b->vx += j_ * nx; b->vy += j_ * ny;
                    if (2 * j_ > imp) imp = 2 * j_;
                }
            }
        }
    }
    for (int i = 0; i < PIPS; i++) {                 /* contact pushes must not cross a wall */
        w->p[i].x = clampf(w->p[i].x, LO, HI);
        w->p[i].y = clampf(w->p[i].y, LO, HI);
        en += w->p[i].vx * w->p[i].vx + w->p[i].vy * w->p[i].vy;
    }
    w->max_impulse = imp;
    w->energy = en / PIPS;
}

void world_settle(world_t *w, int n)
{
    if (n <= 0) {
        w->settling = 0;
        for (int i = 0; i < PIPS; i++) w->p[i].alpha_to = 1.0f;
        return;
    }
    float pts[6][2];
    face_points(n, pts);
    int taken[PIPS] = {0};
    /* greedy nearest assignment: each face point takes the closest free visible pip */
    for (int k = 0; k < n; k++) {
        int best = -1;
        float bd = 1e9f;
        for (int i = 0; i < PIPS; i++) {
            if (taken[i]) continue;
            float dx = w->p[i].x - pts[k][0], dy = w->p[i].y - pts[k][1], d = dx * dx + dy * dy;
            if (d < bd) { bd = d; best = i; }
        }
        taken[best] = 1;
        w->p[best].tx = pts[k][0];
        w->p[best].ty = pts[k][1];
        w->p[best].alpha_to = 1.0f;
    }
    for (int i = 0; i < PIPS; i++) {
        if (taken[i]) continue;
        w->p[i].tx = w->p[i].x;           /* surplus pips stop where they are and fade */
        w->p[i].ty = w->p[i].y;
        w->p[i].alpha_to = 0.0f;
    }
    w->settling = 1;
}

int world_settled(const world_t *w)
{
    if (!w->settling) return 0;
    for (int i = 0; i < PIPS; i++) {
        const pip_t *p = &w->p[i];
        if (fabsf(p->alpha - p->alpha_to) > 0.02f) return 0;
        if (p->alpha_to > 0 && (fabsf(p->x - p->tx) > 0.05f || fabsf(p->y - p->ty) > 0.05f)) return 0;
    }
    return 1;
}
