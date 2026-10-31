"""Sidekick firmware updates through SmartHQ's documented HTTPS command API."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature, UpdateDeviceClass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from .const import DOMAIN
from .dispatcher import SIGNAL_DEVICE_UPDATED
from .sidekick import FIRMWARE, UPGRADE, is_sidekick, firmware_status, firmware_install_error

SCAN_INTERVAL = timedelta(minutes=5)
INSTALL_TIMEOUT = 35 * 60
POLL_SECONDS = 10


async def async_setup_entry(hass, entry, async_add_entities):
    bucket = hass.data[DOMAIN][entry.entry_id]
    coordinator = bucket.get('coordinator')
    entities = []
    for device_id, payload in ((coordinator.data or {}) if coordinator else {}).items():
        item = payload.get('item') or {}
        if not is_sidekick(item):
            continue
        for service in item.get('services', []):
            if service.get('serviceType') != FIRMWARE:
                continue
            if not (service.get('serviceId') or service.get('id')):
                continue
            entities.append(SmartHQFirmwareUpdate(hass, entry, device_id, item, service))
    async_add_entities(entities)


class SmartHQFirmwareUpdate(UpdateEntity):
    """Report cloud firmware state and explicitly install an eligible update."""

    _attr_has_entity_name = True
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_should_poll = True
    _attr_release_url = 'https://www.sourdoughsidekick.com/pages/support'
    _attr_auto_update = False

    def __init__(self, hass, entry, device_id, item, service):
        self.hass, self._entry, self._device_id = hass, entry, device_id
        self._item, self._service = item, service
        self._service_id = service.get('serviceId') or service['id']
        self._attr_unique_id = f'{DOMAIN}:{device_id}:{self._service_id}:firmware_update'
        component = str(service.get('serviceDeviceType', '')).split('.')[-1]
        self._attr_name = 'Wi-Fi Firmware' if component == 'wifi' else 'Device Firmware'
        self._install_requested = False

    @property
    def _bucket(self):
        return self.hass.data[DOMAIN][self._entry.entry_id]

    def _state(self):
        state = dict(self._service.get('state') or {})
        live = ((self._bucket.get('store') or {}).get(self._device_id) or {}).get('snapshot') or {}
        state.update((live.get('services') or {}).get(self._service_id) or {})
        return state

    @property
    def supported_features(self):
        features = UpdateEntityFeature.PROGRESS
        if UPGRADE in (self._service.get('supportedCommands') or []):
            features |= UpdateEntityFeature.INSTALL
        return features

    @property
    def installed_version(self):
        return self._state().get('versionCurrent')

    @property
    def latest_version(self):
        state = self._state()
        if firmware_status(state) == 'idle':
            return state.get('versionCurrent')
        return state.get('versionAvailable')

    @property
    def has_update(self):
        return firmware_status(self._state()) in ('available', 'delayed', 'error.busy')

    @property
    def in_progress(self):
        return self._install_requested or firmware_status(self._state()) in ('downloading', 'updating')

    @property
    def available(self):
        return bool(self.installed_version)

    @property
    def extra_state_attributes(self):
        state = self._state()
        return {
            'sidekick_device_id': self._device_id,
            'sidekick_role': 'firmware',
            'upgrade_status': firmware_status(state),
            'installation_disabled': state.get('disabled'),
            'component': self._service.get('serviceDeviceType'),
        }

    @property
    def device_info(self):
        return {'identifiers': {(DOMAIN, self._device_id)}}

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_DEVICE_UPDATED.format(device_id=self._device_id), self._signal_update,
        ))

    @callback
    def _signal_update(self):
        self.async_write_ha_state()

    async def async_update(self):
        api = self._bucket['api']
        item = await api.async_get_device_item(self._device_id)
        service = next((s for s in item.get('services', [])
                        if (s.get('serviceId') or s.get('id')) == self._service_id), None)
        if service is None:
            raise HomeAssistantError('Firmware service is no longer present on this device.')
        self._item, self._service = item, service
        # Publish the authoritative REST snapshot so other Sidekick entities
        # also see current state. WebSocket updates continue between polls.
        payload = self._bucket.setdefault('store', {}).setdefault(self._device_id, {})
        services = payload.setdefault('snapshot', {}).setdefault('services', {})
        for svc in item.get('services', []):
            sid = svc.get('serviceId') or svc.get('id')
            if sid:
                services[sid] = {
                    **(svc.get('state') or {}),
                    **{k: svc[k] for k in ('serviceType', 'domainType', 'serviceDeviceType', 'config') if k in svc},
                }
        if item.get('presence'):
            payload['presence'] = {'presence': item['presence']}
        async_dispatcher_send(self.hass, SIGNAL_DEVICE_UPDATED.format(device_id=self._device_id))

    async def async_install(self, version=None, backup=False, **kwargs):
        if version is not None or backup:
            raise HomeAssistantError('SmartHQ supports only the advertised update and does not expose firmware backup.')
        if self._install_requested:
            raise HomeAssistantError('A firmware installation is already being monitored.')
        await self.async_update()
        reason = firmware_install_error(self._service, self._item)
        if reason:
            raise HomeAssistantError(reason)
        initial = self.installed_version
        target = self._state().get('versionAvailable')
        api = self._bucket['api']
        self._install_requested = True
        self.async_write_ha_state()
        try:
            result = await api.async_send_command(
                device_id=self._device_id,
                service_type=self._service['serviceType'],
                domain_type=self._service['domainType'],
                service_device_type=self._service['serviceDeviceType'],
                command={'commandType': UPGRADE},
            )
            if isinstance(result, dict) and result.get('success') is False:
                raise HomeAssistantError('SmartHQ rejected the firmware update request.')
            deadline = asyncio.get_running_loop().time() + INSTALL_TIMEOUT
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(POLL_SECONDS)
                try:
                    await self.async_update()
                except Exception:
                    # The device may briefly disappear while rebooting.
                    # Never repeat the install command on a reconnect.
                    continue
                self.async_write_ha_state()
                state = self._state()
                status = firmware_status(state)
                if status.startswith('error.'):
                    raise HomeAssistantError(f'Sidekick reported firmware update failure: {status}')
                current = state.get('versionCurrent')
                if status == 'idle' and current and current != initial and (not target or current == target):
                    return
            raise HomeAssistantError('Timed out waiting for firmware confirmation. Check SmartHQ before attempting another installation.')
        finally:
            self._install_requested = False
            self.async_write_ha_state()
