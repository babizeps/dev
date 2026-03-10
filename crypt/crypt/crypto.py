"""
Kryptographie-Kern: scrypt Key Derivation + AES-256-GCM Verschlüsselung
"""
import os
import json
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


SALT_SIZE = 32
NONCE_SIZE = 12
KEY_SIZE = 32  # AES-256


def derive_key(password: str, salt: bytes) -> bytes:
    """Leitet einen 256-bit Schlüssel aus dem Master-Passwort ab (scrypt)."""
    kdf = Scrypt(salt=salt, length=KEY_SIZE, n=2**17, r=8, p=1)
    return kdf.derive(password.encode())


def encrypt(data: dict, password: str) -> bytes:
    """Verschlüsselt ein dict als JSON mit AES-256-GCM."""
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt)

    plaintext = json.dumps(data).encode()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Format: salt + nonce + ciphertext, alles base64-kodiert
    payload = base64.b64encode(salt + nonce + ciphertext)
    return payload


def decrypt(payload: bytes, password: str) -> dict:
    """Entschlüsselt den Vault. Wirft ValueError bei falschem Passwort."""
    raw = base64.b64decode(payload)
    salt = raw[:SALT_SIZE]
    nonce = raw[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = raw[SALT_SIZE + NONCE_SIZE:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Falsches Master-Passwort oder Vault beschädigt.")

    return json.loads(plaintext)
