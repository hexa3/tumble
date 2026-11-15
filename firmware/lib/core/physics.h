/* Seven pips as discs in the 11 x 11 LED field.  Units: pixels (LED pitch), seconds.
 *
 * Free mode: each pip feels -f, where f is the accelerometer's specific force in the board plane
 * (f = a - g).  That is what a loose ball in a box feels, so tilting rolls the pips downhill and
 * shaking throws them around.  physics_accel() turns f into pixel units: the slow part (tilt) with a
 * gentle gain so pips drift, the fast part (shake) at true scale (1 g = 3924 px/s^2 at 2.5 mm/px)
 * so a real shake moves the box under the pips by real distances.  Walls and pip-pip contacts are inelastic; every contact reports its
 * impulse so the haptic motor can tick in proportion.
 */
#ifndef PHYSICS_H
#define PHYSICS_H
#include <stdint.h>

#define PIPS 7
#define FIELD 11
#define PIP_R 0.95f

typedef struct {
    float x, y, vx, vy;
    float alpha, alpha_to;
    float tx, ty;          /* settle target */
} pip_t;

typedef struct {
    pip_t p[PIPS];
    int settling;
    float max_impulse;     /* largest contact impulse in the last step (px/s) */
    float energy;          /* kinetic energy per pip, (px/s)^2 */
} world_t;

void world_init(world_t *w, uint32_t seed);
/* ax, ay: acceleration felt by the pips, px/s^2 (see physics_accel).  dt: seconds. */
void world_step(world_t *w, float ax, float ay, float dt);
/* f, f_lp: specific force and its low-passed value (gravity estimate), in g, board plane */
void physics_accel(const float f[2], const float f_lp[2], float a[2]);
#endif
