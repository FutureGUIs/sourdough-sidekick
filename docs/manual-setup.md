# Sourdough Sidekick — version 1.6.0

The custom component directory and Home Assistant integration domain are now both **sourdough_sidekick**:

```text
/config/custom_components/sourdough_sidekick/
```

This is a fresh-install release. No account or entity migration is included.

## Replace the earlier smarthq-based installation

1. In Home Assistant, remove the earlier integration entry under Settings → Devices & services. Its display name may already be Sourdough Sidekick, but it belongs to the old `smarthq` domain.
2. Remove the old `/config/custom_components/smarthq` folder.
3. Extract the ZIP and copy its `custom_components/sourdough_sidekick` folder to your HA config directory.
4. Restart Home Assistant.
5. Under Settings → Devices & services → Application credentials, add credentials for **Sourdough Sidekick**, using your existing developer Client ID and Client Secret. The same developer app can be reused.
6. Add the **Sourdough Sidekick** integration and complete account authorization again.

The SmartHQ developer app callback remains exactly `https://my.home-assistant.io/redirect/oauth`. Choose `https://homeassistant.example.com` as your Home Assistant instance when prompted. Keep secrets out of chat and source files.

Entity IDs may change because this is a new integration entry. Regenerate the dashboard and reselect entities in existing automations as needed. Do not leave both integrations enabled for the same device.

## Features included

- Sidekick state, mode, recipe ratios and amounts, feeding frequency, and crock presence.
- Goal Schedule combines the reported weekday and time, without inventing a calendar date.
- Clearly named Until Next Feed, Until Crock Full, and Since Done timers.
- Sound, brightness, and temperature-unit controls use device-advertised options. Brightness includes the optional `disabled` flag fix confirmed on your device.
- Temperature-offset control when advertised by the API.
- Wi-Fi/device firmware update entities, current/available versions, status tracking, and manual Install actions. Installation is sent only after a fresh online/idle/enabled/capability check; reboot disconnections never resend the install command. Completion requires a confirmed changed firmware version. There are no automatic firmware installations.
- Original S-shaped brand icon and light/dark wordmarks matching the product website.

SmartHQ remains the actual account/API provider. Its hostnames and `cloud.smarthq.*` protocol tokens intentionally remain unchanged. Home Assistant actions now use `sourdough_sidekick`, such as `sourdough_sidekick.diagnose`.

## Dashboard and theme

1. Copy `www/sourdough_sidekick` to `/config/www/sourdough_sidekick`.
2. Copy `themes/sourdough_sidekick.yaml` to `/config/themes/sourdough_sidekick.yaml`.
3. If themes are not already configured, merge this into the existing `frontend:` section of `configuration.yaml`:

   ```yaml
   frontend:
     themes: !include_dir_merge_named themes
   ```

4. Restart HA or reload themes with `frontend.reload_themes` if the directory was already configured.
5. From the extracted package directory on a computer with Python, run:

   ```text
   python tools/make_dashboard.py --url https://homeassistant.example.com
   ```

The tool privately requests a Home Assistant long-lived access token, reads only `/api/states`, and saves `sidekick-dashboard.yaml` using your real entity IDs. It does not store the token or modify your server. Revoke the temporary token afterward if desired. Create a new empty dashboard and paste the generated file into its Raw configuration editor. The generated JSON is also valid YAML.

The theme uses the website's cream `#F0EBE1`, brown `#A39382`, and beige `#E2D3C0`, and applies to the Sidekick view. The DM Sans font has system-font fallbacks. Local integration brand images require Home Assistant 2026.3 or newer; refreshing the browser after restarting may be needed to clear old cached images.

## Notifications

Copy `blueprints/automation/sourdough_sidekick/sidekick_notifications.yaml` to that path under `/config/`. Create an automation from the blueprint, choose the new Starter Status sensor and optional crock.full alert sensor, and choose your notification actions. The default is an HA persistent notification; for mobile push use `{{ sidekick_message }}` as the message of your mobile app action. Initial unknown/unavailable state transitions are ignored. No appliance commands are sent by the blueprint.

## Validation

All 39 portable tests pass under the new domain. Tests include firmware entity methods with mocked Home Assistant/SmartHQ transport, reboot interruptions, command rejection, busy/offline/disabled checks, settings validation, typed readings, and dashboard IDs. Python syntax, JSON/YAML, PNG brand dimensions/transparency, and archive layout are checked. Full Home Assistant runtime tests are not available in this environment. The new domain has not been installed on your server.

Run the portable tests from this directory:

```text
python -m unittest discover -s tests -v
```

## Source and branding

Based on GE Appliances' SmartHQ integration at commit `6e52439b1366a4edb77118ae446c11bf6e0570d3`: https://github.com/geappliances/geappliances-smarthq-integration

Upstream BSD-3-Clause license and README are preserved as LICENSE and UPSTREAM_README.md. This modified package is not an official GE release. Brand artwork comes from the original Simple_Logo_Brown.png, Simple_Logo_Cream.png, and full brown/cream logo assets on https://www.sourdoughsidekick.com/; artwork was resized without redrawing.

API references: https://docs.smarthq.com/data-model/devices/sourdough-starter/ and https://docs.smarthq.com/data-model/services/cloud.smarthq.service.firmware.v1/
