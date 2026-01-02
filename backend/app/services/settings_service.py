"""Settings Service

Provides access to system settings stored in the database.
Used by email_service and other services that need configuration values.

Story P16-1.7: Created to support SMTP configuration for email invitations.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.system_setting import SystemSetting
from app.utils.encryption import decrypt_password, is_encrypted

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service for accessing system settings from the database.

    Provides methods to:
    - Get plain text settings
    - Get and decrypt encrypted settings (API keys, passwords)

    Usage:
        service = SettingsService(db)
        smtp_host = service.get_setting("smtp_host")
        smtp_password = service.get_encrypted_setting("smtp_password")
    """

    def __init__(self, db: Session):
        """
        Initialize SettingsService with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_setting(self, key: str) -> Optional[str]:
        """
        Get a setting value by key.

        Args:
            key: The setting key to look up

        Returns:
            The setting value, or None if not found
        """
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == key
        ).first()

        if setting is None:
            return None

        return setting.value

    def get_encrypted_setting(self, key: str) -> Optional[str]:
        """
        Get and decrypt an encrypted setting value.

        For settings like API keys and passwords that are stored encrypted.

        Args:
            key: The setting key to look up

        Returns:
            The decrypted setting value, or None if not found.
            Returns the raw value if not encrypted.
        """
        value = self.get_setting(key)

        if value is None:
            return None

        # If the value is encrypted, decrypt it
        if is_encrypted(value):
            try:
                return decrypt_password(value)
            except ValueError as e:
                logger.error(f"Failed to decrypt setting {key}: {e}")
                return None

        # Return raw value if not encrypted
        return value

    def set_setting(self, key: str, value: str) -> None:
        """
        Set a setting value.

        Args:
            key: The setting key
            value: The value to store
        """
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == key
        ).first()

        if setting is None:
            setting = SystemSetting(key=key, value=value)
            self.db.add(setting)
        else:
            setting.value = value

        self.db.commit()
