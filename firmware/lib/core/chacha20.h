/* ChaCha20 block function (RFC 8439), used as the output generator after each reseed. */
#ifndef CHACHA20_H
#define CHACHA20_H
#include <stdint.h>

/* out = ChaCha20 block for (key, counter, nonce). */
void chacha20_block(const uint8_t key[32], uint32_t counter, const uint8_t nonce[12], uint8_t out[64]);
#endif
