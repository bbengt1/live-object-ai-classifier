"""
HomeKit accessory definitions (Story P4-6.1, P5-1.5, P5-1.6, P5-1.7)

Defines custom HomeKit accessories for ArgusAI cameras.
Story P5-1.5 adds OccupancySensor for person-only detection.
Story P5-1.6 adds Vehicle/Animal/Package sensors for detection-type-specific automations.
Story P5-1.7 adds Doorbell sensor for Protect doorbell ring events.
"""
import logging
from typing import Optional

try:
    from pyhap.accessory import Accessory
    from pyhap.const import CATEGORY_SENSOR
    HAP_AVAILABLE = True
except ImportError:
    HAP_AVAILABLE = False
    CATEGORY_SENSOR = 16  # Default category for sensors

logger = logging.getLogger(__name__)


class CameraMotionSensor:
    """
    HomeKit Motion Sensor accessory for ArgusAI cameras.

    Exposes a camera as a motion sensor in the Home app.
    Motion events are triggered when AI detection events occur.

    Attributes:
        camera_id: Unique identifier for the camera
        name: Display name in Home app
        manufacturer: Manufacturer name
        serial_number: Serial number (uses camera_id)
    """

    category = CATEGORY_SENSOR

    def __init__(
        self,
        driver,
        camera_id: str,
        name: str,
        manufacturer: str = "ArgusAI",
        model: str = "Motion Sensor"
    ):
        """
        Initialize a camera motion sensor accessory.

        Args:
            driver: HAP-python AccessoryDriver instance
            camera_id: Unique camera identifier
            name: Display name for the accessory
            manufacturer: Manufacturer name (default: ArgusAI)
            model: Model name (default: Motion Sensor)
        """
        if not HAP_AVAILABLE:
            raise ImportError("HAP-python is not installed. Install with: pip install HAP-python")

        # Create base accessory - use Accessory class
        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        self.camera_id = camera_id
        self.name = name
        self._motion_detected = False

        # Set accessory information
        accessory_info = self._accessory.get_service("AccessoryInformation")
        if accessory_info:
            accessory_info.configure_char("Manufacturer", value=manufacturer)
            accessory_info.configure_char("Model", value=model)
            accessory_info.configure_char("SerialNumber", value=camera_id[:20])  # HAP limits serial to 20 chars
            accessory_info.configure_char("FirmwareRevision", value="1.0.0")

        # Add MotionSensor service
        self._motion_service = self._accessory.add_preload_service("MotionSensor")
        self._motion_char = self._motion_service.configure_char("MotionDetected", value=False)

        logger.debug(f"Created HomeKit motion sensor for camera: {name} ({camera_id})")

    @property
    def accessory(self):
        """Get the underlying HAP-python Accessory instance."""
        return self._accessory

    @property
    def motion_detected(self) -> bool:
        """Get current motion detection state."""
        return self._motion_detected

    def set_motion(self, detected: bool) -> None:
        """
        Update the motion detection state.

        Args:
            detected: True if motion is detected, False otherwise
        """
        if self._motion_detected != detected:
            self._motion_detected = detected
            self._motion_char.set_value(detected)
            logger.debug(f"HomeKit motion sensor {self.name}: motion={'detected' if detected else 'cleared'}")

    def trigger_motion(self) -> None:
        """Trigger motion detection (sets motion to True)."""
        self.set_motion(True)

    def clear_motion(self) -> None:
        """Clear motion detection (sets motion to False)."""
        self.set_motion(False)

    def __repr__(self) -> str:
        return f"<CameraMotionSensor(name={self.name}, camera_id={self.camera_id}, motion={self._motion_detected})>"


