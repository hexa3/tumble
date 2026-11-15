/* BLAKE2s-256 (RFC 7693), unkeyed, streaming.  Used to condition the entropy pool. */
#ifndef BLAKE2S_H
#define BLAKE2S_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t h[8], t[2];
    uint8_t buf[64];
    size_t n;
} blake2s_t;

void blake2s_init(blake2s_t *s);
void blake2s_update(blake2s_t *s, const void *in, size_t len);
void blake2s_final(blake2s_t *s, uint8_t out[32]);
#endif
