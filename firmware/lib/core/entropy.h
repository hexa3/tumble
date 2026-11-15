/* Entropy pool: raw avalanche-noise samples are health-tested and absorbed into BLAKE2s together with
 * the MCU's TRNG and accelerometer LSBs.  A reseed hashes the pool into a ChaCha20 key; die results are
 * drawn from that key stream with rejection sampling.
 *
 * Crediting is deliberately conservative and is a design parameter, not a measurement:
 *   ENT_NOISE_MILLIBITS  min-entropy credited per raw ADC sample (default 0.5 bit) -- replace with the
 *                        value from an SP 800-90B assessment of real samples (tools/audit.py raw ...)
 *   the TRNG and accelerometer are mixed in but not credited while the noise source is healthy.
 * If the noise source fails its health tests, the die keeps working on TRNG words credited at
 * ENT_TRNG_BITS each, and ent_status() reports the failure so the display can show it.
 */
#ifndef ENTROPY_H
#define ENTROPY_H
#include <stddef.h>
#include <stdint.h>
#include "blake2s.h"

#ifndef ENT_NOISE_MILLIBITS
#define ENT_NOISE_MILLIBITS 500
#endif
#ifndef ENT_TRNG_BITS
#define ENT_TRNG_BITS 16
#endif
#define ENT_RESEED_BITS 256

/* SP 800-90B section 4.4 health tests, alpha = 2^-20, for H = 1 bit/sample (conservative).
 * RCT cutoff C = 1 + ceil(20 / H).  APT window 512; cutoff for H = 1 from SP 800-90B Table 2
 * (verify against the standard once H is measured). */
#define ENT_RCT_CUTOFF 21
#define ENT_APT_WINDOW 512
#define ENT_APT_CUTOFF 410

enum { ENT_OK = 0, ENT_NOISE_FAILED = 1 };

typedef struct {
    blake2s_t pool;
    uint32_t credited_mbits;     /* millibits credited since the last reseed */
    uint8_t key[32];
    uint8_t block[64];
    uint32_t counter, used;      /* ChaCha20 counter, bytes used of `block` */
    uint32_t reseeds;
    /* health tests */
    uint16_t rct_last, apt_ref;
    uint32_t rct_run, apt_n, apt_count;
    uint32_t rct_fail, apt_fail, samples;
    int status;
} ent_t;

void ent_init(ent_t *e);
void ent_add_noise(ent_t *e, const uint16_t *s, size_t n);   /* raw ADC samples */
void ent_add_trng(ent_t *e, const uint32_t *w, size_t n);
void ent_add_aux(ent_t *e, const void *p, size_t n);         /* accelerometer etc., never credited */
int ent_ready(const ent_t *e);
void ent_reseed(ent_t *e);
uint32_t ent_u32(ent_t *e);
uint32_t ent_uniform(ent_t *e, uint32_t n);                  /* 1..n, unbiased */
int ent_status(const ent_t *e);
#endif
