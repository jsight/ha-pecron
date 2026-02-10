# Installation Guide

## Prerequisites

- Home Assistant 2024.1 or later
- Python 3.11+
- Valid Pecron account credentials

## Installation Methods

### Method 1: HACS (Recommended)

1. Open Home Assistant
2. Go to **Settings** → **Devices & Services**
3. Click **+ CREATE INTEGRATION**
4. Search for "Pecron"
5. Click **Install**
6. Restart Home Assistant
7. Go to **Settings** → **Devices & Services** → **+ CREATE INTEGRATION**
8. Search for "Pecron" again and select it
9. Enter your Pecron credentials and region

### Method 2: Manual Installation

#### Step 1: Get the Integration Files

Clone the repository to a temporary location:

```bash
cd /tmp
git clone https://github.com/jsight/ha-pecron.git
```

#### Step 2: Locate Your Home Assistant Configuration

Find your Home Assistant config directory. Common locations:

- **Docker/Container**: `/config`
- **Supervised**: `/home/homeassistant/.homeassistant`
- **Core/Virtual Environment**: `~/.homeassistant` or wherever you configured it
- **OS (HAOS)**: You cannot manually install on HAOS; use HACS instead

#### Step 3: Create custom_components Directory (if needed)

```bash
mkdir -p ~/.homeassistant/custom_components
```

Replace `~/.homeassistant` with your Home Assistant config path.

#### Step 4: Copy Integration Files

```bash
cp -r /tmp/ha-pecron/custom_components/pecron ~/.homeassistant/custom_components/
```

Verify the files are in place:

```bash
ls -la ~/.homeassistant/custom_components/pecron/
```

You should see:
- `__init__.py`
- `config_flow.py`
- `sensor.py`
- `binary_sensor.py`
- `const.py`
- `manifest.json`
- `strings.json`

#### Step 5: Verify File Permissions

Ensure the files are readable by the Home Assistant process:

```bash
# If running as a specific user (e.g., homeassistant)
sudo chown -R homeassistant:homeassistant ~/.homeassistant/custom_components/pecron

# Set proper permissions
chmod -R 755 ~/.homeassistant/custom_components/pecron
```

#### Step 6: Restart Home Assistant

```bash
# If running as a service
sudo systemctl restart homeassistant

# Or in Home Assistant UI:
# Settings → System → Restart
```

#### Step 7: Configure the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ CREATE INTEGRATION**
3. Search for "Pecron"
4. If not visible, clear browser cache and refresh
5. Select "Pecron"
6. Enter your credentials:
   - **Email**: Your Pecron account email
   - **Password**: Your Pecron account password
   - **Region**: US, EU, or CN
   - **Refresh Interval** (optional): Polling interval in seconds (default: 60)

## Troubleshooting

### Integration Not Appearing

**Problem**: "Pecron" option doesn't show in the integration creation dialog

**Solutions**:
1. Verify files are in `custom_components/pecron/` with correct names
2. Check file permissions (should be readable by Home Assistant process)
3. Clear browser cache (Ctrl+Shift+Delete) and refresh
4. Check Home Assistant logs for errors:
   - Settings → System → Logs
   - Search for "pecron" (case-insensitive)

### Authentication Errors

**Problem**: "Invalid email or password" error

**Solutions**:
1. Verify your Pecron account credentials
2. Ensure you're using the correct region (US, EU, or CN)
3. Check your Pecron account password hasn't changed
4. If using email aliases, try your primary email
5. Check logs for specific error messages

### Connection Timeout

**Problem**: "Failed to connect to Pecron API" error

**Solutions**:
1. Verify your internet connection
2. Check if the Pecron API is accessible from your network
3. Increase the refresh interval (Settings → Pecron configuration)
4. Check if Pecron servers are experiencing issues
5. Check Home Assistant logs for more details

### Devices Not Showing

**Problem**: Integration configured but no devices appear

**Solutions**:
1. Ensure your Pecron account has at least one registered device
2. Wait 1-2 minutes for the first update to fetch device data
3. Restart Home Assistant
4. Check logs for device fetch errors

### File Permissions Issues

**Problem**: Integration loads but shows permission errors in logs

**Solutions**:
1. Verify the pecron folder is readable:
   ```bash
   ls -la ~/.homeassistant/custom_components/pecron/
   ```
2. Fix permissions if needed:
   ```bash
   sudo chown -R homeassistant:homeassistant ~/.homeassistant/custom_components/pecron
   chmod -R 755 ~/.homeassistant/custom_components/pecron
   ```
3. Restart Home Assistant

## Uninstallation

### Via HACS
1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Find Pecron integration
3. Click the menu (three dots)
4. Select **Uninstall**
5. Restart Home Assistant

### Manual Installation
1. Remove the integration from Home Assistant:
   - Settings → Devices & Services → find Pecron → delete
2. Delete the folder:
   ```bash
   rm -rf ~/.homeassistant/custom_components/pecron
   ```
3. Restart Home Assistant

Replace `~/.homeassistant` with your actual Home Assistant config path.

## Support

For issues, bugs, or feature requests:
- Check the [GitHub Issues](https://github.com/jsight/ha-pecron/issues)
- Open a new issue with:
  - Home Assistant version
  - Integration version
  - Relevant logs (Settings → System → Logs)
  - Steps to reproduce

## Disclaimer

This integration is **not affiliated with or endorsed by Pecron**. It uses an unofficial API that was reverse-engineered from the Pecron Android app. Use at your own risk.
