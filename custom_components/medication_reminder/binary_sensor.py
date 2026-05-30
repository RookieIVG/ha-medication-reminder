"""Binary sensor: all of a patient's doses given today."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PATIENT, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the per-patient 'all doses given' sensor."""
    async_add_entities([AllDosesGivenBinarySensor(entry, entry.data[CONF_PATIENT])])


class AllDosesGivenBinarySensor(BinarySensorEntity):
    """On when every dose for this patient is marked given today."""

    _attr_should_poll = False
    _attr_icon = "mdi:check-all"

    def __init__(self, entry: ConfigEntry, patient: str) -> None:
        self._patient = patient
        self._attr_name = f"{patient} all doses given"
        self._attr_unique_id = f"{entry.entry_id}_all_doses_given"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": patient,
            "manufacturer": "Medication Reminder",
        }

    def _doses(self) -> list:
        """This patient's dose switches (matched by attributes)."""
        return [
            s
            for s in self.hass.states.async_all("switch")
            if s.attributes.get("medications") is not None
            and s.attributes.get("patient") == self._patient
        ]

    @property
    def is_on(self) -> bool | None:
        doses = self._doses()
        if not doses:
            return None
        return all(s.state == "on" for s in doses)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        doses = self._doses()
        total = len(doses)
        given = sum(1 for s in doses if s.state == "on")
        return {
            "total": total,
            "given": given,
            "remaining": total - given,
            "pending": [s.name for s in doses if s.state != "on"],
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_state_changed(event: Event) -> None:
            if not event.data.get("entity_id", "").startswith("switch."):
                return
            new = event.data.get("new_state")
            if new is None or (
                new.attributes.get("patient") == self._patient
                and new.attributes.get("medications") is not None
            ):
                self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen("state_changed", _on_state_changed)
        )
