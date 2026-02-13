# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.4] - 2026-02-10

### Fixed
- Automatic token refresh when Pecron API authentication expires
- Integration now handles expired tokens gracefully without requiring manual reload or restart
- Added retry logic (up to 2 attempts) to recover from transient authentication failures
- Improved logging to distinguish between initial login and token refresh operations

## [0.2.3] - 2026-02-10

### Added
- Official Pecron integration icon (256x256px and 512x512px for retina displays)
- Integration now has a professional, branded appearance in Home Assistant UI

## [0.2.2] - 2026-02-10

### Fixed
- Fixed TypeError when instantiating options flow - don't pass config_entry argument as base class handles it automatically

## [0.2.1] - 2026-02-10

### Fixed
- Fixed AttributeError in options flow when accessing integration options
- Removed unnecessary `__init__` override in `PecronOptionsFlow` that was trying to set read-only `config_entry` property

## [0.2.0] - 2026-02-10

### Added
- Dynamic device discovery - new devices automatically detected without HA restart
- Configurable refresh interval (1-60 minutes, default: 10 minutes)
- Options flow to change refresh interval after initial setup
- Comprehensive logging for device discovery and data fetching
- Property name validation and debugging
- Retry logic with exponential backoff for initial data fetch
- Persistent notifications for connection issues and missing devices
- Better error differentiation (auth vs connection vs data errors)

### Fixed
- Critical bug where empty dict check prevented entity creation
- Entity descriptions now properly inherit from Home Assistant base classes
- Property validation warnings for missing attributes

### Changed
- Default refresh interval increased from 5 to 10 minutes (reduces API load)
- Integration automatically reloads when refresh interval is changed

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
