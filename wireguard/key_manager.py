import base64
import os
import subprocess
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def _get_encryption_key() -> bytes:
    raw = settings.SECRET_KEY.encode('utf-8')
    return (raw * 2)[:32]


def encrypt(plaintext: str) -> str:
    aesgcm    = AESGCM(_get_encryption_key())
    nonce     = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + encrypted).decode()


def decrypt(encrypted_text: str) -> str:
    aesgcm     = AESGCM(_get_encryption_key())
    data       = base64.b64decode(encrypted_text.encode())
    nonce      = data[:12]
    ciphertext = data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


def generate_private_key() -> str:
    """
    Generate a WireGuard private key.
    Uses the wg command if available (on Linux/GCP server),
    falls back to pure Python using the cryptography library
    (works on Windows for development).
    """
    try:
        result = subprocess.run(
            ['wg', 'genkey'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Pure Python fallback using Curve25519
        private_key = X25519PrivateKey.generate()
        raw_bytes   = private_key.private_bytes(
            encoding=Encoding.Raw,
            format=PrivateFormat.Raw,
            encryption_algorithm=NoEncryption()
        )
        return base64.b64encode(raw_bytes).decode()


def derive_public_key(private_key_b64: str) -> str:
    """
    Derive the WireGuard public key from a private key.
    Uses wg command if available, falls back to pure Python.
    """
    try:
        result = subprocess.run(
            ['wg', 'pubkey'],
            input=private_key_b64,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Pure Python fallback
        raw_bytes   = base64.b64decode(private_key_b64)
        private_key = X25519PrivateKey.from_private_bytes(raw_bytes)
        public_key  = private_key.public_key()
        raw_public  = public_key.public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw
        )
        return base64.b64encode(raw_public).decode()


def generate_preshared_key() -> str:
    """
    Generate a WireGuard preshared key.
    Uses wg command if available, falls back to pure Python.
    """
    try:
        result = subprocess.run(
            ['wg', 'genpsk'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # A preshared key is just 32 random bytes base64 encoded
        return base64.b64encode(os.urandom(32)).decode()


def generate_keypair() -> dict:
    """
    Generate a complete WireGuard keypair plus a preshared key.
    Returns plain text keys — always encrypt before saving to DB.
    """
    private_key   = generate_private_key()
    public_key    = derive_public_key(private_key)
    preshared_key = generate_preshared_key()

    return {
        'private_key':   private_key,
        'public_key':    public_key,
        'preshared_key': preshared_key,
    }