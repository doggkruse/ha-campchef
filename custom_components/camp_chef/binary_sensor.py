from __future__ import annotations

from typing import Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pycampchef.const import VENDOR_CONFIGS, WifiStatus

from .const import CONF_ADDRESS, CONF_NAME, CONF_VENDOR, DOMAIN
from .coordinator import CampChefCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: CampChefCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, entry.title)
    async_add_entities([CampChefWifiStatusBinarySensor(coordinator, entry, name)])


class CampChefBaseBinarySensor(CoordinatorEntity[CampChefCoordinator], BinarySensorEntity):
    _attr_device_class = None
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._base_name = name

    @property
    def device_info(self) -> DeviceInfo:
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


class CampChefWifiStatusBinarySensor(CampChefBaseBinarySensor):
    _attr_name = "Wi-Fi status"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: CampChefCoordinator, entry, name: str) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{self._entry.data[CONF_ADDRESS]}_wifi_status"

    @property
    def is_on(self) -> Optional[bool]:
        wifi = self.coordinator.data.wifi if self.coordinator.data else None
        status = getattr(wifi, "status", None)
        if status is None:
            return None
        try:
            return WifiStatus(status) == WifiStatus.CONNECTED
        except Exception:
            return None
