from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pycampchef.const import VENDOR_CONFIGS

from .const import CONF_ADDRESS, CONF_NAME, CONF_VENDOR, DOMAIN
from .coordinator import CampChefCoordinator


@dataclass(frozen=True)
class CampChefSensorDescription:
    key: str
    name: str


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: CampChefCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, entry.title)
    caps = getattr(getattr(coordinator.data, "device", None), "capabilities", None)
    probe_count = caps.probe_count if caps and caps.probe_count else 0
    entities: list[SensorEntity] = [
        CampChefModeSensor(coordinator, entry, name),
        CampChefFanSensor(coordinator, entry, name),
        CampChefWifiRssiSensor(coordinator, entry, name),
        CampChefWifiSsidSensor(coordinator, entry, name),
        CampChefOtaStateSensor(coordinator, entry, name),
        CampChefOtaProgressSensor(coordinator, entry, name),
        CampChefPelletLevelSensor(coordinator, entry, name),
        CampChefTransitioningSensor(coordinator, entry, name),
        CampChefFaultSensor(coordinator, entry, name),
    ]
    for index in range(probe_count):
        entities.append(CampChefProbeSensor(coordinator, entry, name, index))
    async_add_entities(entities)


class CampChefBaseSensor(CoordinatorEntity[CampChefCoordinator], SensorEntity):
    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = None

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._base_name = name

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        # Ensure an initial state is written so history shows unavailable entries
        self.async_write_ha_state()

    @property
    def device_info(self):
        vendor_key = self._entry.data.get(CONF_VENDOR, "campchef")
        vendor = VENDOR_CONFIGS.get(vendor_key, VENDOR_CONFIGS["campchef"]).name
        address = self._entry.data[CONF_ADDRESS]
        return DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            name=self._base_name,
            manufacturer=vendor,
            sw_version=self.coordinator._device_info.get("sw_version"),
            hw_version=self.coordinator._device_info.get("hw_version"),
        )


class CampChefModeSensor(CampChefBaseSensor):
    _attr_name = "Mode"
    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = None
    _attr_icon = "mdi:grill"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.data[CONF_ADDRESS]}_mode"

    @property
    def native_value(self) -> Optional[str]:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if not mode or mode.mode is None:
            return None
        return mode.mode.name if hasattr(mode.mode, "name") else str(mode.mode)


class CampChefFanSensor(CampChefBaseSensor):
    _attr_name = "Fan level"
    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:fan"
    _attr_entity_registry_enabled_default = False

    @property
    def unique_id(self) -> str:
        return f"{self._entry.data[CONF_ADDRESS]}_fan"

    @property
    def native_value(self) -> Optional[int]:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if not mode or mode.fan_level is None:
            return None
        return int(mode.fan_level)


class CampChefWifiRssiSensor(CampChefBaseSensor):
    _attr_name = "Wi-Fi RSSI"
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:wifi-strength-2"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_wifi_rssi"
        # Use dBm unit
        self._attr_native_unit_of_measurement = "dBm"

    @property
    def native_value(self) -> Optional[int]:
        wifi = self.coordinator.data.wifi if self.coordinator.data else None
        return wifi.rssi_dbm if wifi and getattr(wifi, "rssi_dbm", None) is not None else None


class CampChefWifiSsidSensor(CampChefBaseSensor):
    _attr_name = "Wi-Fi SSID"
    _attr_device_class = None
    _attr_state_class = None
    _attr_icon = "mdi:wifi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_wifi_ssid"

    @property
    def native_value(self) -> Optional[str]:
        wifi = self.coordinator.data.wifi if self.coordinator.data else None
        ssid = getattr(wifi, "ssid", None)
        return ssid if ssid else None


class CampChefOtaStateSensor(CampChefBaseSensor):
    _attr_name = "OTA state"
    _attr_device_class = None
    _attr_state_class = None
    _attr_icon = "mdi:progress-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_ota_state"

    @property
    def native_value(self) -> Optional[str]:
        ota = self.coordinator.data.ota if self.coordinator.data else None
        state = getattr(ota, "state", None)
        if state is None:
            return None
        return state.name if hasattr(state, "name") else str(state)


class CampChefOtaProgressSensor(CampChefBaseSensor):
    _attr_name = "OTA progress"
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:progress-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_ota_progress"

    @property
    def native_value(self) -> Optional[int]:
        ota = self.coordinator.data.ota if self.coordinator.data else None
        progress = getattr(ota, "progress_percent", None)
        return int(progress) if progress is not None else None


class CampChefPelletLevelSensor(CampChefBaseSensor):
    _attr_name = "Pellet level"
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:silo"
    _attr_entity_category = None
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_pellet_level"

    @property
    def native_value(self) -> Optional[int]:
        status = self.coordinator.data.status if self.coordinator.data else None
        pellet = getattr(status, "pellet_level", None)
        return int(pellet) if pellet is not None else None


class CampChefTransitioningSensor(CampChefBaseSensor):
    _attr_name = "Transitioning"
    _attr_device_class = None
    _attr_state_class = None
    _attr_icon = "mdi:progress-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_transitioning"

    @property
    def native_value(self) -> Optional[bool]:
        status = self.coordinator.data.status if self.coordinator.data else None
        return bool(status.transitioning) if status and status.transitioning is not None else None


class CampChefFaultSensor(CampChefBaseSensor):
    _attr_name = "Fault present"
    _attr_device_class = None
    _attr_state_class = None
    _attr_icon = "mdi:alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_fault"

    @property
    def native_value(self) -> Optional[bool]:
        status = self.coordinator.data.status if self.coordinator.data else None
        return bool(status.has_fault) if status and status.has_fault is not None else None


class CampChefProbeSensor(CampChefBaseSensor):
    def __init__(self, coordinator: CampChefCoordinator, entry, name: str, index: int) -> None:
        super().__init__(coordinator, entry, name)
        self._index = index
        self._attr_name = f"Probe {index + 1}"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.data[CONF_ADDRESS]}_probe_{self._index + 1}"

    @property
    def native_value(self) -> Optional[float]:
        probes = self.coordinator.data.probes if self.coordinator.data else {}
        probe = probes.get(self._index)
        if not probe or not probe.connected:
            return None
        if probe.temp_f is None:
            return None
        return probe.temp_f
