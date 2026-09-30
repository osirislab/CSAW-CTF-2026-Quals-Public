import os
from hashlib import shake_256

from pwn import context, remote


HOST = os.environ.get("HOST", "localhost")
PORT = int(os.environ.get("PORT", "5000"))

MASK64 = (1 << 64) - 1
MAX_OBSERVATIONS = 64
MAX_ATTEMPTS = 10
MAX_SEARCH_STEPS = 1 << 28

context.log_level = os.environ.get("LOG_LEVEL", "error")


def transform(state, shifts, direction):
    if direction == 0:
        state ^= (state << shifts[0]) & MASK64
        state ^= state >> shifts[1]
        state ^= (state << shifts[2]) & MASK64
        state ^= state >> shifts[3]
    else:
        state ^= state >> shifts[0]
        state ^= (state << shifts[1]) & MASK64
        state ^= state >> shifts[2]
        state ^= (state << shifts[3]) & MASK64

    return state & MASK64


def parameters_from_nonce(nonce_bytes):
    base_nonce = nonce_bytes[:9]
    material = shake_256(base_nonce).digest(5)
    available_shifts = list(range(1, 64))
    shifts = []

    for byte in material[1:]:
        index = byte % len(available_shifts)
        shifts.append(available_shifts.pop(index))

    return shifts, material[0] & 1


def read_instance(conn):
    conn.recvuntil(b"is ")
    encrypted_flag = bytes.fromhex(conn.recvuntil(b",", drop=True).decode())
    conn.recvuntil(b"is ")
    nonce = bytes.fromhex(conn.recvuntil(b" ", drop=True).decode())
    return encrypted_flag, nonce


def query_nonce_byte(conn, x):
    conn.recvuntil(b"use?\n")
    conn.sendline(str(x).encode())
    conn.recvuntil(b": ")
    conn.sendline(b"")
    conn.recvuntil(b": ")
    conn.recvuntil(b" \n", drop=True)  # ciphertext is not needed yet
    conn.recvuntil(b": ")
    return int(conn.recvuntil(b" \n", drop=True), 16)


def add_to_basis(row, basis):
    """Add a 64-bit coefficient row to an incremental GF(2) basis."""
    while row:
        pivot = row.bit_length() - 1
        if pivot not in basis:
            basis[pivot] = row
            return True
        row ^= basis[pivot]
    return False


def recover_seed(equations):
    """Solve coefficient/RHS equations over GF(2)."""
    rows = [coefficient | (answer << 64) for coefficient, answer in equations]
    pivot_row = 0

    for seed_bit in range(64):
        row_with_pivot = next(
            (row for row in range(pivot_row, len(rows)) if rows[row] & (1 << seed_bit)),
            None,
        )
        if row_with_pivot is None:
            continue

        rows[pivot_row], rows[row_with_pivot] = rows[row_with_pivot], rows[pivot_row]

        for row in range(len(rows)):
            if row != pivot_row and rows[row] & (1 << seed_bit):
                rows[row] ^= rows[pivot_row]

        pivot_row += 1

    if pivot_row != 64:
        return None

    seed = 0
    for seed_bit in range(64):
        seed |= ((rows[seed_bit] >> 64) & 1) << seed_bit
    return seed


def recover_seed_from_oracle(conn, shifts, direction):
    equations = []
    basis = {}
    # columns[i] is T**x applied to a seed containing only bit i.
    columns = [1 << seed_bit for seed_bit in range(64)]

    for x in range(MAX_OBSERVATIONS):
        leaked_byte = query_nonce_byte(conn, x)

        for output_bit in range(8):
            coefficient = 0
            for seed_bit, column in enumerate(columns):
                coefficient |= ((column >> output_bit) & 1) << seed_bit

            equations.append((coefficient, (leaked_byte >> output_bit) & 1))
            add_to_basis(coefficient, basis)

        if len(basis) == 64:
            return recover_seed(equations), x + 1

        columns = [transform(column, shifts, direction) for column in columns]

    return None, MAX_OBSERVATIONS


def state_after(state, count, shifts, direction):
    for _ in range(count):
        state = transform(state, shifts, direction)
    return state


def validate_seed(conn, seed, x, shifts, direction):
    expected = state_after(seed, x, shifts, direction) & 0xFF
    return query_nonce_byte(conn, x) == expected


def find_matching_x(seed, target_suffix, shifts, direction):
    state = seed
    for x in range(MAX_SEARCH_STEPS):
        if state & 0xFFFFFF == target_suffix:
            return x
        state = transform(state, shifts, direction)
    return None


def recover_flag(conn, encrypted_flag, x):
    conn.recvuntil(b"use?\n")
    conn.sendline(str(x).encode())
    conn.recvuntil(b": ")
    conn.sendline(b"")
    conn.recvuntil(b": ")
    known_ciphertext = bytes.fromhex(conn.recvuntil(b" \n", drop=True).decode())
    return bytes(a ^ b for a, b in zip(encrypted_flag, known_ciphertext))


def solve_attempt(attempt):
    conn = remote(HOST, PORT)
    try:
        encrypted_flag, nonce = read_instance(conn)
        shifts, direction = parameters_from_nonce(nonce)
        target_suffix = int.from_bytes(nonce[9:], "big")

        seed, observations = recover_seed_from_oracle(conn, shifts, direction)
        if seed is None:
            print(
                f"Attempt {attempt}: rank stayed below 64 after "
                f"{observations} observations; reconnecting."
            )
            return None

        # This response was not used to recover the seed, so it catches equation
        # or parsing mistakes before the expensive suffix search begins.
        if not validate_seed(conn, seed, observations, shifts, direction):
            print(f"Attempt {attempt}: recovered seed failed validation; reconnecting.")
            return None

        print(
            f"Attempt {attempt}: recovered and validated the seed with "
            f"{observations} observations."
        )
        x = find_matching_x(seed, target_suffix, shifts, direction)
        if x is None:
            print(
                f"Attempt {attempt}: no matching suffix in {MAX_SEARCH_STEPS} steps; "
                "reconnecting."
            )
            return None

        flag = recover_flag(conn, encrypted_flag, x)
        print(f"Matching x: {x}")
        print(f"Flag: {flag.decode()}")
        return flag
    finally:
        conn.close()


def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if solve_attempt(attempt) is not None:
                return
        except (EOFError, OSError, ValueError, UnicodeDecodeError) as error:
            print(f"Attempt {attempt}: {error}; reconnecting.")

    raise RuntimeError(f"Failed to solve after {MAX_ATTEMPTS} fresh instances")


if __name__ == "__main__":
    main()
