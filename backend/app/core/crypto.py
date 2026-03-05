"""AES-256 encryption/decryption utilities for API tokens."""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(passphrase: str) -> bytes:
    """Derive a 32-byte AES-256 key from a passphrase using SHA-256."""
    return hashlib.sha256(passphrase.encode("utf-8")).digest()


def encrypt(plaintext: str, passphrase: str) -> str:
    """Encrypt plaintext using AES-256-GCM.

    Returns a base64-encoded string containing nonce + ciphertext.
    """
    key = _derive_key(passphrase)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Concatenate nonce + ciphertext and base64-encode
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt(encrypted: str, passphrase: str) -> str:
    """Decrypt an AES-256-GCM encrypted string.

    Expects a base64-encoded string containing nonce (12 bytes) + ciphertext.
    """
    key = _derive_key(passphrase)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
