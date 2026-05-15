"""Chiffrement Fernet pour les tokens OAuth."""
from cryptography.fernet import Fernet
from core.config import settings
from functools import lru_cache


@lru_cache
def _fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # Génère une clé de dev — en prod, toujours définir ENCRYPTION_KEY
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
