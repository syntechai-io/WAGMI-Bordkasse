import hashlib
import hmac
import secrets


def generate_reset_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    computed = hash_token(raw_token)
    return hmac.compare_digest(computed, stored_hash)
