# Diamond Dogs - DEPLOY image (glibc 2.31). Build from the challenge root:
#   docker build -f Dockerfile -t guard-dog .
# Do NOT ship this file or ../flag.txt to players.
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m ctf
WORKDIR /home/ctf
COPY files/guard-dog files/libc-2.31.so files/ld-2.31.so ./
COPY flag.txt ./
RUN chmod +x ./guard-dog ./ld-2.31.so && \
    chown -R root:root /home/ctf && chmod 0644 flag.txt
USER ctf
EXPOSE 1025
CMD ["socat", "-T60", "TCP-LISTEN:1025,reuseaddr,fork", "EXEC:./guard-dog,stderr"]
