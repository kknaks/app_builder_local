"""Tests for AES-256 encryption/decryption."""

import pytest

from app.core.crypto import decrypt, encrypt


class TestCrypto:
    """AES-256-GCM encryption tests."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting should return the original text."""
        plaintext = "sk-ant-api03-test-key-12345"
        passphrase = "my-secret-passphrase-32b"

        encrypted = encrypt(plaintext, passphrase)
        decrypted = decrypt(encrypted, passphrase)

        assert decrypted == plaintext

    def test_encrypted_differs_from_plaintext(self):
        """Encrypted string should not contain the plaintext."""
        plaintext = "sk-ant-api03-test-key-12345"
        passphrase = "my-secret-passphrase-32b"

        encrypted = encrypt(plaintext, passphrase)
        assert encrypted != plaintext
        assert "sk-ant" not in encrypted

    def test_different_passphrases_produce_different_output(self):
        """Different passphrases should produce different ciphertexts."""
        plaintext = "sk-ant-api03-test-key-12345"

        encrypted1 = encrypt(plaintext, "passphrase-one-32bytes-long-xxx")
        encrypted2 = encrypt(plaintext, "passphrase-two-32bytes-long-xxx")

        assert encrypted1 != encrypted2

    def test_same_plaintext_produces_different_ciphertext(self):
        """Due to random nonce, same input should produce different output each time."""
        plaintext = "sk-ant-api03-test-key-12345"
        passphrase = "my-secret-passphrase-32b"

        encrypted1 = encrypt(plaintext, passphrase)
        encrypted2 = encrypt(plaintext, passphrase)

        # Different nonces → different ciphertext
        assert encrypted1 != encrypted2

        # Both should decrypt correctly
        assert decrypt(encrypted1, passphrase) == plaintext
        assert decrypt(encrypted2, passphrase) == plaintext

    def test_wrong_passphrase_fails(self):
        """Decrypting with wrong passphrase should raise an error."""
        plaintext = "sk-ant-api03-test-key-12345"
        encrypted = encrypt(plaintext, "correct-passphrase-32b-long-xxx")

        with pytest.raises(Exception):
            decrypt(encrypted, "wrong-passphrase-32b-long-xxxxx")

    def test_empty_string_encryption(self):
        """Should handle empty string encryption."""
        passphrase = "my-secret-passphrase-32b"
        encrypted = encrypt("", passphrase)
        decrypted = decrypt(encrypted, passphrase)
        assert decrypted == ""

    def test_unicode_encryption(self):
        """Should handle unicode characters."""
        plaintext = "토큰-키-한글-테스트-🔑"
        passphrase = "my-secret-passphrase-32b"

        encrypted = encrypt(plaintext, passphrase)
        decrypted = decrypt(encrypted, passphrase)
        assert decrypted == plaintext

    def test_long_token_encryption(self):
        """Should handle long API tokens."""
        plaintext = "sk-ant-api03-" + "x" * 200
        passphrase = "my-secret-passphrase-32b"

        encrypted = encrypt(plaintext, passphrase)
        decrypted = decrypt(encrypted, passphrase)
        assert decrypted == plaintext
