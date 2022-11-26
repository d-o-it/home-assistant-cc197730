"""The Conrad Components 197730 integration."""
from __future__ import annotations

import logging
from typing import Any
import serialio
from .cc197730 import CC197730

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant

from .const import HUB, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Conrad Components 197730 from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    if entry.entry_id in hass.data[DOMAIN]:
        return False

    # create connection
    sio = serialio.serial_for_url(entry.data[CONF_URL])
    await sio.set_timeout(1.0)
    hub = CC197730(sio)

    _LOGGER.info('Connection created to "%s"', entry.data[CONF_URL])
    hass.data[DOMAIN][entry.entry_id] = {HUB: hub}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
