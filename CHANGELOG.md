# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.5] - 2026-02-15

### Fixed
- **Eliminated UI flicker during switch toggles**
  - Problem: Switches showed ON → OFF → ON pattern when toggling
  - Root cause: Immediate coordinator refresh returned stale state, clearing optimistic update
  - Solution: 20-second settling period keeps optimistic state while device processes change
  - Stale coordinator updates ignored during settling period
  - UI now shows smooth ON/OFF transitions without flickering back to old state
- Switch state synchronization now rock-solid with optimistic updates + settling period + delayed refreshes

## [0.3.4] - 2026-02-15

### Fixed
- **Enhanced switch state synchronization** with delayed refreshes
  - Added automatic refreshes at 5 seconds and 15 seconds after toggle
  - Accounts for device processing delay
  - Ensures UI eventually syncs even if optimistic update doesn't trigger
  - Multiple refresh attempts catch slow device responses
- Combines optimistic updates (instant feedback) with scheduled polling (guaranteed sync)

## [0.3.3] - 2026-02-15

### Fixed
- **Critical**: Switch state not updating in UI after toggle
  - Implemented optimistic UI updates for instant feedback
  - UI now updates immediately when toggling AC/DC switches
  - State reverts automatically if API call fails
  - Background coordinator refresh confirms actual device state
- Previous behavior: UI showed stale state until next scheduled refresh (up to 10 minutes)
- New behavior: UI updates instantly, confirmed by API within seconds

## [0.3.2] - 2026-02-15

### Added
- **Smart Time Sensor Logic**: Time to Full and Time to Empty sensors now intelligently show N/A based on device state
  - **IDLE** (no power flow): Both sensors show N/A
  - **CHARGING** (input > 0, no output): Show Time to Full, N/A for Time to Empty
  - **DISCHARGING** (output > 0, no input): N/A for Time to Full, show Time to Empty
  - **UPS MODE** (both input and output): Show both values (charging time + runtime if input lost)
- **Always Show Both Sensors**: Both time sensors always appear regardless of TSL availability
- **Robust Edge Case Handling**:
  - Missing properties: Pass through N/A
  - Zero values: Show 0 (indicates battery full/empty, not N/A)
  - Negative power values: Treated as 0 (measurement errors)
  - None/missing power values: Treated as 0

### Changed
- Time sensors bypass TSL filtering (always created)
- Time sensor values are now context-aware instead of raw API values

### Developer
- Added 18 comprehensive unit tests for time sensor logic
- All device states tested (idle, charging, discharging, UPS mode)
- Edge cases: missing properties, zero values, negative/None power values
- Total test count: 43 (all passing)

## [0.3.1] - 2026-02-15

### Fixed
- **Critical**: TSL filtering was too strict, causing switches and some sensors to not appear after integration reload
- TSL property codes use `_hm` suffix (e.g., `ac_switch_hm`) but API maps them to properties without suffix (e.g., `ac_switch`)
- Filtering logic now checks both `property_name` and `property_name_hm` variants
- Switches (AC Output, DC Output) now appear correctly
- UPS Mode binary sensor now appears correctly
- All supported entities are now created properly

### Impact
If you upgraded to v0.3.0 and don't see your switches:
1. Update to v0.3.1
2. Reload the integration (Settings → Devices & Services → Pecron → three dots → Reload)
3. Switches and missing sensors will now appear

## [0.3.0] - 2026-02-14

### Added
- **Controllable Switch Entities**: AC and DC outputs are now controllable switches (previously read-only binary sensors)
  - Turn AC/DC outputs on/off directly from Home Assistant
  - Create automations to control power outputs based on conditions
  - Enhanced error handling with persistent notifications on control failure
- **Advanced Control Service**: New `pecron.set_property` service for power users
  - Control any writable device property via automations or scripts
  - TSL validation ensures only valid properties are modified
  - Auto-converts value types (boolean strings, numbers)
  - Detailed error feedback for troubleshooting
- **TSL-Based Dynamic Discovery**: Integration now queries device capabilities
  - Only creates entities for properties the device actually supports
  - No more 'unavailable' entities for unsupported features
  - Automatically supports new device models without code changes
  - Logs discovered readable and writable properties for diagnostics

### Changed
- Upgraded to unofficial-pecron-api v0.2.0 (adds control capabilities)
- AC and DC outputs moved from binary_sensor platform to switch platform
- Binary sensors now only include UPS Mode and Online status (read-only properties)

### Fixed
- Token refresh now triggers correctly during property fetch failures (not just initial device fetch)
- Authentication errors during `get_device_properties()` now properly reset API and retry
- Case-insensitive detection of authentication errors (5032, token, 401, unauthorized, authentication)

### Developer
- Added comprehensive test suite for token refresh scenarios (16 tests, all passing)
- Improved test coverage for coordinator retry logic
- Enhanced logging for token refresh operations

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
