# Pecron Home Assistant Integration

A Home Assistant community integration for Pecron portable power stations. Monitor battery levels, power input/output, and switch states in real-time.

## Features

- **Real-time monitoring** of battery percentage, input/output power, and switch states
- **Multi-device support** for accounts with multiple Pecron stations
- **Configurable refresh rate** for polling device properties
- **Switch entities** for AC, DC, and UPS mode control (read-only for now)
- **Sensor entities** for all key metrics (battery %, power, time estimates)
- **Support for multiple regions** (US, EU, CN)

## Installation

### Via HACS

1. Go to **HACS** → **Integrations** → **Custom repositories**
2. Add this repository: `https://github.com/jsight/ha-pecron`
3. Select **Pecron** and click **Install**
4. Restart Home Assistant
5. Go to **Settings** → **Devices & Services** → **Create Integration**
6. Search for **Pecron**

### Manual

```bash
git clone https://github.com/jsight/ha-pecron.git
cp -r ha-pecron/custom_components/pecron ~/.homeassistant/custom_components/
# Restart Home Assistant
```

## Configuration

Add via the UI:
1. **Settings** → **Devices & Services** → **Create Integration**
2. Select **Pecron**
3. Enter:
   - Email
   - Password
   - Region (US, EU, or CN)
   - (Optional) Custom refresh interval

## Requirements

- Home Assistant 2024.1 or later
- Python 3.11+

## Issues & Support

For bugs, feature requests, or questions, please open an issue on GitHub.

## Disclaimer

This integration is not affiliated with or endorsed by Pecron. It uses the unofficial API which was reverse-engineered from the Pecron Android app. Use at your own risk.

## License

MIT
