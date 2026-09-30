FROM ubuntu:22.04 AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        make \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY src/vespers.c /build/vespers.c

RUN gcc -O2 -fstack-protector-all -D_FORTIFY_SOURCE=2 \
        -Wl,-z,relro,-z,now -pie -fPIE \
        -o /build/vespers /build/vespers.c \
    && strip /build/vespers

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        socat \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -d /home/vespers -s /usr/sbin/nologin vespers

WORKDIR /home/vespers
COPY --from=build /build/vespers /home/vespers/vespers
COPY build/flag.txt /home/vespers/flag.txt
RUN chmod 555 /home/vespers/vespers && \
    chown root:root /home/vespers/flag.txt && \
    chmod 444 /home/vespers/flag.txt

EXPOSE 5000
USER vespers
CMD ["socat", "-T30", "TCP-LISTEN:5000,reuseaddr,fork", "EXEC:/home/vespers/vespers,stderr"]
