/* USB serial commands for auditing the die.  One command per line:
 *   raw N        N raw noise samples, hex, 16 per line   (feed to SP 800-90B tools)
 *   roll N S     N results of an S-sided die, one per line, each from its own reseed
 *   health       health-test counters and entropy status
 *   dfu          reboot into the STM32 system bootloader (USB DFU)
 * The platform supplies the I/O and the noise source. */
#ifndef CLI_H
#define CLI_H
#include <stddef.h>
#include <stdint.h>
#include "entropy.h"

typedef struct {
    void (*puts)(void *ctx, const char *s);
    void (*noise)(void *ctx, uint16_t *buf, size_t n);     /* blocking: fill n raw samples */
    void (*trng)(void *ctx, uint32_t *w, size_t n);
    void (*dfu)(void *ctx);
    void *ctx;
    ent_t *ent;
    char line[64];
    size_t n;
} cli_t;

void cli_char(cli_t *c, char ch);
void cli_exec(cli_t *c, const char *line);
#endif
