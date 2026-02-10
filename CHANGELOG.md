# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-09

### Added
- Initial release of Pecron Home Assistant integration
- Real-time monitoring of battery percentage, input/output power, and switch states
- Multi-device support for accounts with multiple Pecron stations
- Configurable refresh rate for polling device properties
- Switch entities for AC, DC, and UPS mode status (read-only)
- Sensor entities for all key metrics (battery %, power, time estimates)
- Support for multiple regions (US, EU, CN)
- Config flow UI for easy setup
- Manual installation support

### Notes
- Uses unofficial Pecron API (reverse-engineered from Android app)
- Requires Home Assistant 2024.1 or later
- Requires Python 3.11+