def create_motion_sensor(
    driver,
    camera_id: str,
    camera_name: str,
    manufacturer: str = "ArgusAI"
) -> Optional[CameraMotionSensor]:
    """
    Factory function to create a camera motion sensor.

    Args:
        driver: HAP-python AccessoryDriver instance
        camera_id: Unique camera identifier
        camera_name: Display name for the camera
        manufacturer: Manufacturer name

    Returns:
        CameraMotionSensor instance or None if HAP-python not available
    """
    if not HAP_AVAILABLE:
        logger.warning("HAP-python not available, cannot create HomeKit motion sensor")
        return None

    try:
        return CameraMotionSensor(
            driver=driver,
            camera_id=camera_id,
            name=camera_name,
            manufacturer=manufacturer
        )
    except Exception as e:
        logger.error(f"Failed to create motion sensor for {camera_name}: {e}")
        return None


class CameraOccupancySensor:
    """
    HomeKit Occupancy Sensor accessory for ArgusAI cameras (Story P5-1.5).

    Exposes a camera as an occupancy sensor in the Home app.
    Only triggers on person detection events (not motion, vehicle, animal, or package).
    Has a longer timeout (5 minutes default) compared to motion sensors (30s).

    Attributes:
        camera_id: Unique identifier for the camera
        name: Display name in Home app (should include "Occupancy")
        manufacturer: Manufacturer name
        serial_number: Serial number (uses camera_id)
    """

    category = CATEGORY_SENSOR

    def __init__(
        self,
        driver,
        camera_id: str,
        name: str,
        manufacturer: str = "ArgusAI",
        model: str = "Occupancy Sensor"
    ):
        """
        Initialize a camera occupancy sensor accessory.

        Args:
            driver: HAP-python AccessoryDriver instance
            camera_id: Unique camera identifier
            name: Display name for the accessory (should include "Occupancy")
            manufacturer: Manufacturer name (default: ArgusAI)
            model: Model name (default: Occupancy Sensor)
        """
        if not HAP_AVAILABLE:
            raise ImportError("HAP-python is not installed. Install with: pip install HAP-python")

        # Create base accessory - use Accessory class
        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        self.camera_id = camera_id
        self.name = name
        self._occupancy_detected = False

        # Set accessory information
        accessory_info = self._accessory.get_service("AccessoryInformation")
        if accessory_info:
            accessory_info.configure_char("Manufacturer", value=manufacturer)
            accessory_info.configure_char("Model", value=model)
            accessory_info.configure_char("SerialNumber", value=camera_id[:20])  # HAP limits serial to 20 chars
            accessory_info.configure_char("FirmwareRevision", value="1.0.0")

        # Add OccupancySensor service (distinct from MotionSensor)
        self._occupancy_service = self._accessory.add_preload_service("OccupancySensor")
        self._occupancy_char = self._occupancy_service.configure_char("OccupancyDetected", value=0)

        logger.debug(f"Created HomeKit occupancy sensor for camera: {name} ({camera_id})")

    @property
    def accessory(self):
        """Get the underlying HAP-python Accessory instance."""
        return self._accessory

    @property
    def occupancy_detected(self) -> bool:
        """Get current occupancy detection state."""
        return self._occupancy_detected

    def set_occupancy(self, detected: bool) -> None:
        """
        Update the occupancy detection state.

        Args:
            detected: True if occupancy is detected, False otherwise
        """
        if self._occupancy_detected != detected:
            self._occupancy_detected = detected
            # OccupancyDetected uses integer: 0 = Not Occupied, 1 = Occupied
            self._occupancy_char.set_value(1 if detected else 0)
            logger.debug(f"HomeKit occupancy sensor {self.name}: occupancy={'detected' if detected else 'cleared'}")

    def trigger_occupancy(self) -> None:
        """Trigger occupancy detection (sets occupancy to True)."""
        self.set_occupancy(True)

    def clear_occupancy(self) -> None:
        """Clear occupancy detection (sets occupancy to False)."""
        self.set_occupancy(False)

    def __repr__(self) -> str:
        return f"<CameraOccupancySensor(name={self.name}, camera_id={self.camera_id}, occupancy={self._occupancy_detected})>"


