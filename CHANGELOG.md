# Changelog

## 1.6.1

- Climate and water heater entities use the `native_` temperature properties introduced in Home Assistant 2026.11, removing the deprecation warnings ahead of the 2027.11 removal.
- Minimum Home Assistant version is now 2026.11.0.

## 1.6.0

- Dedicated `sourdough_sidekick` integration domain and folder.
- Sourdough Sidekick branding with local light/dark icons and wordmarks.
- Status, recipe, goal schedule, crock presence, and named timer sensors.
- Capability-driven sound, brightness, and temperature settings.
- Optional mode-service `disabled` flag handled correctly.
- Manual firmware installation with eligibility checks and completion monitoring.
- Optional dashboard generator, theme, and notification blueprint.
- HACS repository metadata and validation workflows.

Sound, brightness, and firmware installation have been confirmed on the owner's device. Other capabilities depend on the cloud services exposed by each device.
