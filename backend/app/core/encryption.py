import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings

# Derive a valid 32-byte URL-safe base64 Fernet key from SECRET_KEY
_fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
)
_fernet = Fernet(_fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string using Fernet symmetric encryption."""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def mask_api_key(key: str) -> str:
    """Return a masked version: first 4 chars + *** + last 4 chars."""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"
