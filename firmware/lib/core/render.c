#include "render.h"
#include <math.h>
#include <string.h>

uint8_t gamma8(float v)
{
    if (v <= 0) return 0;
    if (v >= 1) return 255;
    float g = v * v * (0.6f + 0.4f * v);        /* ~gamma 2.4, cheap */
    int x = (int)(g * 255.0f + 0.5f);
    return (uint8_t)(x < 1 ? 1 : x);              /* anything visible stays visible */
}

void render_world(const world_t *w, float brightness, uint8_t out[NPIX])
{
    float acc[NPIX] = {0};
    for (int i = 0; i < PIPS; i++) {
        const pip_t *p = &w->p[i];
        if (p->alpha <= 0.002f) continue;
        int x0 = (int)floorf(p->x - PIP_R - 1), x1 = (int)ceilf(p->x + PIP_R + 1);
        int y0 = (int)floorf(p->y - PIP_R - 1), y1 = (int)ceilf(p->y + PIP_R + 1);
        for (int y = y0; y <= y1; y++) {
            if (y < 0 || y >= FIELD) continue;
            for (int x = x0; x <= x1; x++) {
                if (x < 0 || x >= FIELD) continue;
                float d = sqrtf((x - p->x) * (x - p->x) + (y - p->y) * (y - p->y));
                float c = PIP_R + 0.5f - d;              /* 1 px soft edge: sub-pixel motion */
                if (c > 1) c = 1;
                if (c > 0) acc[y * FIELD + x] += c * p->alpha;
            }
        }
    }
    for (int k = 0; k < NPIX; k++) out[k] = gamma8((acc[k] > 1 ? 1 : acc[k]) * brightness);
}

/* 3x5 digits, rows top to bottom, bit 2 = left column */
static const uint8_t DIGIT[10][5] = {
    {7, 5, 5, 5, 7}, {2, 6, 2, 2, 7}, {7, 1, 7, 4, 7}, {7, 1, 7, 1, 7}, {5, 5, 7, 1, 1},
    {7, 4, 7, 1, 7}, {7, 4, 7, 5, 7}, {7, 1, 1, 2, 2}, {7, 5, 7, 5, 7}, {7, 5, 7, 1, 7}};

static void put_digit(int d, int x0, int y0, uint8_t lv, uint8_t out[NPIX])
{
    for (int r = 0; r < 5; r++)
        for (int c = 0; c < 3; c++)
            if (DIGIT[d][r] & (4 >> c)) out[(y0 + r) * FIELD + x0 + c] = lv;
}

void render_number(int n, float brightness, uint8_t out[NPIX])
{
    memset(out, 0, NPIX);
    uint8_t lv = gamma8(brightness);
    char s[4];
    int len = 0;
    if (n >= 100) { s[len++] = 1; s[len++] = 0; s[len++] = 0; }
    else if (n >= 10) { s[len++] = (char)(n / 10); s[len++] = (char)(n % 10); }
    else s[len++] = (char)n;
    int w = len * 4 - 1, x = (FIELD - w) / 2, y = (FIELD - 5) / 2;
    for (int i = 0; i < len; i++) put_digit(s[i], x + 4 * i, y, lv, out);
}

void render_mark(uint8_t out[NPIX], uint8_t level) { out[FIELD - 1] = level; }
