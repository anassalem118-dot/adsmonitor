"""
core/security.py
----------------
- تشفير التوكنات (Meta + Telegram) قبل ما تنحفظ في القاعدة (Fernet).
- تشفير كلمات المرور (bcrypt).
مفتاح التشفير (SECRET_KEY) لازم يكون نفسه في Streamlit وفي GitHub.
"""
from functools import lru_cache

import bcrypt
from cryptography.fernet import Fernet

from .config import secret


class MissingSecret(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = secret("SECRET_KEY")
    if not key:
        raise MissingSecret("SECRET_KEY")
    return Fernet(key.encode())


def new_key() -> str:
    return Fernet.generate_key().decode()


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False
