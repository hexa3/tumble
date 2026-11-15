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
