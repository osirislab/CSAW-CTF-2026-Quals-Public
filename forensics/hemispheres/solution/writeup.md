# Hemispheres — Writeup

**Flag:** `csaw{0n3_f1l3_tw0_truth5_p0lygl0t_m4g1c}`
**Archive password (hidden in the pixels):** `r3ad_b3tw33n_th3_p1x3ls`

## The idea

`the_signal.png` is a **polyglot**: one byte stream that is simultaneously a
valid **PNG** and a valid **ZIP**, because the two formats are parsed from
opposite ends of the file:

- **PNG** is read front-to-back: the 8-byte signature, then chunks ending at
  `IEND`. Anything after `IEND` is ignored by image decoders.
- **ZIP** is read back-to-front: a reader scans from EOF for the *End of
  Central Directory* (EOCD) record, then follows offsets to the entries.

So `valid PNG ++ valid ZIP` satisfies both readers at once.

**But this time the archive is encrypted**, and the password is *not* written
anywhere as text — it is steganographically hidden in the **least-significant
bits of the image's blue channel**. That kills the one-liner solve.

## Why `binwalk`/`unzip` alone is not enough

```
$ unzip the_signal.png
warning: ... extra bytes at beginning or within zipfile ...
   skipping: flag.txt                need PK compat. v2.0 (can do v4.6)
[the_signal.png] flag.txt password:
```

The archive is found, but `flag.txt` is encrypted. `binwalk -e` carves the
same encrypted entry. Without the password you get nothing — and the password
appears in no string, no metadata, no comment.

## Finding the key

The PNG `Comment` chunk nudges you: *"The key is in the pixels, not the
words."* Read the LSB of the blue channel of each pixel in row-major order:

- first **16 bits** = a big-endian length `N`,
- next `N * 8` bits = the password bytes.

That yields `r3ad_b3tw33n_th3_p1x3ls`.

## Solving

```
$ python3 solve.py
[+] PNG signature present: True
[+] LSB password recovered: r3ad_b3tw33n_th3_p1x3ls
[+] archive entries: ['flag.txt', 'README.txt']
FLAG: csaw{0n3_f1l3_tw0_truth5_p0lygl0t_m4g1c}
```

Equivalently, by hand: extract the LSB password with any stego tool (or a few
lines of Pillow), then `unzip -P r3ad_b3tw33n_th3_p1x3ls the_signal.png`.

## Regenerating

```
python3 generate.py    # builds the image, embeds the LSB password, appends the
                       # encrypted ZIP, and verifies EVERY view (PNG, LSB, ZIP)
```

The generator renders the image with Pillow, hides the password in the pixel
LSBs, builds a traditional-ZipCrypto encrypted archive in memory (pure
standard library — so `zipfile` can read it back with a password), and
concatenates `PNG || ZIP`.
