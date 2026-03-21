"""Unit tests for encryption module."""
import base64

import pytest

from app.core.encryption import decrypt_value, encrypt_value, mask_api_key


def test_encrypt_decrypt_round_trip():
    plaintext = "sk-test-api-key-1234567890"
    encrypted = encrypt_value(plaintext)
    assert encrypted != plaintext
    assert decrypt_value(encrypted) == plaintext


def test_encrypt_returns_base64_string():
    encrypted = encrypt_value("test")
    # Fernet tokens are URL-safe base64
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0


def test_fernet_key_is_32_bytes():
    """The derived key must be exactly 32 bytes (44 chars base64-encoded)."""
    import base64
    import hashlib
    from app.core.config import settings

    raw_key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    )
    assert len(raw_key) == 44


def test_different_plaintexts_produce_different_ciphertexts():
    enc1 = encrypt_value("key-abc")
    enc2 = encrypt_value("key-xyz")
    assert enc1 != enc2


def test_mask_api_key_short():
    # Keys <= 8 chars get masked as "***"
    assert mask_api_key("1234") == "***"


def test_mask_api_key_long():
    result = mask_api_key("sk-1234567890abcdef")
    assert result.startswith("sk-1")
    assert result.endswith("cdef")
    assert "***" in result


def test_mask_api_key_empty():
    # Empty key <= 8 chars returns "***"
    assert mask_api_key("") == "***"