def create_occupancy_sensor(
    driver,
    camera_id: str,
    camera_name: str,
    manufacturer: str = "ArgusAI"
) -> Optional[CameraOccupancySensor]:
    """
    Factory function to create a camera occupancy sensor (Story P5-1.5).

    Args:
        driver: HAP-python AccessoryDriver instance
        camera_id: Unique camera identifier
        camera_name: Display name for the camera (will have " Occupancy" appended if not present)
        manufacturer: Manufacturer name

    Returns:
        CameraOccupancySensor instance or None if HAP-python not available
    """
    if not HAP_AVAILABLE:
        logger.warning("HAP-python not available, cannot create HomeKit occupancy sensor")
        return None

    try:
        return CameraOccupancySensor(
            driver=driver,
            camera_id=camera_id,
            name=camera_name,
            manufacturer=manufacturer
        )
    except Exception as e:
        logger.error(f"Failed to create occupancy sensor for {camera_name}: {e}")
        return None


# =============================================================================
# Story P5-1.6: Detection-Type-Specific Sensors (Vehicle, Animal, Package)
# =============================================================================


class CameraVehicleSensor:
    """
    HomeKit Vehicle Sensor accessory for ArgusAI cameras (Story P5-1.6).

    Uses MotionSensor service but only triggers on vehicle detection events.
    Enables users to create vehicle-specific HomeKit automations.

    Attributes:
        camera_id: Unique identifier for the camera
        name: Display name in Home app (should include "Vehicle")
        manufacturer: Manufacturer name
        serial_number: Serial number (uses camera_id)
    """

    category = CATEGORY_SENSOR

    def __init__(
        self,
        driver,
        camera_id: str,
        name: str,
        manufacturer: str = "ArgusAI",
        model: str = "Vehicle Sensor"
    ):
        """
        Initialize a camera vehicle sensor accessory.

        Args:
            driver: HAP-python AccessoryDriver instance
            camera_id: Unique camera identifier
            name: Display name for the accessory (should include "Vehicle")
            manufacturer: Manufacturer name (default: ArgusAI)
            model: Model name (default: Vehicle Sensor)
        """
        if not HAP_AVAILABLE:
            raise ImportError("HAP-python is not installed. Install with: pip install HAP-python")

        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        self.camera_id = camera_id
        self.name = name
        self._motion_detected = False

        # Set accessory information
        accessory_info = self._accessory.get_service("AccessoryInformation")
        if accessory_info:
            accessory_info.configure_char("Manufacturer", value=manufacturer)
            accessory_info.configure_char("Model", value=model)
            accessory_info.configure_char("SerialNumber", value=camera_id[:20])
            accessory_info.configure_char("FirmwareRevision", value="1.0.0")

        # Use MotionSensor service (same as motion sensor, differentiated by name)
        self._motion_service = self._accessory.add_preload_service("MotionSensor")
        self._motion_char = self._motion_service.configure_char("MotionDetected", value=False)

        logger.debug(f"Created HomeKit vehicle sensor for camera: {name} ({camera_id})")

    @property
    def accessory(self):
        """Get the underlying HAP-python Accessory instance."""
        return self._accessory

    @property
    def motion_detected(self) -> bool:
        """Get current motion detection state."""
        return self._motion_detected

    def set_motion(self, detected: bool) -> None:
        """Update the motion detection state."""
        if self._motion_detected != detected:
            self._motion_detected = detected
            self._motion_char.set_value(detected)
            logger.debug(f"HomeKit vehicle sensor {self.name}: {'detected' if detected else 'cleared'}")

    def trigger_motion(self) -> None:
        """Trigger vehicle detection."""
        self.set_motion(True)

    def clear_motion(self) -> None:
        """Clear vehicle detection."""
        self.set_motion(False)

    def __repr__(self) -> str:
        return f"<CameraVehicleSensor(name={self.name}, camera_id={self.camera_id}, detected={self._motion_detected})>"


