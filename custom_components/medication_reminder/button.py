"""Button platform.

Two button types:
  * a one-tap "refill to full" per tracked medication supply (fires
    EVENT_SUPPLY_REFILL; the matching supply number restocks to its
    configured refill-to amount), and
  * a "Log dose" button per as-needed (PRN) dose (fires EVENT_DOSE_LOGGED;
    the matching supply decrements by its per-dose amount on every press).
    PRN doses have no schedule, so the daily on/off switch never counts them;
    this button records a dose each time it is pressed, which also supports
    meds taken several times a day.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    CONF_DOSES,
    CONF_MEDS,
    CONF_PATIENT,
    CONF_SCHEDULE_TYPE,
    CONF_SUPPLIES,
    CONF_SUPPLY_MED,
    CONF_TIME,
    DOMAIN,
    EVENT_DOSE_LOGGED,
    EVENT_SUPPLY_REFILL,
    SCHEDULE_PRN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a refill button per supply, plus a log-dose button per PRN dose."""
    patient: str = entry.data[CONF_PATIENT]
    supplies: list[dict[str, Any]] = entry.options.get(CONF_SUPPLIES, [])
    doses: list[dict[str, Any]] = entry.options.get(CONF_DOSES, [])

    entities: list[ButtonEntity] = [
        MedicationRefillButton(entry, patient, str(supply[CONF_SUPPLY_MED]).strip())
        for supply in supplies
    ]
    entities.extend(
        MedicationLogDoseButton(
            entry, patient, str(dose[CONF_TIME])[:5], str(dose[CONF_MEDS])
        )
        for dose in doses
        if (dose.get(CONF_SCHEDULE_TYPE) or "") == SCHEDULE_PRN
    )
    async_add_entities(entities)


class MedicationRefillButton(ButtonEntity):
    """One-tap restock of a medication supply to its refill-to amount."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:package-variant-plus"

    def __init__(self, entry: ConfigEntry, patient: str, med: str) -> None:
        self._patient = patient
        self._med = med
        self._attr_name = f"{med} refill"
        self._attr_unique_id = f"{entry.entry_id}_refill_{slugify(med)}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": patient,
            "manufacturer": "Medication Reminder",
        }

    async def async_press(self) -> None:
        """Tell the matching supply to restock to full."""
        self.hass.bus.async_fire(
            EVENT_SUPPLY_REFILL,
            {"patient": self._patient, "medication": self._med},
        )


class MedicationLogDoseButton(ButtonEntity):
    """Record one as-needed (PRN) dose; decrements supply on every press."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:pill"

    def __init__(self, entry: ConfigEntry, patient: str, time: str, meds: str) -> None:
        self._patient = patient
        self._meds = meds
        self._attr_name = f"Log {meds} dose"
        self._attr_unique_id = f"{entry.entry_id}_logdose_{slugify(time + '_' + meds)}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": patient,
            "manufacturer": "Medication Reminder",
        }

    async def async_press(self) -> None:
        """Log one dose taken; matching supplies decrement by their per-dose amount."""
        self.hass.bus.async_fire(
            EVENT_DOSE_LOGGED,
            {"patient": self._patient, "medications": self._meds},
        )
