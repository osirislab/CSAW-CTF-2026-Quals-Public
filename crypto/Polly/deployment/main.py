import os
import secrets
import sys
from hashlib import shake_256

from Crypto.Cipher import ChaCha20

key = os.urandom(32)
seed = secrets.randbits(64)
while seed == 0:
    seed = secrets.randbits(64)

flag = os.environ["FLAG"]
flag_bytes = flag.encode("utf-8")

MASK64 = (1 << 64) - 1
MAX_PLAINTEXT_BYTES = 4096
MAX_X_INPUT_BYTES = 20
MAX_OBSERVATIONS = 64
MAX_FLAG_X = 1 << 24


def make_shifts():
    base_nonce = os.urandom(9)
    material = shake_256(base_nonce).digest(5)
    shifts = []

    available_shifts = list(range(1, 64))
    for byte in material[1:]:
        index = byte % len(available_shifts)
        shifts.append(available_shifts.pop(index))

    num = material[0] & 1
    return base_nonce, shifts, num


def read_limited_line(prompt, max_bytes):
    print(prompt, end="", flush=True)
    line = sys.stdin.buffer.readline(max_bytes + 3)

    if not line:
        raise EOFError

    if not line.endswith(b"\n"):
        while line and not line.endswith(b"\n"):
            line = sys.stdin.buffer.readline(max_bytes + 3)
        return None

    value = line[:-1]
    if value.endswith(b"\r"):
        value = value[:-1]

    if len(value) > max_bytes:
        return None

    return value


def transform(state, num):

    if num % 2 == 0:
    
        state ^= (state << shifts[0]) & MASK64
        state ^= state >> shifts[1]
        state ^= (state << shifts[2]) & MASK64
        state ^= state >> shifts[3]

    else:

        state ^= (state >> shifts[0]) 
        state ^= (state << shifts[1])& MASK64
        state ^= (state >> shifts[2]) 
        state ^= (state << shifts[3]) & MASK64
        
    return state & MASK64


def seed_can_be_recovered():
    matrix = []
    states = []

    #start with a pretend seed that has one bit set for each column
    for seed_bit in range(64):
        single_bit_seed = 1 << seed_bit
        states.append(single_bit_seed)

    #build the rows that the solver would get from 64 leaked bytes
    for x in range(MAX_OBSERVATIONS):
        for output_bit in range(8):
            row = []

            for state in states:
                shifted_state = state >> output_bit
                coefficient = shifted_state & 1
                row.append(coefficient)

            matrix.append(row)

        next_states = []
        for state in states:
            next_states.append(transform(state, num))
        states = next_states

    #do gaussian elimination and see if all 64 seed bits get a pivot
    pivot_row = 0

    for seed_column in range(64):
        row_with_pivot = None

        for candidate_row in range(pivot_row, len(matrix)):
            if matrix[candidate_row][seed_column] == 1:
                row_with_pivot = candidate_row
                break

        if row_with_pivot == None:
            continue

        matrix[pivot_row], matrix[row_with_pivot] = (
            matrix[row_with_pivot],
            matrix[pivot_row]
        )

        for row in range(pivot_row + 1, len(matrix)):
            if matrix[row][seed_column] == 1:
                for column in range(seed_column, 64):
                    matrix[row][column] ^= matrix[pivot_row][column]

        pivot_row += 1

    return pivot_row == 64


#just keep making new shifts until the seed can actually be recovered
while True:
    base_nonce, shifts, num = make_shifts()

    if seed_can_be_recovered():
        break


def transformation(operator, state):
    result = 0

    for bit in range(64):
        if state & (1 << bit):
            result ^= operator[bit]

    return result & MASK64


def square_operator(operator):
    return [
        transformation(operator, column)
        for column in operator
    ]


def build_jump_table():
    first_jump = [
        transform(1 << bit,  num)
        for bit in range(64)
    ]

    jumps = [first_jump]

    for _ in range(63):
        jumps.append(square_operator(jumps[-1]))

    return jumps


JUMPS = build_jump_table()


def state_at(x, seed):
    if not 0 <= x <= MASK64:
        raise ValueError("x must be an unsigned 64-bit integer")

    state = seed & MASK64

    for bit in range(64):
        if x & (1 << bit):
            state = transformation(JUMPS[bit], state)

    return state


#this makes sure the solver will reach the exact nonce without searching forever
flag_x = secrets.randbelow(MAX_FLAG_X - 1) + 1
state = state_at(flag_x, seed)
nonce = base_nonce + (state & 0xFFFFFF).to_bytes(3, "big")

original_cipher = ChaCha20.new(key=key, nonce=nonce)
original_ciphertext = original_cipher.encrypt(flag_bytes)

print(
    f"The encrypted flag is {original_ciphertext.hex()}, the nonce is "
    f"{nonce.hex()} perhaps theirs a way to decrypt it??\n"
)

while True:
    try:
        x_input = read_limited_line(
            "which seed modifier would you like to use?\n",
            MAX_X_INPUT_BYTES,
        )
    except EOFError:
        break

    if x_input is None:
        print("x must be an unsigned 64-bit integer")
        continue

    try:
        x = int(x_input.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        print("x must be an unsigned 64-bit integer")
        continue

    if not 0 <= x <= MASK64:
        print("x must be an unsigned 64-bit integer")
        continue

    state = state_at(x, seed)
    nonce = base_nonce + (state & 0xFFFFFF).to_bytes(3, "big")

    try:
        plaintext = read_limited_line(
            "enter a string to be encrypted: ",
            MAX_PLAINTEXT_BYTES,
        )
    except EOFError:
        break

    if plaintext is None:
        print(f"plaintext must be at most {MAX_PLAINTEXT_BYTES} bytes")
        continue
    if len(plaintext) < len(flag_bytes):
        plaintext = plaintext.ljust(len(flag_bytes), b"\x00")
    cipher = ChaCha20.new(key=key, nonce=nonce)
    ciphertext = cipher.encrypt(plaintext)

    print(
        f"Your ciphertext is: {ciphertext.hex()} \n"
        f"Your nonce byte is: {nonce[-1:].hex()} \n"
    )
