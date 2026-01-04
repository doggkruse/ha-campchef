from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pycampchef.client import CampChefBleClient
from pycampchef.const import ModeName, VENDOR_CONFIGS
from pycampchef.models import GrillChamber, GrillMode, GrillProbe, GrillState

from .const import DOMAIN

POLL_INTERVAL_NOTIFY_BACKSTOP = timedelta(seconds=120)
POLL_INTERVAL_POLLING = timedelta(seconds=20)
_LOGGER = logging.getLogger(__name__)


class CampChefCoordinator(DataUpdateCoordinator[GrillState]):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        address: str,
        vendor_key: str,
        name: str,
        entry_id: str,
    ) -> None:
        vendor = VENDOR_CONFIGS.get(vendor_key, VENDOR_CONFIGS["campchef"])
        self._address = address
        self._vendor = vendor
        self._name = name
        self._entry_id = entry_id
        self.client: Optional[CampChefBleClient] = None
        self._device_info: dict[str, Any] = {}
        self.update_interval: timedelta | None = timedelta(seconds=15)
        self.data: GrillState | None = GrillState()
        self.last_update_success = True
        super().__init__(
            hass,
            _LOGGER,
            name=f"{name} BLE",
            update_interval=timedelta(seconds=15),
        )

    async def async_start(self) -> None:
        ble_device = async_ble_device_from_address(self.hass, self._address)
        if ble_device is None:
            ble_device = async_ble_device_from_address(
                self.hass, self._address, connectable=False
            )
        if ble_device is None:
            raise ConfigEntryNotReady("BLE device not yet available")

        self.client = CampChefBleClient(
            ble_device,
            vendor=self._vendor,
            on_update=self._handle_telemetry,
        )

        # Kick off the first refresh (will connect, read, and schedule polling)
        await self.async_refresh()

    async def async_stop(self) -> None:
        if self.client is not None:
            await self.client.disconnect()

    async def _async_update_data(self) -> GrillState:
        if self.client is None:
            raise ConfigEntryNotReady("BLE client not connected")

        try:
            await self.client.ensure_connected()
        except Exception as exc:
            raise ConfigEntryNotReady(f"Unable to connect: {exc}") from exc

        notify_ok = self.client.is_notifying

        # Adjust poll interval based on mode (optional but nice)
        self.update_interval = POLL_INTERVAL_NOTIFY_BACKSTOP if notify_ok else POLL_INTERVAL_POLLING

        try:
            if notify_ok:
                # Prefer cached state (from notifications). If none yet, do a snapshot once.
                if self.data is not None:
                    data = self.client.state
                else:
                    data = await self.client.get_state_snapshot()
            else:
                data = await self.client.get_state_snapshot()
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc

        self.data = data
        self._update_device_info()
        return self.data

    def _update_device_info(self) -> None:
        """Update cached device info for entities."""
        device = getattr(self.data, "device", None)
        info = getattr(device, "info", None)
        self._device_info = {
            "sw_version": getattr(device, "model_fw", None),
            "hw_version": getattr(device, "esp_fw", None),
            "model": getattr(info, "model_id", None) if info else None,
        }

    @property
    def vendor(self):
        return self._vendor

    async def _handle_telemetry(self, state: GrillState) -> None:
        self.data = state
        self._update_device_info()
        self.async_set_updated_data(self.data)
