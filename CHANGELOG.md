# Changelog

## 0.1.0

- Local Micro Nabto connection with device identity verification.
- 21 sensors and all controls exposed on the tested PKOM4 app screens.
- Operation modes, holiday end date, ventilation levels, heating/cooling setpoints,
  cooling permission, domestic hot-water setpoint, electric heating and boost.
- Acknowledgement and readback validation; no automatic command retries.
- Italian and English translations, UI configuration and HACS metadata.
- Known limitation: automatic ventilation can acknowledge a command without
  confirming a change in the device's readable state; the integration reports this.
