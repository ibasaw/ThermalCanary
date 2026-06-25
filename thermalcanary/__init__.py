__version__ = '1.1.8'

# Fixed app UUID — passed as --app-id=<UUID> on every launch.
# Used to identify and kill running instances via `pgrep -f <APP_UUID>` — zero false positives.
# Derived from: uuid5(NAMESPACE_DNS, "thermalcanary.ibasaw.io")
APP_UUID = '99e18195-0d42-5165-826c-b6a04d5ed4d4'
