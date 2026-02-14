"""Constants for the Pecron integration."""

from typing import Final

DOMAIN: Final = "pecron"

# Configuration
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_REGION: Final = "region"
CONF_REFRESH_INTERVAL: Final = "refresh_interval"

# Defaults
DEFAULT_REFRESH_INTERVAL: Final = 600  # 10 minutes in seconds
DEFAULT_REGION: Final = "US"

# Supported regions
REGIONS: Final = ["US", "EU", "CN"]

# Device attributes
ATTR_DEVICE_KEY: Final = "device_key"
ATTR_PRODUCT_KEY: Final = "product_key"
ATTR_PRODUCT_NAME: Final = "product_name"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"

# Sensor types
SENSOR_BATTERY_PERCENTAGE: Final = "battery_percentage"
SENSOR_TOTAL_INPUT_POWER: Final = "total_input_power"
SENSOR_TOTAL_OUTPUT_POWER: Final = "total_output_power"
SENSOR_REMAINING_CHARGING_TIME: Final = "remaining_charging_time"
SENSOR_REMAINING_DISCHARGING_TIME: Final = "remaining_discharging_time"
SENSOR_AC_OUTPUT_VOLTAGE: Final = "ac_output_voltage"
SENSOR_AC_OUTPUT_POWER: Final = "ac_output_power"
SENSOR_AC_OUTPUT_FREQUENCY: Final = "ac_output_frequency"

# Switch types
SWITCH_AC: Final = "ac_switch"
SWITCH_DC: Final = "dc_switch"
SWITCH_UPS: Final = "ups_status"

# Services
SERVICE_SET_PROPERTY: Final = "set_property"
ATTR_PROPERTY_CODE: Final = "property_code"
ATTR_VALUE: Final = "value"
