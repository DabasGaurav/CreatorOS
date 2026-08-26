import pytest
from cryptography.fernet import Fernet

from creatoros.security import crypto


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto.get_settings.cache_clear()
    yield
    crypto.get_settings.cache_clear()


def test_encrypt_decrypt_roundtrip():
    plaintext = "IGQVJYc2xhbnRva2VuLXZlcnktbG9uZy1zZWNyZXQ"
    ciphertext = crypto.encrypt_token(plaintext)
    assert ciphertext != plaintext
    assert crypto.decrypt_token(ciphertext) == plaintext


def test_tampered_ciphertext_is_rejected():
    ciphertext = crypto.encrypt_token("some-long-lived-token")
    tampered = ciphertext[:-4] + ("A" * 4)
    with pytest.raises(crypto.TokenEncryptionError):
        crypto.decrypt_token(tampered)


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "")
    crypto.get_settings.cache_clear()
    with pytest.raises(crypto.TokenEncryptionError):
        crypto.encrypt_token("anything")
