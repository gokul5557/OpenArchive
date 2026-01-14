import os
import base64
from cryptography.fernet import Fernet

def generate_key() -> bytes:
    """Generates a new Fernet key."""
    return Fernet.generate_key()

def encrypt_data(data: bytes, key: bytes) -> bytes:
    """Encrypts bytes using the provided key."""
    f = Fernet(key)
    return f.encrypt(data)

def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """Decrypts bytes using the provided key."""
    f = Fernet(key)
    return f.decrypt(encrypted_data)
