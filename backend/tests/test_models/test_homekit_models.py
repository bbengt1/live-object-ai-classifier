"""
Unit tests for HomeKit database models (Story P5-1.1)

Tests cover:
- HomeKitConfig model creation and validation
- HomeKitAccessory model with camera FK
- PIN code encryption/decryption
"""
import pytest
from datetime import datetime
from app.models.homekit import HomeKitConfig, HomeKitAccessory
from app.models.camera import Camera


class TestHomeKitConfigModel:
    """Tests for HomeKitConfig database model."""

    def test_create_config_with_defaults(self, db_session):
        """AC5: HomeKitConfig creates with sensible defaults."""
        config = HomeKitConfig(id=1)

        db_session.add(config)
        db_session.commit()

        assert config.id == 1
        assert config.enabled is False
        assert config.bridge_name == "ArgusAI"
        assert config.port == 51826
        assert config.motion_reset_seconds == 30
        assert config.max_motion_duration == 300
        assert config.pin_code is None
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_create_config_with_custom_values(self, db_session):
        """AC5: HomeKitConfig accepts custom values."""
        config = HomeKitConfig(
            id=1,
            enabled=True,
            bridge_name="MyHome",
            port=51827,
            motion_reset_seconds=60,
            max_motion_duration=600
        )

        db_session.add(config)
        db_session.commit()

        assert config.enabled is True
        assert config.bridge_name == "MyHome"
        assert config.port == 51827
        assert config.motion_reset_seconds == 60
        assert config.max_motion_duration == 600

    def test_pin_code_encryption(self, db_session):
        """AC5: PIN code is encrypted when set."""
        config = HomeKitConfig(id=1)
        plain_pin = "123-45-678"

        config.set_pin_code(plain_pin)

        db_session.add(config)
        db_session.commit()

        # PIN should be encrypted in database
        assert config.pin_code is not None
        assert config.pin_code.startswith("encrypted:")
        assert config.pin_code != plain_pin

    def test_pin_code_decryption(self, db_session):
        """AC5: PIN code can be decrypted."""
        config = HomeKitConfig(id=1)
        plain_pin = "987-65-432"

        config.set_pin_code(plain_pin)

        db_session.add(config)
        db_session.commit()

        # Should decrypt correctly
        decrypted = config.get_pin_code()
        assert decrypted == plain_pin

    def test_pin_code_none_handling(self, db_session):
        """PIN code handles None correctly."""
        config = HomeKitConfig(id=1)

        db_session.add(config)
        db_session.commit()

        assert config.pin_code is None
        assert config.get_pin_code() is None

        # Setting None should work
        config.set_pin_code(None)
        db_session.commit()

        assert config.pin_code is None

    def test_port_validation_low(self, db_session):
        """Port validation rejects values below 1024."""
        with pytest.raises(ValueError, match="Port must be between"):
            config = HomeKitConfig(id=1, port=80)

    def test_port_validation_high(self, db_session):
        """Port validation rejects values above 65535."""
        with pytest.raises(ValueError, match="Port must be between"):
            config = HomeKitConfig(id=1, port=70000)

    def test_motion_reset_validation(self, db_session):
        """Motion reset validation rejects values below 1."""
        with pytest.raises(ValueError, match="motion_reset_seconds must be >= 1"):
            config = HomeKitConfig(id=1, motion_reset_seconds=0)

    def test_max_duration_validation(self, db_session):
        """Max duration validation rejects values below 1."""
        with pytest.raises(ValueError, match="max_motion_duration must be >= 1"):
            config = HomeKitConfig(id=1, max_motion_duration=0)

    def test_to_dict(self, db_session):
        """to_dict returns correct dictionary."""
        config = HomeKitConfig(
            id=1,
            enabled=True,
            bridge_name="TestBridge",
            port=51827
        )

        db_session.add(config)
        db_session.commit()

        result = config.to_dict()

        assert result["id"] == 1
        assert result["enabled"] is True
        assert result["bridge_name"] == "TestBridge"
        assert result["port"] == 51827
        assert "created_at" in result
        assert "updated_at" in result

    def test_repr(self, db_session):
        """__repr__ returns useful string."""
        config = HomeKitConfig(
            id=1,
            enabled=True,
            bridge_name="ArgusAI",
            port=51826
        )

        db_session.add(config)
        db_session.commit()

        repr_str = repr(config)

        assert "HomeKitConfig" in repr_str
        assert "enabled=True" in repr_str
        assert "ArgusAI" in repr_str


