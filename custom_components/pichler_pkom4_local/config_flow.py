"""Validate local access without collecting a cloud password."""

import voluptuous as vol
from homeassistant import config_entries

from . import DOMAIN
from .client import Pkom4Client, Pkom4Error

SCHEMA = vol.Schema(
    {vol.Required("host"): str, vol.Required("device_id"): str, vol.Required("email"): str}
)


def validate(data):
    client = Pkom4Client(data["host"], data["device_id"], data["email"])
    try:
        client.read()
    finally:
        client.close()


class Pkom4ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = {k: v.strip() for k, v in user_input.items()}
            await self.async_set_unique_id(data["device_id"])
            self._abort_if_unique_id_configured()
            try:
                await self.hass.async_add_executor_job(validate, data)
            except (Pkom4Error, ValueError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Pichler PKOM4", data=data)
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
