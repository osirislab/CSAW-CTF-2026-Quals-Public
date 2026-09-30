# Ghost in the Machine

**Category:** Forensics / Networking
**Difficulty:** Hard
**Flag format:** `csaw{...}`

---

We intercepted a host quietly beaconing out of a locked-down network. The
firewall logs every byte that leaves — and every byte here is boring. Same
source, same destination, the same little `PING` payload, over and over.

And yet something is getting out. It's buried in the noise, it's scrambled,
and the operator left just enough on the wire to unscramble it — if you know
which columns to trust.

Find the message.

## Files

- `capture.pcap` — 504 packets. Open it in Wireshark, or parse it yourself.

## Hint

Look at the columns you usually ignore. Not every packet is telling the
truth — some are just there to throw off your averages. And once you read the
signal, it still won't look like a flag until you find what it was mixed with
(the sender left the key hiding in plain sight, in another column you skipped).
