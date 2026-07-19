from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher


# configure one bcrypt manager and reuse it for every password operation
PASSWORD_MANAGER = PasswordHash((BcryptHasher(),))


def hash_password(password: str) -> str:
    """
    create a salted bcrypt hash for a plain password
    """

    # only the returned hash is stored in sqlite
    return PASSWORD_MANAGER.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    compare a plain password with a stored bcrypt hash
    """

    try:
        # pwdlib performs the bcrypt comparison without exposing the hash data
        return PASSWORD_MANAGER.verify(
            password,
            password_hash,
        )
    except Exception:
        # malformed hashes are rejected like incorrect passwords
        return False
