"""Support for Conrad Components 197730 switches."""
from __future__ import annotations

import logging
from typing import Any
from .cc197730 import CC197730
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_OFF, STATE_ON
from .const import DOMAIN, HUB

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


def create_cc197730_switch_entity(
    config_entry: ConfigEntry, hub: CC197730, card: int, relay: int, is_on: bool
) -> CC197730Relay:
    """Set up an entity for this domain."""
    _LOGGER.info(
        "Adding CC197730 switch card %i relay %i with state %s",
        card,
        relay,
        STATE_ON if is_on else STATE_OFF,
    )
    return CC197730Relay(config_entry.entry_id, hub, card, relay, is_on)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LCN switch entities from a config entry."""

    entities = []

    hub: CC197730 = hass.data[DOMAIN][config_entry.entry_id][HUB]
    states = await hub.get_states()
    for state in states:
        entities.append(
            create_cc197730_switch_entity(
                config_entry, hub, state.card, state.relay, state.is_on
            )
        )

    async_add_entities(entities)


class CC197730Relay(SwitchEntity):
    """Representation of a LCN switch for relay ports."""

    def __init__(
        self, entry_id: str, hub: CC197730, card: int, relay: int, is_on: bool
    ) -> None:
        """Initialize the LCN switch."""
        self.entry_id = entry_id
        self.hub = hub
        self.card = card
        self.relay = relay
        self._attr_name = f"K{card}R{relay}"
        self._attr_unique_id = f"{card}.{relay}"
        self._is_on = is_on

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        try:
            await self.hub.set(self.card, self.relay)
        except ConnectionRefusedError as ex:
            _LOGGER.exception(ex.strerror)
        else:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        try:
            await self.hub.clear(self.card, self.relay)
        except ConnectionRefusedError as ex:
            _LOGGER.error(ex.strerror)
        else:
            self._is_on = False
            self.async_write_ha_state()