def create_vehicle_sensor(
    driver,
    camera_id: str,
    camera_name: str,
    manufacturer: str = "ArgusAI"
) -> Optional[CameraVehicleSensor]:
    """
    Factory function to create a camera vehicle sensor (Story P5-1.6).

    Args:
        driver: HAP-python AccessoryDriver instance
        camera_id: Unique camera identifier
        camera_name: Display name for the camera
        manufacturer: Manufacturer name

    Returns:
        CameraVehicleSensor instance or None if HAP-python not available
    """
    if not HAP_AVAILABLE:
        logger.warning("HAP-python not available, cannot create HomeKit vehicle sensor")
        return None

    try:
        return CameraVehicleSensor(
            driver=driver,
            camera_id=camera_id,
            name=camera_name,
            manufacturer=manufacturer
        )
    except Exception as e:
        logger.error(f"Failed to create vehicle sensor for {camera_name}: {e}")
        return None


class CameraAnimalSensor:
    """
    HomeKit Animal Sensor accessory for ArgusAI cameras (Story P5-1.6).

    Uses MotionSensor service but only triggers on animal detection events.
    Enables users to create animal-specific HomeKit automations.

    Attributes:
        camera_id: Unique identifier for the camera
        name: Display name in Home app (should include "Animal")
        manufacturer: Manufacturer name
        serial_number: Serial number (uses camera_id)
    """

    category = CATEGORY_SENSOR

    def __init__(
        self,
        driver,
        camera_id: str,
        name: str,
        manufacturer: str = "ArgusAI",
        model: str = "Animal Sensor"
    ):
        """
        Initialize a camera animal sensor accessory.

        Args:
            driver: HAP-python AccessoryDriver instance
            camera_id: Unique camera identifier
            name: Display name for the accessory (should include "Animal")
            manufacturer: Manufacturer name (default: ArgusAI)
            model: Model name (default: Animal Sensor)
        """
        if not HAP_AVAILABLE:
            raise ImportError("HAP-python is not installed. Install with: pip install HAP-python")

        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        self.camera_id = camera_id
        self.name = name
        self._motion_detected = False

        accessory_info = self._accessory.get_service("AccessoryInformation")
        if accessory_info:
            accessory_info.configure_char("Manufacturer", value=manufacturer)
            accessory_info.configure_char("Model", value=model)
            accessory_info.configure_char("SerialNumber", value=camera_id[:20])
            accessory_info.configure_char("FirmwareRevision", value="1.0.0")

        self._motion_service = self._accessory.add_preload_service("MotionSensor")
        self._motion_char = self._motion_service.configure_char("MotionDetected", value=False)

        logger.debug(f"Created HomeKit animal sensor for camera: {name} ({camera_id})")

    @property
    def accessory(self):
        """Get the underlying HAP-python Accessory instance."""
        return self._accessory

    @property
    def motion_detected(self) -> bool:
        """Get current motion detection state."""
        return self._motion_detected

    def set_motion(self, detected: bool) -> None:
        """Update the motion detection state."""
        if self._motion_detected != detected:
            self._motion_detected = detected
            self._motion_char.set_value(detected)
            logger.debug(f"HomeKit animal sensor {self.name}: {'detected' if detected else 'cleared'}")

    def trigger_motion(self) -> None:
        """Trigger animal detection."""
        self.set_motion(True)

    def clear_motion(self) -> None:
        """Clear animal detection."""
        self.set_motion(False)

    def __repr__(self) -> str:
        return f"<CameraAnimalSensor(name={self.name}, camera_id={self.camera_id}, detected={self._motion_detected})>"


def create_animal_sensor(
    driver,
    camera_id: str,
    camera_name: str,
    manufacturer: str = "ArgusAI"
) -> Optional[CameraAnimalSensor]:
    """
    Factory function to create a camera animal sensor (Story P5-1.6).

    Args:
        driver: HAP-python AccessoryDriver instance
        camera_id: Unique camera identifier
        camera_name: Display name for the camera
        manufacturer: Manufacturer name

    Returns:
        CameraAnimalSensor instance or None if HAP-python not available
    """
    if not HAP_AVAILABLE:
        logger.warning("HAP-python not available, cannot create HomeKit animal sensor")
        return None

    try:
        return CameraAnimalSensor(
            driver=driver,
            camera_id=camera_id,
            name=camera_name,
            manufacturer=manufacturer
        )
    except Exception as e:
        logger.error(f"Failed to create animal sensor for {camera_name}: {e}")
        return None


