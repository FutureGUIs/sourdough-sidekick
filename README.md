# Sourdough Sidekick for Home Assistant

![Sourdough Sidekick](custom_components/sourdough_sidekick/brand/logo.png)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FutureGUIs&repository=sourdough-sidekick&category=integration)
[![Validate](https://github.com/FutureGUIs/sourdough-sidekick/actions/workflows/validate.yml/badge.svg)](https://github.com/FutureGUIs/sourdough-sidekick/actions/workflows/validate.yml)

Monitor your Sourdough Sidekick and manage supported settings through the SmartHQ cloud API. This is an independent community integration, not an official GE Appliances or FirstBuild release. An internet connection and SmartHQ account are required.

## Features

- Starter mode/status, feeding recipe amounts and ratios, and crock presence.
- Goal weekday/time, next-feed timer, full-crock timer, and time since completion.
- Sound, display brightness, temperature units, and temperature offset when exposed by the device's public API.
- Firmware update entities with manual installation, eligibility checks, and version confirmation.
- Live cloud updates and local Sourdough Sidekick icons for light/dark mode.
- Optional dashboard generator, cream/brown theme, and notification blueprint.

Sound, brightness, and firmware installation have been confirmed on the owner's Sidekick. Actual services and commands depend on device firmware and SmartHQ API support. Starting a feeding cycle or changing the feeding mode still happens on the appliance.

## Install with HACS

Requires **Home Assistant 2026.3 or newer** and HACS.

[Open this repository in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=FutureGUIs&repository=sourdough-sidekick&category=integration)

Or add it manually:

1. In HACS, open the menu and select **Custom repositories**.
2. Add `https://github.com/FutureGUIs/sourdough-sidekick` with category **Integration**.
3. Find **Sourdough Sidekick** and download it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → Sourdough Sidekick**.

HACS installs only `custom_components/sourdough_sidekick`. The optional theme, dashboard helper, and notification blueprint require the additional steps below. This repository is a HACS custom repository; it is not yet included in the default marketplace catalog.

### Existing manual installations

If you already use the `sourdough_sidekick` domain, HACS can manage the same component folder. Keep your existing account entry, install from HACS, and restart. Back up first; do not remove a working entry just to switch installation methods.

For the earlier `smarthq`-domain build, remove the old integration entry and folder before adding this integration. This release does not migrate old entries. New entity IDs may require changes to dashboards/automations.

## SmartHQ account setup

1. Pair your Sidekick in the official SmartHQ app.
2. Sign in at the [SmartHQ Developer Portal](https://developer.smarthq.com/) using the same account.
3. Open **Apps → Add app** and choose a globally unique machine name.
4. Set the callback URL to exactly:

   ```text
   https://my.home-assistant.io/redirect/oauth
   ```

5. In Home Assistant, add Application credentials for **Sourdough Sidekick**, using the developer app's Client ID and Client Secret.
6. Add the integration and complete authorization. When prompted by My Home Assistant, choose your own HA server URL.

Enter secrets directly in Home Assistant. Do not commit them or paste them into issues. The callback URL remains the same when your server has a custom hostname.

## Optional dashboard, theme, and notifications

See [manual setup and extras](docs/manual-setup.md).

- `tools/make_dashboard.py` reads your actual entity IDs and produces a dashboard using built-in cards. It prompts privately for an HA access token and performs a read-only states request.
- `themes/sourdough_sidekick.yaml` provides the website-inspired cream/brown palette.
- `www/sourdough_sidekick` provides dashboard images; integration icons are already installed by HACS.
- `blueprints/automation/sourdough_sidekick/sidekick_notifications.yaml` provides ready/full-crock notification setup.

No firmware is installed automatically. The explicit Install action refreshes device state, requires a supported/enabled firmware service and an online, idle device, and monitors the result. It does not resend an install command after a reboot disconnection.

## Troubleshooting

- Ensure the Sidekick is online in the official SmartHQ app.
- Missing controls can mean the public API does not expose that feature; the app may have additional capabilities.
- For brightness or sound, the integration only offers device-advertised options. An explicitly disabled setting remains blocked.
- Cancel the active appliance mode before attempting firmware installation.
- The `sourdough_sidekick.diagnose` action can inspect advertised services. Remove secrets and account/device identifiers before sharing output.
- Report problems in [GitHub Issues](https://github.com/FutureGUIs/sourdough-sidekick/issues).

## Development and validation

```text
python -m unittest discover -s tests -v
python -m compileall -q custom_components/sourdough_sidekick
```

There are 39 portable tests. The firmware tests use mocked Home Assistant framework objects and mocked cloud transport; they do not install firmware. The GitHub workflow runs these tests, HACS validation, and hassfest. Portable tests do not replace a full Home Assistant runtime test.

Read the [changelog](CHANGELOG.md) for version history.

## Credits and license

Derived from [GE Appliances' SmartHQ integration](https://github.com/geappliances/geappliances-smarthq-integration), based on commit `6e52439b1366a4edb77118ae446c11bf6e0570d3`. The original BSD-3-Clause copyright notice and license are retained in [LICENSE](LICENSE); the original documentation is retained in [UPSTREAM_README.md](UPSTREAM_README.md).

Product names and artwork belong to their respective owners. The included Sidekick artwork comes from the [product website](https://www.sourdoughsidekick.com/); its use here identifies the device and does not imply endorsement.
