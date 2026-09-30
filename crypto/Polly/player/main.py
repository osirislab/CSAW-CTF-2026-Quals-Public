# Please note that something like 20% of instances can not be solved client side. There wasn't a way to make it 100% without making the solve too obvious
# instances will have modified code to make every instance solvable. Sorry for any inconvenience. 
import os
import secrets
import sys
from hashlib import shake_256

from Crypto.Cipher import ChaCha20

key = os.urandom(32)
base_nonce = os.urandom(9)
seed = secrets.randbits(64)
while seed == 0:
    seed = secrets.randbits(64)

flag = os.environ["FLAG"]
flag_bytes = flag.encode("utf-8")

MASK64 = (1 << 64) - 1
MAX_PLAINTEXT_BYTES = 4096
MAX_X_INPUT_BYTES = 20

shifts = []
material = shake_256(base_nonce).digest(5)

available_shifts = list(range(1, 64))
for byte in material[1:]:
    index = byte % len(available_shifts)
    shifts.append(available_shifts.pop(index))
num = material[0] & 1


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


flag_x = secrets.randbits(64)
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
