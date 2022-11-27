"""Support for Conrad Components 197730 switches."""
from __future__ import annotations

import logging
from typing import Any
from dataclasses import dataclass

from .cc197730 import CC197730, CC197330State, InvalidResponseException
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, HUB, ATTR_SURGE_MODE

_LOGGER = logging.getLogger(__name__)


def create_cc197730_switch_entity(
    config_entry: ConfigEntry, hub: CC197730, state: CC197330State
):
    """Set up an entity for this domain."""
    _LOGGER.info("Adding CC197730 switch %s", state)
    return CC197730Relay(config_entry.entry_id, hub, state)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LCN switch entities from a config entry."""

    entities = []

    hub: CC197730 = hass.data[DOMAIN][config_entry.entry_id][HUB]
    states: list[CC197330State] = await hub.get_states()
    for state in states:
        entities.append(create_cc197730_switch_entity(config_entry, hub, state))

    async_add_entities(entities)


@dataclass
class SurgeEntityDescription(SwitchEntityDescription):
    """A class that describes surge entities."""


class CC197730Relay(SwitchEntity):
    """Representation of a Conrad Components 197730 switch for relay ports."""

    entity_description: SurgeEntityDescription
    _attr_mode_surge: bool = False

    @property
    def mode_surge(self) -> bool:
        """Whether the relay is in surge mode."""
        return self._attr_mode_surge

    def __init__(self, entry_id: str, hub: CC197730, state: CC197330State) -> None:
        """Initialize the LCN switch."""
        self.entry_id = entry_id
        self.hub = hub
        self.card = state.card
        self.relay = state.relay
        self.card_name = f"K{self.card}"
        self._attr_name = f"K{self.card}R{self.relay}"
        self._attr_unique_id = f"{self.card}.{self.relay}"
        self._is_on = state.is_on
        self.hw_version = state.hw_version

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.card_name)
            },
            name=self.card_name,
            manufacturer="Conrad Components",
            model="197730",
            hw_version=self.hw_version,
        )

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        try:
            await self.hub.set(self.card, self.relay)
        except ConnectionRefusedError as ex:
            _LOGGER.error(ex.strerror)
        except InvalidResponseException as ex:
            _LOGGER.error(ex.strerror)
        else:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        try:
            await self.hub.clear(self.card, self.relay)
        except ConnectionRefusedError as ex:
            _LOGGER.error(ex.strerror)
        except InvalidResponseException as ex:
            _LOGGER.error(ex.strerror)
        else:
            self._is_on = False
            self.async_write_ha_state()
