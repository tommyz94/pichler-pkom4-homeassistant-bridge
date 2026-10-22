# Pichler PKOM4 Local

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1%2B-18BCF2?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?logo=homeassistantcommunitystore&logoColor=white)](https://github.com/hacs/integration)
[![Local polling](https://img.shields.io/badge/IoT%20class-Local%20polling-78A55A)](#connection-and-privacy)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue)](LICENSE)

Local Home Assistant integration for **Pichler PKOM⁴** ventilation, heating, cooling, and domestic hot water systems.

Monitor your unit and control its operating settings directly from Home Assistant through the built-in Micro Nabto gateway. No cloud password, Modbus adapter, or separate bridge service is required.

This is an independent community integration, not affiliated with or endorsed by Pichler.

## Features

- **21 sensors** for temperatures, airflow, power, energy, operating settings, and diagnostics.
- **9 controls** for operating mode, ventilation, temperature setpoints, cooling, hot water, and holidays.
- **Local communication** over your home network, with readings every 30 seconds.
- **Verified commands** with device readback rather than optimistic state updates.
- **UI configuration** with English and Italian entity names. No YAML required.

## Compatibility

| Requirement | Details |
| --- | --- |
| Home Assistant | 2026.1.0 or later |
| Device | Pichler PKOM4 with a compatible legacy Micro Nabto gateway |
| Network | Home Assistant must be able to reach the gateway's local IPv4 address on UDP port 5570 |
| Device access | Full Nabto ID and an account email already authorized on the unit |

Tested on a PKOM4 with an integrated hot water tank and a Nabto model 1030 gateway. Compatibility with other gateway models and firmware versions has not yet been established. **Nabto Edge 5-only devices are not supported.**

## Installation

### HACS

This integration is available as a **custom repository**.

1. Open **HACS** in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Add the following URL and select **Integration** as the category:

   ```text
   https://github.com/tommyz94/pichler-pkom4-homeassistant-bridge
   ```

4. Find **Pichler PKOM4 Local** in HACS and download it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and search for **Pichler PKOM4 Local**.

### Manual installation

1. Download this repository.
2. Copy the `custom_components/pichler_pkom4_local` directory into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Add **Pichler PKOM4 Local** from **Settings → Devices & services**.

## Configuration

The setup dialog asks for three values:

| Field | Description |
| --- | --- |
| Local IP address | The PKOM4 gateway's IPv4 address on your home network. A DHCP reservation is recommended. |
| Full Nabto ID | The complete device identifier shown in PICHLERluft. An abbreviated ID ending in an ellipsis is not sufficient. |
| Account email | The email address of an account already authorized to access the device. No account password is requested. |

Setup checks the device identity and model before adding the integration. Once connected, all entities are grouped under a single PKOM4 device.

## Controls

| Control | Entity type | Available settings |
| --- | --- | --- |
| Operating mode | Select | Off, Summer, Winter, Automatic, Holiday |
| Ventilation | Select | Automatic, levels 1–4 |
| Room temperature setpoint | Number | 10–30 °C, in 0.5 °C steps |
| Cooling temperature setpoint | Number | 15–40 °C, in 0.5 °C steps |
| Cooling permission | Select | No, Yes, Eco |
| Hot water setpoint | Number | 20–75 °C, in 0.5 °C steps |
| Hot water boost | Switch | Request rapid hot water heating |
| Hot water electric heating | Switch | Allow electric heating of the hot water tank |
| Holiday end | Date | Set the holiday end date |

For holiday operation, set the end date before selecting **Holiday** mode. The room temperature setpoint is shared with the holiday temperature setting on the device.

The electric heating switch controls **permission to use the heater**; its state does not indicate that the heater is currently drawing power.

Controls use standard Home Assistant entities and can be added to dashboards, scripts, and automations. Commands are sent only when a control is used, including by an automation. Setup, startup, and routine polling do not change device settings.

### Command confirmation

Each write is validated, sent to the unit, and checked against a fresh device reading. If the resulting value does not match the request, the integration reports an error. Failed writes are not automatically retried.

Multiple setting changes are sent as separate commands, not as an atomic transaction. If a command fails, check the current device state before retrying a sequence.

## Sensors

| Category | Measurements |
| --- | --- |
| Air temperatures | Room, outdoor, supply, extract, and exhaust air |
| Hot water | Tank middle and bottom temperatures |
| Airflow | Supply and extract airflow, in m³/h |
| Power | Climate compressor, hot water compressor, ventilation, and calculated total power, in W |
| Energy | Cumulative energy consumption, in kWh |
| Operating settings | Current fan level, ventilation setting, room temperature setpoint, and hot water setpoint |
| Diagnostics | Raw operating mode, fault code, and status word |

The total power sensor is calculated from the three reported power components. The energy sensor is a cumulative counter, not a daily consumption figure.

## Known limitations

### Automatic ventilation

On the tested firmware, selecting **Automatic** ventilation is acknowledged by the gateway, but the readable setting continues to report the previous manual level. The same behavior was observed after selecting Automatic in the official app.

The option remains available, but the integration reports an unconfirmed command if the requested setting cannot be read back. Manual levels 1–4 have been verified. Behavior on other firmware versions may differ.

### Feature coverage

The integration supports the operating controls listed above. It does not expose weekly schedules, installer parameters, counter resets, cloud account management, or a filter-life estimate. The filter counter's conversion to remaining days has not been verified.

Hardware testing has confirmed command acceptance and register readback. It does not establish the thermal performance or completion of a full heating or cooling cycle.

## Troubleshooting

### Setup cannot connect

- Check that Home Assistant can reach the gateway's local IP address. Being able to use PICHLERluft remotely does not establish local connectivity from Home Assistant.
- Confirm the full Nabto ID and use an email already authorized on the device.
- Check firewall or VLAN rules for UDP port 5570 between Home Assistant and the gateway.
- Confirm that the gateway uses the supported legacy Micro Nabto protocol.

### Entities become unavailable

When a read fails, the entities become unavailable. The next polling attempt establishes a new session. If the problem persists, check the gateway's network connection and whether its IP address has changed.

### A command is not confirmed

Check the actual setting in Home Assistant and PICHLERluft before retrying. For Automatic ventilation, see the firmware limitation above.

### Reporting an issue

Open a [GitHub issue](https://github.com/tommyz94/pichler-pkom4-homeassistant-bridge/issues) with your Home Assistant version, integration version, gateway model or firmware if known, and steps to reproduce the problem. Include relevant error messages, with personal information removed.

Do not publish account emails, Nabto IDs, network captures, or credentials.

## Connection and privacy

Device communication stays between Home Assistant and the PKOM4 gateway. The integration does not contact Pichler, LS Control, or Nabto cloud services, and does not send device configuration to this project. Home Assistant and HACS still download code and dependencies during installation and updates.

The IP address, Nabto ID, and authorized email are stored in your Home Assistant configuration. The local Micro Nabto connection identifies the client by email and uses unencrypted traffic with checksums. Keep it on a trusted network and do not expose UDP port 5570 to the internet.

## Contributing

Bug reports, compatibility reports, and pull requests are welcome. Use synthetic data in tests and remove personal identifiers from logs and examples.

To run the development checks:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Automated tests use simulated transports and do not communicate with a real device.

## License and acknowledgements

Licensed under [GPL-3.0-or-later](LICENSE).

Micro Nabto framing is provided by [GenvexNabto](https://github.com/superrob/genvexnabto), with PKOM4-specific register mappings in this integration. See [Third-party notices](THIRD_PARTY_NOTICES.md) for details.
