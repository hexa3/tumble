/* Turn the world into 121 8-bit LED levels, row-major, gamma-corrected. */
#ifndef RENDER_H
#define RENDER_H
#include <stdint.h>
#include "physics.h"

#define NPIX (FIELD * FIELD)

void render_world(const world_t *w, float brightness, uint8_t out[NPIX]);
uint8_t gamma8(float v);                                  /* 0..1 -> PWM 0..255 */
#endif
