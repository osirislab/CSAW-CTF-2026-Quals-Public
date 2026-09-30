import secrets
import string


def generate_storage_key():
    return "".join(secrets.choice(string.digits) for _ in range(20))


def xor_with_repeating_key(data, recovery_key):
    if not recovery_key:
        raise ValueError("recovery_key is required")

    key_bytes = recovery_key.encode()
    return bytes(
        byte ^ key_bytes[index % len(key_bytes)]
        for index, byte in enumerate(data)
    )


def encrypt_password(plaintext_password, recovery_key):
    encrypted = xor_with_repeating_key(plaintext_password.encode(), recovery_key)
    return encrypted.hex()
