from homeassistant.const import Platform

DOMAIN = "camp_chef"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CLIMATE, Platform.NUMBER]

CONF_ADDRESS = "address"
CONF_VENDOR = "vendor"
CONF_NAME = "name"

DEFAULT_MIN_TEMP_F = 160
DEFAULT_MAX_TEMP_F = 500
SMOKE_MIN_DEFAULT = 1
SMOKE_MAX_DEFAULT = 10