class TestHomeKitAccessoryModel:
    """Tests for HomeKitAccessory database model."""

    def test_create_accessory_with_camera_fk(self, db_session):
        """AC5: HomeKitAccessory links to camera correctly."""
        # Create camera first
        camera = Camera(
            name="Test Camera",
            type="rtsp",
            rtsp_url="rtsp://example.com/stream"
        )
        db_session.add(camera)
        db_session.commit()

        # Create config
        config = HomeKitConfig(id=1)
        db_session.add(config)
        db_session.commit()

        # Create accessory
        accessory = HomeKitAccessory(
            config_id=1,
            camera_id=camera.id,
            accessory_type="motion",
            enabled=True
        )

        db_session.add(accessory)
        db_session.commit()

        assert accessory.id is not None
        assert accessory.camera_id == camera.id
        assert accessory.config_id == 1
        assert accessory.accessory_type == "motion"
        assert accessory.enabled is True

    def test_accessory_types(self, db_session):
        """AC5: Valid accessory types are accepted."""
        camera = Camera(
            name="Test Camera",
            type="rtsp",
            rtsp_url="rtsp://example.com/stream"
        )
        db_session.add(camera)

        config = HomeKitConfig(id=1)
        db_session.add(config)
        db_session.commit()

        valid_types = ['camera', 'motion', 'occupancy', 'doorbell']

        for i, atype in enumerate(valid_types):
            accessory = HomeKitAccessory(
                config_id=1,
                camera_id=camera.id,
                accessory_type=atype
            )
            db_session.add(accessory)

        db_session.commit()

        accessories = db_session.query(HomeKitAccessory).all()
        assert len(accessories) == 4

    def test_accessory_invalid_type(self, db_session):
        """Invalid accessory type is rejected."""
        camera = Camera(
            name="Test Camera",
            type="rtsp",
            rtsp_url="rtsp://example.com/stream"
        )
        db_session.add(camera)

        config = HomeKitConfig(id=1)
        db_session.add(config)
        db_session.commit()

        with pytest.raises(ValueError, match="accessory_type must be one of"):
            HomeKitAccessory(
                config_id=1,
                camera_id=camera.id,
                accessory_type="invalid_type"
            )

    def test_accessory_to_dict(self, db_session):
        """to_dict returns correct dictionary."""
        camera = Camera(
            name="Test Camera",
            type="rtsp",
            rtsp_url="rtsp://example.com/stream"
        )
        db_session.add(camera)

        config = HomeKitConfig(id=1)
        db_session.add(config)
        db_session.commit()

        accessory = HomeKitAccessory(
            config_id=1,
            camera_id=camera.id,
            accessory_type="motion",
            accessory_aid=5,
            enabled=True
        )
        db_session.add(accessory)
        db_session.commit()

        result = accessory.to_dict()

        assert result["camera_id"] == camera.id
        assert result["accessory_type"] == "motion"
        assert result["accessory_aid"] == 5
        assert result["enabled"] is True

    def test_camera_relationship_backref(self, db_session):
        """Camera.homekit_accessories relationship works."""
        camera = Camera(
            name="Test Camera",
            type="rtsp",
            rtsp_url="rtsp://example.com/stream"
        )
        db_session.add(camera)

        config = HomeKitConfig(id=1)
        db_session.add(config)
        db_session.commit()

        accessory1 = HomeKitAccessory(
            config_id=1,
            camera_id=camera.id,
            accessory_type="motion"
        )
        accessory2 = HomeKitAccessory(
            config_id=1,
            camera_id=camera.id,
            accessory_type="occupancy"
        )
        db_session.add_all([accessory1, accessory2])
        db_session.commit()

        # Check backref
        db_session.refresh(camera)
        assert len(camera.homekit_accessories) == 2

    def test_cascade_delete_on_camera(self, db_session):
        """Accessories deleted when camera is deleted."""
        camera = Camera(
            name="Test Camera",
            type="rtsp",
            rtsp_url="rtsp://example.com/stream"
        )
        db_session.add(camera)

        config = HomeKitConfig(id=1)
        db_session.add(config)
        db_session.commit()

        accessory = HomeKitAccessory(
            config_id=1,
            camera_id=camera.id,
            accessory_type="motion"
        )
        db_session.add(accessory)
        db_session.commit()

        accessory_id = accessory.id

        # Delete camera
        db_session.delete(camera)
        db_session.commit()

        # Accessory should be gone
        result = db_session.query(HomeKitAccessory).filter(
            HomeKitAccessory.id == accessory_id
        ).first()
        assert result is None
