from unittest.mock import Mock

import pytest
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant

from custom_components.pichler_pkom4_local import DOMAIN
from custom_components.pichler_pkom4_local.config_flow import Pkom4ConfigFlow


@pytest.mark.asyncio
async def test_config_flow_accepts_only_validated_local_configuration(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = ConfigEntries(hass, {})
    flow = Pkom4ConfigFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.context = {"source": "user"}
    validate = Mock()
    monkeypatch.setattr("custom_components.pichler_pkom4_local.config_flow.validate", validate)
    data = {"host": "10.42.0.20", "device_id": "000000000001", "email": "test@example.invalid"}
    result = await flow.async_step_user(data)
    assert result["type"] == "create_entry"
    assert result["data"] == data
    validate.assert_called_once_with(data)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_config_flow_connection_failure_keeps_form(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = ConfigEntries(hass, {})
    flow = Pkom4ConfigFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.context = {"source": "user"}
    monkeypatch.setattr(
        "custom_components.pichler_pkom4_local.config_flow.validate",
        Mock(side_effect=ValueError("invalid host")),
    )
    result = await flow.async_step_user(
        {"host": "invalid", "device_id": "000000000001", "email": "test@example.invalid"}
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}
    await hass.async_block_till_done()
