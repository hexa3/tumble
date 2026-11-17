#include "cli.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void fill(cli_t *c)
{
    uint16_t buf[64];
    uint32_t w[4];
    while (!ent_ready(c->ent)) {
        c->noise(c->ctx, buf, 64);
        ent_add_noise(c->ent, buf, 64);
        c->trng(c->ctx, w, 4);
        ent_add_trng(c->ent, w, 4);
    }
}

void cli_exec(cli_t *c, const char *line)
{
    char out[128];
    unsigned long n = 0, s = 0;
    if (sscanf(line, "raw %lu", &n) == 1) {
        uint16_t buf[16];
        while (n) {
            size_t k = n > 16 ? 16 : n;
            c->noise(c->ctx, buf, k);
            int p = 0;
            for (size_t i = 0; i < k; i++) p += snprintf(out + p, sizeof out - p, "%03x%s", buf[i], i + 1 < k ? " " : "\n");
            c->puts(c->ctx, out);
            n -= k;
        }
    } else if (sscanf(line, "roll %lu %lu", &n, &s) == 2 && s >= 2) {
        while (n--) {
            fill(c);
            ent_reseed(c->ent);
            snprintf(out, sizeof out, "%lu\n", (unsigned long)ent_uniform(c->ent, (uint32_t)s));
            c->puts(c->ctx, out);
        }
    } else if (!strncmp(line, "health", 6)) {
        snprintf(out, sizeof out, "samples %lu rct_fail %lu apt_fail %lu status %s\n",
                 (unsigned long)c->ent->samples, (unsigned long)c->ent->rct_fail, (unsigned long)c->ent->apt_fail,
                 ent_status(c->ent) == ENT_OK ? "ok" : "NOISE-FAILED");
        c->puts(c->ctx, out);
    } else if (line[0]) {
        c->puts(c->ctx, "? raw N | roll N S | health\n");
    }
}

void cli_char(cli_t *c, char ch)
{
    if (ch == '\r' || ch == '\n') {
        c->line[c->n] = 0;
        cli_exec(c, c->line);
        c->n = 0;
    } else if (c->n + 1 < sizeof c->line) {
        c->line[c->n++] = ch;
    }
}