class CameraPackageSensor:
    """
    HomeKit Package Sensor accessory for ArgusAI cameras (Story P5-1.6).

    Uses MotionSensor service but only triggers on package detection events.
    Enables users to create package-specific HomeKit automations.
    Has a longer default timeout (60s) since packages persist.

    Attributes:
        camera_id: Unique identifier for the camera
        name: Display name in Home app (should include "Package")
        manufacturer: Manufacturer name
        serial_number: Serial number (uses camera_id)
    """

    category = CATEGORY_SENSOR

    def __init__(
        self,
        driver,
        camera_id: str,
        name: str,
        manufacturer: str = "ArgusAI",
        model: str = "Package Sensor"
    ):
        """
        Initialize a camera package sensor accessory.

        Args:
            driver: HAP-python AccessoryDriver instance
            camera_id: Unique camera identifier
            name: Display name for the accessory (should include "Package")
            manufacturer: Manufacturer name (default: ArgusAI)
            model: Model name (default: Package Sensor)
        """
        if not HAP_AVAILABLE:
            raise ImportError("HAP-python is not installed. Install with: pip install HAP-python")

        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        self.camera_id = camera_id
        self.name = name
        self._motion_detected = False

        accessory_info = self._accessory.get_service("AccessoryInformation")
        if accessory_info:
            accessory_info.configure_char("Manufacturer", value=manufacturer)
            accessory_info.configure_char("Model", value=model)
            accessory_info.configure_char("SerialNumber", value=camera_id[:20])
            accessory_info.configure_char("FirmwareRevision", value="1.0.0")

        self._motion_service = self._accessory.add_preload_service("MotionSensor")
        self._motion_char = self._motion_service.configure_char("MotionDetected", value=False)

        logger.debug(f"Created HomeKit package sensor for camera: {name} ({camera_id})")

    @property
    def accessory(self):
        """Get the underlying HAP-python Accessory instance."""
        return self._accessory

    @property
    def motion_detected(self) -> bool:
        """Get current motion detection state."""
        return self._motion_detected

    def set_motion(self, detected: bool) -> None:
        """Update the motion detection state."""
        if self._motion_detected != detected:
            self._motion_detected = detected
            self._motion_char.set_value(detected)
            logger.debug(f"HomeKit package sensor {self.name}: {'detected' if detected else 'cleared'}")

    def trigger_motion(self) -> None:
        """Trigger package detection."""
        self.set_motion(True)

    def clear_motion(self) -> None:
        """Clear package detection."""
        self.set_motion(False)

    def __repr__(self) -> str:
        return f"<CameraPackageSensor(name={self.name}, camera_id={self.camera_id}, detected={self._motion_detected})>"


def create_package_sensor(
    driver,
    camera_id: str,
    camera_name: str,
    manufacturer: str = "ArgusAI"
) -> Optional[CameraPackageSensor]:
    """
    Factory function to create a camera package sensor (Story P5-1.6).

    Args:
        driver: HAP-python AccessoryDriver instance
        camera_id: Unique camera identifier
        camera_name: Display name for the camera
        manufacturer: Manufacturer name

    Returns:
        CameraPackageSensor instance or None if HAP-python not available
    """
    if not HAP_AVAILABLE:
        logger.warning("HAP-python not available, cannot create HomeKit package sensor")
        return None

    try:
        return CameraPackageSensor(
            driver=driver,
            camera_id=camera_id,
            name=camera_name,
            manufacturer=manufacturer
        )
    except Exception as e:
        logger.error(f"Failed to create package sensor for {camera_name}: {e}")
        return None


# =============================================================================
# Story P5-1.7: Doorbell Sensor for Protect Doorbell Ring Events
# =============================================================================


