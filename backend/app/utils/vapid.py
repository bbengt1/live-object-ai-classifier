"""
VAPID key management utilities for Web Push notifications (Story P4-1.1)

VAPID (Voluntary Application Server Identification) is used to identify
the application server sending push notifications to browsers.
"""
import base64
import logging
from typing import Tuple, Optional
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization
from sqlalchemy.orm import Session

from app.models.system_setting import SystemSetting
from app.utils.encryption import encrypt_password, decrypt_password, is_encrypted

logger = logging.getLogger(__name__)

# Settings keys for VAPID
VAPID_PRIVATE_KEY_SETTING = "vapid_private_key"
VAPID_PUBLIC_KEY_SETTING = "vapid_public_key"


def generate_vapid_keys() -> Tuple[str, str]:
    """
    Generate a new VAPID key pair.

    Returns:
        Tuple of (private_key_pem, public_key_urlsafe_base64)

    The private key is returned in PEM format for storage.
    The public key is returned in URL-safe base64 format for the frontend.
    """
    vapid = Vapid()
    vapid.generate_keys()

    # Get private key in PEM format
    private_key_pem = vapid.private_pem().decode('utf-8')

    # Get public key in URL-safe base64 format (applicationServerKey for frontend)
    # Extract uncompressed point format and encode as URL-safe base64
    public_key_bytes = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

    logger.info("Generated new VAPID key pair")
    return private_key_pem, public_key_b64


def get_vapid_keys(db: Session) -> Tuple[Optional[str], Optional[str]]:
    """
    Get VAPID keys from database settings.

    Args:
        db: Database session

    Returns:
        Tuple of (private_key_pem, public_key_b64) or (None, None) if not set
    """
    private_setting = db.query(SystemSetting).filter(
        SystemSetting.key == VAPID_PRIVATE_KEY_SETTING
    ).first()

    public_setting = db.query(SystemSetting).filter(
        SystemSetting.key == VAPID_PUBLIC_KEY_SETTING
    ).first()

    if not private_setting or not public_setting:
        return None, None

    # Decrypt private key if encrypted
    private_key = private_setting.value
    if is_encrypted(private_key):
        try:
            private_key = decrypt_password(private_key)
        except ValueError:
            logger.error("Failed to decrypt VAPID private key")
            return None, None

    return private_key, public_setting.value


def save_vapid_keys(db: Session, private_key: str, public_key: str) -> None:
    """
    Save VAPID keys to database settings.

    The private key is encrypted before storage.

    Args:
        db: Database session
        private_key: Private key in PEM format
        public_key: Public key in URL-safe base64 format
    """
    # Encrypt private key
    encrypted_private = encrypt_password(private_key)

    # Save or update private key
    private_setting = db.query(SystemSetting).filter(
        SystemSetting.key == VAPID_PRIVATE_KEY_SETTING
    ).first()

    if private_setting:
        private_setting.value = encrypted_private
    else:
        private_setting = SystemSetting(
            key=VAPID_PRIVATE_KEY_SETTING,
            value=encrypted_private
        )
        db.add(private_setting)

    # Save or update public key (not encrypted - exposed to frontend)
    public_setting = db.query(SystemSetting).filter(
        SystemSetting.key == VAPID_PUBLIC_KEY_SETTING
    ).first()

    if public_setting:
        public_setting.value = public_key
    else:
        public_setting = SystemSetting(
            key=VAPID_PUBLIC_KEY_SETTING,
            value=public_key
        )
        db.add(public_setting)

    db.commit()
    logger.info("VAPID keys saved to database")


def ensure_vapid_keys(db: Session) -> Tuple[str, str]:
    """
    Ensure VAPID keys exist, generating them if necessary.

    This is the main entry point for getting VAPID keys. It will:
    1. Check if keys exist in database
    2. Generate new keys if not present
    3. Return the keys

    Args:
        db: Database session

    Returns:
        Tuple of (private_key_pem, public_key_b64)
    """
    private_key, public_key = get_vapid_keys(db)

    if private_key and public_key:
        logger.debug("Using existing VAPID keys")
        return private_key, public_key

    # Generate new keys
    logger.info("No VAPID keys found, generating new pair")
    private_key, public_key = generate_vapid_keys()
    save_vapid_keys(db, private_key, public_key)

    return private_key, public_key


def get_vapid_public_key(db: Session) -> Optional[str]:
    """
    Get only the VAPID public key (for frontend).

    This is a convenience function that only returns the public key,
    which is safe to expose to the frontend.

    Args:
        db: Database session

    Returns:
        Public key in URL-safe base64 format, or None if not set
    """
    # First ensure keys exist
    ensure_vapid_keys(db)

    # Get public key
    public_setting = db.query(SystemSetting).filter(
        SystemSetting.key == VAPID_PUBLIC_KEY_SETTING
    ).first()

    return public_setting.value if public_setting else None
