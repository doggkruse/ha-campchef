from __future__ import annotations

from typing import Any, Dict, Tuple

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
)
from homeassistant.data_entry_flow import FlowResult

from pycampchef import async_discover
from pycampchef.const import VENDOR_CONFIGS

from .const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_VENDOR,
    DOMAIN,
)


class CampChefConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._choices: Dict[str, Tuple[str, str]] = {}
        self._discovered: Dict[str, str] = {}

    def _vendor_from_discovery(self, discovery_info: BluetoothServiceInfoBleak) -> Tuple[str, Any]:
        service_uuids = {uuid.lower() for uuid in discovery_info.service_uuids or []}
        for key, cfg in VENDOR_CONFIGS.items():
            if cfg.service_uuid.lower() in service_uuids:
                return key, cfg
        name = discovery_info.name or ""
        for key, cfg in VENDOR_CONFIGS.items():
            if name.startswith(cfg.adv_name_prefix):
                return key, cfg
        return "campchef", VENDOR_CONFIGS["campchef"]

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        vendor_key, vendor = self._vendor_from_discovery(discovery_info)
        address = discovery_info.address
        name = discovery_info.name or f"{vendor.name} ({address})"

        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=name,
            data={
                CONF_ADDRESS: address,
                CONF_VENDOR: vendor_key,
                CONF_NAME: name,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            name, vendor_key = self._choices[address]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_VENDOR: vendor_key,
                    CONF_NAME: name,
                },
            )

        devices = await async_discover()
        if not devices:
            return self.async_abort(reason="no_devices_found")

        choices: Dict[str, str] = {}
        self._choices = {}
        for dev, name, vendor in devices:
            vendor_key = "campchef"
            for key, cfg in VENDOR_CONFIGS.items():
                if cfg == vendor:
                    vendor_key = key
                    break
            title = name or f"{vendor.name} ({dev.address})"
            choices[dev.address] = f"{title} ({vendor.name})"
            self._choices[dev.address] = (title, vendor_key)

        schema = vol.Schema({vol.Required(CONF_ADDRESS): vol.In(choices)})
        return self.async_show_form(step_id="user", data_schema=schema)
