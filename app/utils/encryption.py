from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

_NONCE_SIZE = 12


def _derive_key(secret_key: str) -> bytes:
    return hashlib.sha256(secret_key.encode("utf-8")).digest()


def encrypt_string(value: str, secret_key: str | None = None) -> str:
    key = _derive_key(secret_key or settings.secret_key)
    nonce = os.urandom(_NONCE_SIZE)
    encrypted = AESGCM(key).encrypt(nonce, value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")


def decrypt_string(token: str, secret_key: str | None = None) -> str:
    key = _derive_key(secret_key or settings.secret_key)
    payload = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce = payload[:_NONCE_SIZE]
    encrypted = payload[_NONCE_SIZE:]
    decrypted = AESGCM(key).decrypt(nonce, encrypted, None)
    return decrypted.decode("utf-8")
