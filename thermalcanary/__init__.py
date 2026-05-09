__version__ = '1.1.0'

# Fixed app UUID — passed as --app-id=<UUID> on every launch.
# Used by install.sh / uninstall.sh to find and kill running instances
# via `pgrep -f <APP_UUID>` — zero false positives, rename-proof.
# Derived from: uuid5(NAMESPACE_DNS, "thermalcanary.ibasaw.io")
APP_UUID = '99e18195-0d42-5165-826c-b6a04d5ed4d4'
