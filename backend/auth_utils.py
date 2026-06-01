import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed or not plain:
        return False
    try:
        scheme, salt, digest = hashed.split("$", 2)
        if scheme != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
        return secrets.compare_digest(check.hex(), digest)
    except ValueError:
        return False
