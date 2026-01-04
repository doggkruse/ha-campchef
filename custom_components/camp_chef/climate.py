from __future__ import annotations

from typing import Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pycampchef.const import VENDOR_CONFIGS, ModeName
from pycampchef.models import GrillMode

from .const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_VENDOR,
    DEFAULT_MAX_TEMP_F,
    DEFAULT_MIN_TEMP_F,
    DOMAIN,
)
from .coordinator import CampChefCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: CampChefCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, entry.title)
    async_add_entities([CampChefThermostat(coordinator, entry, name)])


class CampChefThermostat(CoordinatorEntity[CampChefCoordinator], ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_native_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_name = "Chamber"

    def __init__(self, coordinator: CampChefCoordinator, entry, base_name: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._base_name = base_name
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_climate"
        self._attr_translation_key = "chamber"
        vendor_key = entry.data.get(CONF_VENDOR, "campchef")
        vendor_cfg = VENDOR_CONFIGS.get(vendor_key, VENDOR_CONFIGS["campchef"])
        self._min_temp_f = getattr(vendor_cfg, "min_temp_f", DEFAULT_MIN_TEMP_F)
        self._max_temp_f = getattr(vendor_cfg, "max_temp_f", DEFAULT_MAX_TEMP_F)

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
    def hvac_mode(self) -> HVACMode:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if mode and mode.mode == ModeName.RUN:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_modes(self) -> list[HVACMode]:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if mode and mode.mode == ModeName.RUN:
            return [HVACMode.OFF, HVACMode.HEAT]
        return [HVACMode.OFF]

    @property
    def current_temperature(self) -> Optional[float]:
        chamber = self.coordinator.data.chamber if self.coordinator.data else None
        return chamber.temp_f if chamber and chamber.temp_f is not None else None

    @property
    def target_temperature(self) -> Optional[float]:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        return float(mode.set_temp_f) if mode and mode.set_temp_f is not None else None

    @property
    def min_temp(self) -> float:
        return float(self._min_temp_f)

    @property
    def max_temp(self) -> float:
        return float(self._max_temp_f)

    @property
    def target_temperature_step(self) -> float:
        return 1.0

    @property
    def supported_features(self) -> int:
        if self.hvac_mode == HVACMode.HEAT:
            return ClimateEntityFeature.TARGET_TEMPERATURE
        return ClimateEntityFeature(0)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if hvac_mode == HVACMode.OFF:
            # Setting OFF should drop the grill to standby
            if self.coordinator.client is None:
                return
            try:
                await self.coordinator.client.commands.set_mode(ModeName.STANDBY)
            except Exception:
                return
            new_mode = GrillMode(
                mode=ModeName.STANDBY,
                set_temp_f=None,
                smoke_level=None,
                fan_level=None,
            )
            self.coordinator._data.mode = new_mode
            self.coordinator.async_set_updated_data(self.coordinator._data)
            return

        if hvac_mode == HVACMode.HEAT and self.target_temperature is not None:
            await self.async_set_temperature(temperature=self.target_temperature)

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        if self.coordinator.client is None:
            return
        mode = self.coordinator.data.mode if self.coordinator.data else None
        if not mode or mode.mode != ModeName.RUN:
            # Ignore set attempts when not in RUN; UI should already hide controls
            return
        smoke_level = mode.smoke_level if mode and mode.smoke_level is not None else 0
        await self.coordinator.client.commands.set_temp_smoke(int(temperature), smoke_level)
        # Optimistically update target temp so UI reflects the change immediately
        if mode is None:
            new_mode = GrillMode(set_temp_f=int(temperature), smoke_level=smoke_level)
        else:
            new_mode = GrillMode(
                mode=mode.mode,
                set_temp_f=int(temperature),
                smoke_level=mode.smoke_level if mode.smoke_level is not None else smoke_level,
                fan_level=mode.fan_level,
            )
        self.coordinator._data.mode = new_mode
        self.coordinator.async_set_updated_data(self.coordinator._data)
        await self.coordinator.async_request_refresh()
