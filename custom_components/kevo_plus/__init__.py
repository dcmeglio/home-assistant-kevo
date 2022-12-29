# Kevo lock integration
"""The Kevo Plus integration."""
from __future__ import annotations
import asyncio
import uuid


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from aiokevoplus import KevoApi, KevoAuthError

from .const import (
    DOMAIN,
)
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LOCK, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kevo Plus from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    device_id = uuid.UUID(int=uuid.getnode())
    client = KevoApi(device_id)
    await client.login(entry.data.get(CONF_USERNAME), entry.data.get(CONF_PASSWORD))

    coordinator = KevoCoordinator(hass, client, entry)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_config_entry_first_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class KevoCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: KevoApi,
        entry: ConfigEntry,
        devices=None,
    ):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Kevo",
        )
        self.api = api
        self.hass: HomeAssistant = hass
        self.entry = entry
        self._devices = None
        self._device_lock = asyncio.Lock()

    async def get_devices(self):
        async with self._device_lock:
            if self._devices is None:
                try:
                    self._devices = await self.api.get_locks()
                except KevoAuthError:
                    await self.entry.async_start_reauth(self.hass)
            return self._devices

    async def _async_update_data(self):
        await self.api.websocket_connect()
