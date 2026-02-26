"""
encryption.py – Fernet symmetric encryption helpers for PII fields.

Design:
  - Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library.
  - The key is read from Django settings (FERNET_KEY) which is itself sourced
    from the FERNET_KEY environment variable, keeping it out of source control.
  - Ciphertext is stored in the database as a base64-encoded string so it fits
    cleanly into a TEXT/VARCHAR column without binary escaping issues.

Generate a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import base64

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def get_fernet() -> Fernet:
    """Return a Fernet instance built from settings.FERNET_KEY.

    Raises ValueError if the key is absent or empty so misconfiguration
    is caught immediately rather than silently storing plaintext.
    """
    key: str = getattr(settings, "FERNET_KEY", "")
    if not key:
        raise ValueError(
            "FERNET_KEY is not set in Django settings. "
            "Add it to your .env file and restart the server."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_bytes(plaintext: str) -> bytes:
    """Encrypt *plaintext* and return the raw Fernet token (bytes)."""
    fernet = get_fernet()
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_bytes(token: bytes) -> str:
    """Decrypt a raw Fernet *token* and return the original string.

    Raises cryptography.fernet.InvalidToken if the token is malformed
    or the key has changed.
    """
    fernet = get_fernet()
    return fernet.decrypt(token).decode("utf-8")


def encrypt_to_db(plaintext: str) -> str:
    """Encrypt and base64-encode for DB storage; returns a str."""
    raw_token = encrypt_bytes(plaintext)
    return base64.b64encode(raw_token).decode("ascii")


def decrypt_from_db(db_value: str) -> str:
    """Decode base64 from DB then decrypt; returns the original str."""
    raw_token = base64.b64decode(db_value.encode("ascii"))
    return decrypt_bytes(raw_token)
