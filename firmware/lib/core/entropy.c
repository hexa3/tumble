#include "entropy.h"
#include <string.h>
#include "chacha20.h"

void ent_init(ent_t *e)
{
    memset(e, 0, sizeof *e);
    blake2s_init(&e->pool);
    e->used = 64;
}

static void health(ent_t *e, uint16_t x)
{
    /* repetition count test */
    if (e->samples && x == e->rct_last) {
        if (++e->rct_run >= ENT_RCT_CUTOFF) { e->rct_fail++; e->status = ENT_NOISE_FAILED; e->rct_run = 1; }
    } else {
        e->rct_last = x;
        e->rct_run = 1;
    }
    /* adaptive proportion test */
    if (e->apt_n == 0) { e->apt_ref = x; e->apt_count = 1; }
    else if (x == e->apt_ref && ++e->apt_count >= ENT_APT_CUTOFF) {
        e->apt_fail++;
        e->status = ENT_NOISE_FAILED;
    }
    if (++e->apt_n == ENT_APT_WINDOW) e->apt_n = 0;
    e->samples++;
}

void ent_add_noise(ent_t *e, const uint16_t *s, size_t n)
{
    for (size_t i = 0; i < n; i++) health(e, s[i]);
    blake2s_update(&e->pool, s, n * sizeof *s);
    if (e->status == ENT_OK) e->credited_mbits += (uint32_t)n * ENT_NOISE_MILLIBITS;
}

void ent_add_trng(ent_t *e, const uint32_t *w, size_t n)
{
    blake2s_update(&e->pool, w, n * sizeof *w);
    if (e->status != ENT_OK) e->credited_mbits += (uint32_t)n * ENT_TRNG_BITS * 1000u;
}

void ent_add_aux(ent_t *e, const void *p, size_t n) { blake2s_update(&e->pool, p, n); }

int ent_ready(const ent_t *e) { return e->credited_mbits >= ENT_RESEED_BITS * 1000u; }

int ent_status(const ent_t *e) { return e->status; }

void ent_reseed(ent_t *e)
{
    uint8_t d[32];
    blake2s_update(&e->pool, e->key, sizeof e->key);     /* chain: old key feeds the new one */
    blake2s_update(&e->pool, &e->reseeds, sizeof e->reseeds);
    blake2s_final(&e->pool, d);
    memcpy(e->key, d, 32);
    memset(d, 0, sizeof d);
    blake2s_init(&e->pool);
    e->credited_mbits = 0;
    e->counter = 0;
    e->used = 64;
    e->reseeds++;
}

uint32_t ent_u32(ent_t *e)
{
    if (e->used + 4 > 64) {
        static const uint8_t nonce[12] = {'T', 'u', 'm', 'b', 'l', 'e', 'D', 'i', 'e', 0, 0, 1};
        chacha20_block(e->key, e->counter++, nonce, e->block);
        e->used = 0;
    }
    const uint8_t *p = e->block + e->used;
    e->used += 4;
    return p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24;
}

uint32_t ent_uniform(ent_t *e, uint32_t n)
{
    if (n < 2) return 1;
    uint32_t limit = (uint32_t)(0x100000000ull - (0x100000000ull % n));   /* multiple of n */
    uint32_t x;
    do x = ent_u32(e); while (limit && x >= limit);
    return x % n;
}
