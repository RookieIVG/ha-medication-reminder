"""Diagnostics for the Medication Reminder integration.

Downloadable from the device/entry page; bundles the patient's config and the
current state of every entity the entry created, to make support easy.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    states: dict[str, Any] = {}
    for ent in entities:
        state = hass.states.get(ent.entity_id)
        states[ent.entity_id] = (
            None
            if state is None
            else {"state": state.state, "attributes": dict(state.attributes)}
        )
    return {
        "data": dict(entry.data),
        "options": dict(entry.options),
        "entities": states,
    }
