/* Guard Dog - CSAW Quals 2026 pwn
 *
 * A K-9 unit manager. Each "dog" is a heap object with a function pointer
 * (its bark) followed... no -- with the NAME first and the bark handler
 * after it:
 *
 *     struct dog { char name[0x18]; void (*bark)(struct dog *); };
 *
 * `command` invokes dog->bark(dog), i.e. it calls the handler with a
 * pointer to the object (which begins with the name) in the first argument.
 *
 * Intended bug: `release` frees the dog but leaves the slot pointer live
 * (use-after-free). A same-size "note" allocation reclaims the freed chunk
 * with attacker-controlled bytes, overwriting `bark`. A separate
 * read-after-free on a large freed note leaks libc.
 *
 * glibc 2.31.  Intended path: unsorted-bin libc leak -> reclaim a released
 * dog with name="/bin/sh" and bark=system -> command -> system("/bin/sh").
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX 8
#define NAMELEN 0x18
#define MAX_NOTE 0x1000

struct dog {
    char name[NAMELEN];
    void (*bark)(struct dog *);
};

static struct dog *dogs[MAX];
static char  *notes[MAX];
static size_t note_sz[MAX];

static void flush(void) { fflush(stdout); }

static long read_long(void)
{
    char buf[32];
    int i = 0, c;
    while (i < (int)sizeof(buf) - 1) {
        c = getchar();
        if (c == '\n' || c == EOF) break;
        buf[i++] = (char)c;
    }
    buf[i] = '\0';
    return strtol(buf, NULL, 10);
}

static void read_n(char *dst, size_t n)
{
    size_t got = 0;
    while (got < n) {
        ssize_t r = read(0, dst + got, n - got);
        if (r <= 0) break;
        got += (size_t)r;
    }
}

static int idx_ok(long i) { return i >= 0 && i < MAX; }

/* default handler: greet by name */
static void woof(struct dog *d)
{
    printf("%s says: woof!\n", d->name);
}

static void do_adopt(void)
{
    printf("kennel (0-%d): ", MAX - 1); flush();
    long i = read_long();
    if (!idx_ok(i)) { puts("bad kennel"); return; }
    if (dogs[i]) { puts("kennel occupied"); return; }

    struct dog *d = malloc(sizeof(*d));
    if (!d) { puts("no room"); return; }
    d->bark = woof;
    printf("name: "); flush();
    read_n(d->name, NAMELEN);
    d->name[NAMELEN - 1] = '\0';
    dogs[i] = d;
    printf("adopted a good dog in kennel %ld\n", i);
}

static void do_command(void)
{
    printf("kennel: "); flush();
    long i = read_long();
    if (!idx_ok(i) || !dogs[i]) { puts("empty kennel"); return; }
    dogs[i]->bark(dogs[i]);        /* UAF: pointer may be dangling */
}

static void do_release(void)
{
    printf("kennel: "); flush();
    long i = read_long();
    if (!idx_ok(i) || !dogs[i]) { puts("empty kennel"); return; }
    free(dogs[i]);                 /* BUG: slot pointer left dangling */
    puts("dog released to the wild");
}

static void do_add_note(void)
{
    printf("note slot (0-%d): ", MAX - 1); flush();
    long i = read_long();
    if (!idx_ok(i)) { puts("bad slot"); return; }
    if (notes[i]) { puts("slot occupied"); return; }

    printf("size: "); flush();
    long sz = read_long();
    if (sz <= 0 || sz > MAX_NOTE) { puts("bad size"); return; }

    char *p = malloc((size_t)sz);
    if (!p) { puts("no room"); return; }
    printf("contents: "); flush();
    read_n(p, (size_t)sz);
    notes[i] = p;
    note_sz[i] = (size_t)sz;
    printf("note filed in slot %ld\n", i);
}

static void do_show_note(void)
{
    printf("note slot: "); flush();
    long i = read_long();
    if (!idx_ok(i) || !notes[i]) { puts("no note"); return; }
    printf("contents: ");
    write(1, notes[i], note_sz[i]);   /* read-after-free possible */
    puts("");
}

static void do_free_note(void)
{
    printf("note slot: "); flush();
    long i = read_long();
    if (!idx_ok(i) || !notes[i]) { puts("no note"); return; }
    free(notes[i]);                   /* left dangling too */
    puts("note shredded");
}

static void menu(void)
{
    puts("");
    puts("=== K-9 Unit Manager ===");
    puts("1) adopt dog");
    puts("2) command dog");
    puts("3) release dog");
    puts("4) file note");
    puts("5) read note");
    puts("6) shred note");
    puts("7) go home");
    printf("> "); flush();
}

int main(void)
{
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);

    for (;;) {
        menu();
        switch (read_long()) {
        case 1: do_adopt();     break;
        case 2: do_command();   break;
        case 3: do_release();   break;
        case 4: do_add_note();  break;
        case 5: do_show_note(); break;
        case 6: do_free_note(); break;
        case 7: puts("good boy."); return 0;
        default: puts("?");
        }
    }
}
