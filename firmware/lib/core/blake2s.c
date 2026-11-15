#include "blake2s.h"
#include <string.h>

static const uint32_t IV[8] = {0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                               0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19};
static const uint8_t SIGMA[10][16] = {
    {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}, {14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3},
    {11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4}, {7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8},
    {9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13}, {2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9},
    {12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11}, {13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10},
    {6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5}, {10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0}};

static uint32_t ror(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
static uint32_t ld32(const uint8_t *p) { return p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24; }

static void compress(blake2s_t *s, int last)
{
    uint32_t v[16], m[16];
    for (int i = 0; i < 16; i++) m[i] = ld32(s->buf + 4 * i);
    for (int i = 0; i < 8; i++) { v[i] = s->h[i]; v[i + 8] = IV[i]; }
    v[12] ^= s->t[0];
    v[13] ^= s->t[1];
    if (last) v[14] = ~v[14];
#define G(a, b, c, d, x, y)                                       \
    do {                                                          \
        v[a] += v[b] + (x); v[d] = ror(v[d] ^ v[a], 16);           \
        v[c] += v[d];       v[b] = ror(v[b] ^ v[c], 12);           \
        v[a] += v[b] + (y); v[d] = ror(v[d] ^ v[a], 8);            \
        v[c] += v[d];       v[b] = ror(v[b] ^ v[c], 7);            \
    } while (0)
    for (int r = 0; r < 10; r++) {
        const uint8_t *z = SIGMA[r];
        G(0, 4, 8, 12, m[z[0]], m[z[1]]);
        G(1, 5, 9, 13, m[z[2]], m[z[3]]);
        G(2, 6, 10, 14, m[z[4]], m[z[5]]);
        G(3, 7, 11, 15, m[z[6]], m[z[7]]);
        G(0, 5, 10, 15, m[z[8]], m[z[9]]);
        G(1, 6, 11, 12, m[z[10]], m[z[11]]);
        G(2, 7, 8, 13, m[z[12]], m[z[13]]);
        G(3, 4, 9, 14, m[z[14]], m[z[15]]);
    }
#undef G
    for (int i = 0; i < 8; i++) s->h[i] ^= v[i] ^ v[i + 8];
}

void blake2s_init(blake2s_t *s)
{
    memset(s, 0, sizeof *s);
    memcpy(s->h, IV, sizeof IV);
    s->h[0] ^= 0x01010000u ^ 32;      /* depth 1, fanout 1, no key, 32-byte digest */
}

void blake2s_update(blake2s_t *s, const void *in, size_t len)
{
    const uint8_t *p = in;
    while (len) {
        size_t k = 64 - s->n;
        if (k > len) k = len;
        memcpy(s->buf + s->n, p, k);
        s->n += k;
        p += k;
        len -= k;
        if (s->n == 64) {
            s->t[0] += 64;
            if (s->t[0] < 64) s->t[1]++;
            compress(s, 0);
            s->n = 0;
        }
    }
}

void blake2s_final(blake2s_t *s, uint8_t out[32])
{
    s->t[0] += (uint32_t)s->n;
    if (s->t[0] < s->n) s->t[1]++;
    memset(s->buf + s->n, 0, 64 - s->n);
    compress(s, 1);
    for (int i = 0; i < 32; i++) out[i] = (uint8_t)(s->h[i / 4] >> (8 * (i % 4)));
    memset(s, 0, sizeof *s);
}
