from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_VENDOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import CampChefCoordinator

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Camp Chef integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Camp Chef from a config entry."""
    coordinator = CampChefCoordinator(
        hass,
        address=entry.data[CONF_ADDRESS],
        vendor_key=entry.data.get(CONF_VENDOR, "campchef"),
        name=entry.data.get(CONF_NAME, entry.title),
        entry_id=entry.entry_id,
    )
    await coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: CampChefCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
