# Hells Bells - local reproduction image (glibc 2.31)
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m ctf
WORKDIR /home/ctf
COPY thermite-charge libc-2.31.so ld-2.31.so flag.txt ./
RUN chmod +x ./thermite-charge ./ld-2.31.so && \
    chown -R root:root /home/ctf && chmod 0644 flag.txt
USER ctf
EXPOSE 1024
CMD ["socat", "-T60", "TCP-LISTEN:1024,reuseaddr,fork", "EXEC:./thermite-charge,stderr"]
