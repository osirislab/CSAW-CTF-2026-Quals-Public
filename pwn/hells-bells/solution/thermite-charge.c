/* Thermite Charge - CSAW Quals 2026 pwn
 *
 * A "demolition inventory" note manager. Each charge is a heap buffer.
 *
 * The intended bug set:
 *   - free() does NOT clear the slot pointer  -> dangling reference
 *   - edit() re-writes the buffer using the stored size, with no check that
 *     the slot is still "live"  -> edit-after-free (overwrite a freed
 *     tcache chunk's fd)
 *   - view() prints the raw bytes            -> read-after-free (libc leak)
 *
 * glibc 2.31: tcache present, no safe-linking, __free_hook available.
 * Intended path: unsorted-bin libc leak -> tcache poison __free_hook ->
 * system("/bin/sh").
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_CHARGES 16
#define MAX_SIZE    0x1000

static char  *charges[MAX_CHARGES];
static size_t sizes[MAX_CHARGES];

static void flush(void) { fflush(stdout); fflush(stderr); }

static long read_long(void)
{
    char buf[32];
    int i = 0, c;
    while (i < (int)sizeof(buf) - 1) {
        c = getchar();
        if (c == '\n' || c == EOF)
            break;
        buf[i++] = (char)c;
    }
    buf[i] = '\0';
    return strtol(buf, NULL, 10);
}

/* read exactly n raw bytes (nulls allowed) */
static void read_n(char *dst, size_t n)
{
    size_t got = 0;
    while (got < n) {
        ssize_t r = read(0, dst + got, n - got);
        if (r <= 0)
            break;
        got += (size_t)r;
    }
}

static int valid_index(long idx)
{
    return idx >= 0 && idx < MAX_CHARGES;
}

static void do_add(void)
{
    printf("slot (0-%d): ", MAX_CHARGES - 1);
    flush();
    long idx = read_long();
    if (!valid_index(idx)) { puts("bad slot"); return; }
    if (charges[idx] != NULL) { puts("slot occupied"); return; }

    printf("size: ");
    flush();
    long sz = read_long();
    if (sz <= 0 || sz > MAX_SIZE) { puts("bad size"); return; }

    char *p = malloc((size_t)sz);
    if (!p) { puts("out of thermite"); return; }

    printf("payload: ");
    flush();
    read_n(p, (size_t)sz);

    charges[idx] = p;
    sizes[idx] = (size_t)sz;
    printf("charge planted in slot %ld\n", idx);
}

static void do_free(void)
{
    printf("slot: ");
    flush();
    long idx = read_long();
    if (!valid_index(idx) || charges[idx] == NULL) { puts("bad slot"); return; }

    free(charges[idx]);           /* BUG: pointer intentionally left dangling */
    puts("charge defused");
}

static void do_edit(void)
{
    printf("slot: ");
    flush();
    long idx = read_long();
    if (!valid_index(idx) || charges[idx] == NULL) { puts("bad slot"); return; }

    printf("new payload: ");
    flush();
    read_n(charges[idx], sizes[idx]);   /* BUG: writes even if freed */
    puts("charge rewired");
}

static void do_view(void)
{
    printf("slot: ");
    flush();
    long idx = read_long();
    if (!valid_index(idx) || charges[idx] == NULL) { puts("bad slot"); return; }

    printf("payload: ");
    write(1, charges[idx], sizes[idx]);  /* BUG: reads even if freed */
    puts("");
}

static void menu(void)
{
    puts("");
    puts("=== Thermite Charge Inventory ===");
    puts("1) plant charge");
    puts("2) defuse charge");
    puts("3) rewire charge");
    puts("4) inspect charge");
    puts("5) leave");
    printf("> ");
    flush();
}

int main(void)
{
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    for (;;) {
        menu();
        long choice = read_long();
        switch (choice) {
        case 1: do_add();  break;
        case 2: do_free(); break;
        case 3: do_edit(); break;
        case 4: do_view(); break;
        case 5: puts("boom."); return 0;
        default: puts("no such option");
        }
    }
}
