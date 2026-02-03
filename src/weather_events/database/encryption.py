"""Encryption utilities for sensitive data.

Uses Fernet symmetric encryption for storing sensitive data like OAuth tokens.

## Security Model

1. A master encryption key is derived from the application secret
2. Each sensitive field is encrypted with Fernet before storage
3. Keys can be rotated by re-encrypting all data with a new key

## Key Derivation

The encryption key is derived from the application secret using PBKDF2:
- Salt: Configurable, should be unique per deployment
- Iterations: 480,000 (OWASP recommendation for PBKDF2-HMAC-SHA256)
- Key length: 32 bytes (256 bits)

## Usage

```python
from weather_events.database.encryption import encrypt_token, decrypt_token

# Encrypt before storing
encrypted = encrypt_token("my-oauth-token")
# Store encrypted in database

# Decrypt after retrieving
decrypted = decrypt_token(encrypted)
```
"""

from __future__ import annotations

import base64
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Module-level cipher instance (initialized on first use)
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get or create the Fernet cipher instance."""
    global _fernet

    if _fernet is None:
        from weather_events.config import get_settings

        settings = get_settings()
        _fernet = _create_fernet(
            settings.secret_key,
            settings.encryption_salt,
        )

    return _fernet


def _create_fernet(secret_key: str, salt: str) -> Fernet:
    """Create a Fernet cipher from the secret key and salt.

    Uses PBKDF2 to derive a proper encryption key from the secret.

    Args:
        secret_key: Application secret key
        salt: Unique salt for this deployment

    Returns:
        Configured Fernet cipher
    """
    # Derive a proper encryption key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for Fernet
        salt=salt.encode("utf-8"),
        iterations=480_000,  # OWASP recommendation
    )

    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode("utf-8")))
    return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token for secure storage.

    Args:
        plaintext: The token to encrypt

    Returns:
        Base64-encoded encrypted token
    """
    if not plaintext:
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored token.

    Args:
        ciphertext: The encrypted token (base64-encoded)

    Returns:
        Decrypted plaintext token

    Raises:
        ValueError: If decryption fails (invalid token or wrong key)
    """
    if not ciphertext:
        return ""

    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as e:
        logger.error("Failed to decrypt token: invalid token or key")
        raise ValueError("Failed to decrypt token") from e


def rotate_encryption_key(
    old_secret: str,
    old_salt: str,
    new_secret: str,
    new_salt: str,
    ciphertext: str,
) -> str:
    """Re-encrypt data with a new key.

    Used during key rotation to migrate encrypted data.

    Args:
        old_secret: Previous secret key
        old_salt: Previous salt
        new_secret: New secret key
        new_salt: New salt
        ciphertext: Data encrypted with old key

    Returns:
        Data encrypted with new key
    """
    if not ciphertext:
        return ""

    # Decrypt with old key
    old_fernet = _create_fernet(old_secret, old_salt)
    try:
        plaintext = old_fernet.decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as e:
        raise ValueError("Failed to decrypt with old key") from e

    # Encrypt with new key
    new_fernet = _create_fernet(new_secret, new_salt)
    encrypted = new_fernet.encrypt(plaintext)
    return encrypted.decode("utf-8")


def reset_cipher() -> None:
    """Reset the cached cipher instance.

    Call this if the configuration changes (e.g., in tests).
    """
    global _fernet
    _fernet = None
