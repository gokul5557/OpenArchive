import hashlib
import hmac
try:
    from config import settings
except ImportError:
    from core.config import settings

SECRET_KEY = settings.SYSTEM_SECRET
# System-level secret for HMAC signing (In production, use KMS or Environment Secret)
SYSTEM_SECRET = settings.SYSTEM_SECRET.encode()

def calculate_hash(data: bytes) -> str:
    """Returns the SHA-256 hash of the data."""
    return hashlib.sha256(data).hexdigest()

def sign_data(data: bytes) -> str:
    """Generates an HMAC-SHA256 signature for the data."""
    h = hmac.new(SYSTEM_SECRET, data, hashlib.sha256)
    return h.hexdigest()

def verify_integrity(data: bytes, signature: str) -> bool:
    """Verifies if the provided signature matches the data."""
    expected = sign_data(data)
    return hmac.compare_digest(expected, signature)
