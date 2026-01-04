from __future__ import annotations

from typing import Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pycampchef.const import VENDOR_CONFIGS, ModeName

from .const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_VENDOR,
    DOMAIN,
    SMOKE_MAX_DEFAULT,
    SMOKE_MIN_DEFAULT,
)
from .coordinator import CampChefCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: CampChefCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, entry.title)
    async_add_entities([CampChefSmokeLevelNumber(coordinator, entry, name)])


class CampChefSmokeLevelNumber(CoordinatorEntity[CampChefCoordinator], NumberEntity):
    _attr_name = "Smoke level"
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 1
    _attr_icon = "mdi:smoke"

    def __init__(self, coordinator: CampChefCoordinator, entry, base_name: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._base_name = base_name
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_smoke_level"
        vendor_key = entry.data.get(CONF_VENDOR, "campchef")
        vendor_cfg = VENDOR_CONFIGS.get(vendor_key, VENDOR_CONFIGS["campchef"])
        self._attr_native_min_value = getattr(
            vendor_cfg, "smoke_level_min", SMOKE_MIN_DEFAULT
        )
        self._attr_native_max_value = getattr(
            vendor_cfg, "smoke_level_max", SMOKE_MAX_DEFAULT
        )

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

    @property
    def native_value(self) -> Optional[int]:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if not mode:
            return None
        if mode.mode != ModeName.RUN:
            return 0
        return int(mode.smoke_level) if mode.smoke_level is not None else None

    @property
    def available(self) -> bool:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        return bool(mode and mode.mode == ModeName.RUN and mode.set_temp_f is not None)

    async def async_set_native_value(self, value: float) -> None:
        target = int(value)
        if self.coordinator.client is None:
            return
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if mode is None or mode.mode != ModeName.RUN or mode.set_temp_f is None:
            return
        await self.coordinator.client.commands.set_temp_smoke(
            mode.set_temp_f, target
        )
        new_mode = mode.__class__(
            mode=mode.mode,
            set_temp_f=mode.set_temp_f,
            smoke_level=target,
            fan_level=mode.fan_level,
        )
        self.coordinator.data.mode = new_mode
        self.coordinator.async_set_updated_data(self.coordinator.data)