class CameraDoorbellSensor:
    """
    HomeKit Doorbell Sensor accessory for ArgusAI Protect doorbell cameras (Story P5-1.7).

    Uses StatelessProgrammableSwitch service to trigger doorbell ring events.
    Unlike motion/occupancy sensors, doorbell events are stateless (no reset timer needed).
    Ring events fire a single press event (value 0) to notify all paired devices.

    Only created for cameras where is_doorbell == True.

    Attributes:
        camera_id: Unique identifier for the camera
        name: Display name in Home app (should include "Doorbell")
        manufacturer: Manufacturer name
        serial_number: Serial number (uses camera_id)
    """

    category = CATEGORY_SENSOR

    def __init__(
        self,
        driver,
        camera_id: str,
        name: str,
        manufacturer: str = "ArgusAI",
        model: str = "Doorbell"
    ):
        """
        Initialize a camera doorbell sensor accessory.

        Args:
            driver: HAP-python AccessoryDriver instance
            camera_id: Unique camera identifier
            name: Display name for the accessory (should include "Doorbell")
            manufacturer: Manufacturer name (default: ArgusAI)
            model: Model name (default: Doorbell)
        """
        if not HAP_AVAILABLE:
            raise ImportError("HAP-python is not installed. Install with: pip install HAP-python")

        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        self.camera_id = camera_id
        self.name = name

        # Set accessory information
        accessory_info = self._accessory.get_service("AccessoryInformation")
        if accessory_info:
            accessory_info.configure_char("Manufacturer", value=manufacturer)
            accessory_info.configure_char("Model", value=model)
            accessory_info.configure_char("SerialNumber", value=camera_id[:20])
            accessory_info.configure_char("FirmwareRevision", value="1.0.0")

        # Add StatelessProgrammableSwitch service for doorbell events
        # This is the HAP service that triggers doorbell-style notifications
        self._switch_service = self._accessory.add_preload_service(
            "StatelessProgrammableSwitch"
        )
        # ProgrammableSwitchEvent: 0 = Single Press, 1 = Double Press, 2 = Long Press
        # For doorbell, we only use Single Press (0)
        self._switch_event = self._switch_service.configure_char(
            "ProgrammableSwitchEvent",
            value=0
        )

        logger.debug(f"Created HomeKit doorbell sensor for camera: {name} ({camera_id})")

    @property
    def accessory(self):
        """Get the underlying HAP-python Accessory instance."""
        return self._accessory

    def trigger_ring(self) -> None:
        """
        Trigger doorbell ring event (stateless - fires event, no state change).

        Sets ProgrammableSwitchEvent to 0 (Single Press) which notifies
        all paired HomeKit devices of a doorbell ring.
        """
        # Setting value fires the event to HomeKit clients
        self._switch_event.set_value(0)  # 0 = Single Press
        logger.debug(f"HomeKit doorbell ring triggered for: {self.name}")

    def __repr__(self) -> str:
        return f"<CameraDoorbellSensor(name={self.name}, camera_id={self.camera_id})>"


def create_doorbell_sensor(
    driver,
    camera_id: str,
    camera_name: str,
    manufacturer: str = "ArgusAI"
) -> Optional[CameraDoorbellSensor]:
    """
    Factory function to create a camera doorbell sensor (Story P5-1.7).

    Args:
        driver: HAP-python AccessoryDriver instance
        camera_id: Unique camera identifier
        camera_name: Display name for the camera
        manufacturer: Manufacturer name

    Returns:
        CameraDoorbellSensor instance or None if HAP-python not available
    """
    if not HAP_AVAILABLE:
        logger.warning("HAP-python not available, cannot create HomeKit doorbell sensor")
        return None

    try:
        return CameraDoorbellSensor(
            driver=driver,
            camera_id=camera_id,
            name=camera_name,
            manufacturer=manufacturer
        )
    except Exception as e:
        logger.error(f"Failed to create doorbell sensor for {camera_name}: {e}")
        return None
