from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64

# Master Key Management
# In production, this should come from a KMS (AWS KMS, dimaggio, Vault).
# For now, we derive a key from an Env Secret + Salt.

MASTER_SECRET = os.getenv("OPENARCHIVE_MASTER_KEY", "change-this-to-a-very-long-random-string-in-production")
SALT = b'openarchive_static_salt' # Should be random per file, but for simplicity/searchability in recovery, static.
# Actually, AESGCM requires a unique Nonce, not unique Key.
# We can use a static Master Key derived from Secret.

def get_master_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
    )
    return kdf.derive(MASTER_SECRET.encode())

KEY = get_master_key()
aesgcm = AESGCM(KEY)

def encrypt_data(data: bytes) -> bytes:
    """
    Encrypts data using AES-256-GCM.
    Returns: nonce + ciphertext
    """
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext

def decrypt_data(encrypted_data: bytes) -> bytes:
    """
    Decrypts data.
    Expects: nonce (12 bytes) + ciphertext
    """
    try:
        if len(encrypted_data) < 12:
            raise ValueError("Invalid Data")
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        print(f"Decryption Error: {e}")
        return None
