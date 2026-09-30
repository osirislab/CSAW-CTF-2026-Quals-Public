# Saint Vespers and the Copper Choir
#
# `make`          - build the release binary into dist/ and patch it to the
#                   shipped glibc 2.35 loader (matches the Docker runtime).
# `make debug`    - build an unstripped copy for local gdb work.
# `make handout`  - assemble the player-facing handout archive (NO flag).
# `make docker`   - build the challenge container image.
# `make run`      - build + run the container locally on :5000.
# `make test`     - run the solve script against a fresh local instance.
# `make clean`    - remove build artifacts.

CHALL      := saint-vespers-and-the-copper-choir
SRC        := src/vespers.c
DIST       := dist
HANDOUT    := handout
BIN        := $(DIST)/vespers

CFLAGS     := -O2 -fstack-protector-all -D_FORTIFY_SOURCE=2 \
              -Wl,-z,relro,-z,now -pie -fPIE
LOADER     := $(DIST)/ld-2.35.so
LIBC       := $(DIST)/libc.so.6

.PHONY: all debug handout docker run test clean

all: $(BIN)

$(BIN): $(SRC) $(LOADER) $(LIBC)
	gcc $(CFLAGS) -o $(BIN) $(SRC)
	strip $(BIN)
	patchelf --set-interpreter ./ld-2.35.so --set-rpath '$$ORIGIN' $(BIN)
	@echo "[*] built $(BIN)"

debug: $(SRC)
	gcc -O0 -g -fstack-protector-all -D_FORTIFY_SOURCE=2 \
	    -Wl,-z,relro,-z,now -pie -fPIE -o $(DIST)/vespers_debug $(SRC)
	@echo "[*] built $(DIST)/vespers_debug (unstripped)"

# Player handout: binary + the exact libc/loader + source. Never the flag.
handout: all
	rm -rf $(HANDOUT)
	mkdir -p $(HANDOUT)
	cp $(BIN) $(LIBC) $(LOADER) $(HANDOUT)/
	cp $(SRC) $(HANDOUT)/vespers.c
	cd $(HANDOUT) && tar czf ../$(CHALL)-handout.tar.gz *
	@echo "[*] wrote $(CHALL)-handout.tar.gz"

docker:
	docker build -f build/Dockerfile -t $(CHALL) .

run: docker
	docker run --rm -it -p 5000:5000 --name vespers-local $(CHALL)

test: all
	python3 solve/solve.py

clean:
	rm -rf $(HANDOUT) $(CHALL)-handout.tar.gz $(DIST)/vespers_debug
	@echo "[*] cleaned"
