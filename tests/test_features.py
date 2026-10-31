"""Portable logic tests and firmware entity tests with a mocked HA framework."""
import asyncio
import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from enum import IntFlag
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).parents[1] / 'custom_components/sourdough_sidekick'
PACKAGE = '_sidekick_feature_test'
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = pkg

def load(name):
    spec = importlib.util.spec_from_file_location(PACKAGE + '.' + name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

helpers = load('sidekick')

class Features(IntFlag):
    INSTALL = 1
    PROGRESS = 2

class Entity:
    def async_write_ha_state(self):
        pass

class HAError(Exception):
    pass

modules = {name: types.ModuleType(name) for name in (
    'homeassistant', 'homeassistant.components', 'homeassistant.components.update',
    'homeassistant.exceptions', 'homeassistant.core', 'homeassistant.helpers',
    'homeassistant.helpers.dispatcher',
)}
modules['homeassistant.components.update'].UpdateEntity = Entity
modules['homeassistant.components.update'].UpdateEntityFeature = Features
modules['homeassistant.components.update'].UpdateDeviceClass = types.SimpleNamespace(FIRMWARE='firmware')
modules['homeassistant.exceptions'].HomeAssistantError = HAError
modules['homeassistant.core'].callback = lambda f: f
modules['homeassistant.helpers.dispatcher'].async_dispatcher_connect = MagicMock()
modules['homeassistant.helpers.dispatcher'].async_dispatcher_send = MagicMock()
with patch.dict(sys.modules, modules):
    update = load('update')


def fixture(run='idle', status='available', current='P049', available='P050'):
    service = {
        'serviceId': 'fw', 'serviceType': helpers.FIRMWARE,
        'domainType': 'cloud.smarthq.domain.firmware',
        'serviceDeviceType': 'cloud.smarthq.device.wifi',
        'supportedCommands': [helpers.UPGRADE],
        'state': {'disabled': False, 'upgradeStatus': 'cloud.smarthq.type.upgrade.' + status,
                  'versionCurrent': current, 'versionAvailable': available},
    }
    item = {'deviceType': 'cloud.smarthq.device.sourdoughstarter', 'presence': 'ONLINE',
            'services': [service, {'serviceId': 'main', 'serviceType': helpers.SOURDOUGH,
            'state': {'state': 'cloud.smarthq.type.runstatus.' + run}}]}
    return item, service

class TestFeatures(unittest.TestCase):
    def test_combined_goal(self):
        self.assertEqual(helpers.goal_schedule({'goalDay': 'cloud.smarthq.type.weekday.sunday', 'goalTimeHours': 10, 'goalTimeMinutes': 5}), 'Sunday 10:05')

    def test_invalid_goal_not_invented(self):
        for hour, minute in [(24, 0), (0, 60), (True, 5), (1.5, 0), (None, 0), ('2', 0), (float('nan'), 0)]:
            self.assertIsNone(helpers.goal_schedule({'goalDay': 'sunday', 'goalTimeHours': hour, 'goalTimeMinutes': minute}))
        self.assertIsNone(helpers.goal_schedule({}))

    def test_settings_labels(self):
        self.assertEqual(helpers.setting_label('cloud.smarthq.domain.display.brightness')[1], 'display_brightness')
        self.assertEqual(helpers.setting_label('cloud.smarthq.domain.tonevolume')[1], 'tone_volume')
        self.assertIsNone(helpers.setting_label('cloud.smarthq.domain.cooking'))

    def test_timer_names(self):
        self.assertEqual(helpers.timer_label('cloud.smarthq.domain.feed', 'secondsRemaining'), 'Until Next Feed')
        self.assertEqual(helpers.timer_label('cloud.smarthq.domain.full', 'secondsRemaining'), 'Until Crock Full')
        self.assertEqual(helpers.timer_label('cloud.smarthq.domain.complete', 'secondsRemaining'), 'Since Done')

    def test_upgrade_allowed_only_when_idle_and_enabled(self):
        item, service = fixture()
        self.assertIsNone(helpers.firmware_install_error(service, item))
        for run in ['active', 'feeding', 'complete', 'unknown', 'in.progress']:
            item, service = fixture(run=run)
            self.assertIsNotNone(helpers.firmware_install_error(service, item))

    def test_upgrade_rejects_unknown_capabilities(self):
        for mutation in ['offline', 'disabled', 'no-command', 'no-status', 'no-idle', 'other-device']:
            item, service = fixture()
            if mutation == 'offline': item['presence'] = 'OFFLINE'
            if mutation == 'disabled': service['state']['disabled'] = True
            if mutation == 'no-command': service['supportedCommands'] = []
            if mutation == 'no-status': service['state'].pop('disabled')
            if mutation == 'no-idle': item['services'].pop()
            if mutation == 'other-device': item['deviceType'] = 'other'; item['services'].pop()
            self.assertIsNotNone(helpers.firmware_install_error(service, item), mutation)

class TestModeSettings(unittest.TestCase):
    def fixture(self):
        item, _ = fixture()
        service = {'serviceType': 'cloud.smarthq.service.mode', 'domainType': 'cloud.smarthq.domain.brightness',
                   'serviceDeviceType': 'cloud.smarthq.device.sourdoughstarter',
                   'supportedCommands': ['cloud.smarthq.command.mode.set'],
                   'config': {'supportedModes': ['cloud.smarthq.type.mode.low', {'token': 'cloud.smarthq.type.mode.high'}]},
                   'state': {'disabled': False}}
        return item, service

    def test_uses_exact_advertised_token(self):
        item, service = self.fixture()
        self.assertEqual(helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.high'),
                         {'commandType': 'cloud.smarthq.command.mode.set', 'mode': 'cloud.smarthq.type.mode.high'})

    def test_no_invented_option_or_command(self):
        item, service = self.fixture()
        with self.assertRaises(ValueError): helpers.mode_setting_command(service, item, 'medium')
        service['supportedCommands'] = []
        with self.assertRaises(ValueError): helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.low')

    def test_disabled_and_offline_settings_rejected(self):
        item, service = self.fixture(); service['state']['disabled'] = True
        with self.assertRaises(ValueError): helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.low')
        service['state']['disabled'] = False; item['presence'] = 'OFFLINE'
        with self.assertRaises(ValueError): helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.low')

    def test_optional_disabled_flag_may_be_omitted(self):
        item, service = self.fixture()
        service['state'] = {'mode': 'cloud.smarthq.type.mode.low'}
        self.assertEqual(helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.high'),
                         {'commandType': 'cloud.smarthq.command.mode.set', 'mode': 'cloud.smarthq.type.mode.high'})

    def test_malformed_disabled_flag_is_not_treated_as_enabled(self):
        for flag in [None, 'false', 'true', 0, 1]:
            item, service = self.fixture()
            service['state']['disabled'] = flag
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError):
                    helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.high')

    def test_missing_metadata_rejected(self):
        item, service = self.fixture(); del service['serviceDeviceType']
        with self.assertRaises(ValueError): helpers.mode_setting_command(service, item, 'cloud.smarthq.type.mode.low')


class TestFirmwareEntity(unittest.IsolatedAsyncioTestCase):
    def make_entity(self, item=None):
        if item is None: item, _ = fixture()
        service = item['services'][0]
        api = types.SimpleNamespace(async_get_device_item=AsyncMock(return_value=item), async_send_command=AsyncMock(return_value={'success': True}))
        hass = types.SimpleNamespace(data={'sourdough_sidekick': {'entry': {'api': api, 'store': {}}}})
        entity = update.SmartHQFirmwareUpdate(hass, types.SimpleNamespace(entry_id='entry'), 'device', item, service)
        return entity, api

    async def test_versions_and_features(self):
        entity, _ = self.make_entity()
        self.assertEqual(entity.installed_version, 'P049')
        self.assertEqual(entity.latest_version, 'P050')
        self.assertTrue(entity.has_update)
        self.assertTrue(entity.supported_features & Features.INSTALL)
        self.assertFalse(entity.in_progress)

    async def test_read_only_firmware_has_no_install_feature(self):
        item, service = fixture(); service['supportedCommands'] = []
        entity, _ = self.make_entity(item)
        self.assertFalse(entity.supported_features & Features.INSTALL)

    async def test_busy_precheck_never_sends(self):
        item, _ = fixture(run='feeding')
        entity, api = self.make_entity(item)
        with self.assertRaises(HAError): await entity.async_install()
        api.async_send_command.assert_not_awaited()

    async def test_install_once_and_wait_for_new_version(self):
        entity, api = self.make_entity()
        api.async_get_device_item.side_effect = [fixture()[0], fixture(status='downloading')[0], fixture(status='idle', current='P050')[0]]
        with patch.object(update.asyncio, 'sleep', new=AsyncMock()):
            await entity.async_install()
        api.async_send_command.assert_awaited_once_with(
            device_id='device', service_type=helpers.FIRMWARE,
            domain_type='cloud.smarthq.domain.firmware', service_device_type='cloud.smarthq.device.wifi',
            command={'commandType': helpers.UPGRADE},
        )
        self.assertEqual(entity.installed_version, 'P050')
        self.assertFalse(entity.in_progress)

    async def test_transient_disconnect_does_not_resend_install(self):
        entity, api = self.make_entity()
        api.async_get_device_item.side_effect = [fixture()[0], OSError('reboot'), fixture(status='idle', current='P050')[0]]
        with patch.object(update.asyncio, 'sleep', new=AsyncMock()): await entity.async_install()
        api.async_send_command.assert_awaited_once()

    async def test_cloud_rejection_not_success(self):
        entity, api = self.make_entity(); api.async_send_command.return_value = {'success': False}
        with self.assertRaises(HAError): await entity.async_install()
        self.assertFalse(entity._install_requested)

    async def test_device_error_is_reported(self):
        entity, api = self.make_entity()
        api.async_get_device_item.side_effect = [fixture()[0], fixture(status='error.writing')[0]]
        with patch.object(update.asyncio, 'sleep', new=AsyncMock()):
            with self.assertRaisesRegex(HAError, 'error.writing'): await entity.async_install()
        api.async_send_command.assert_awaited_once()

    async def test_timeout_never_reports_install_success(self):
        entity, api = self.make_entity()
        with patch.object(update, 'INSTALL_TIMEOUT', 0):
            with self.assertRaisesRegex(HAError, 'Timed out'): await entity.async_install()
        api.async_send_command.assert_awaited_once()

    async def test_specific_versions_and_backup_rejected(self):
        entity, api = self.make_entity()
        for kwargs in [{'version': 'P050'}, {'backup': True}]:
            with self.assertRaises(HAError): await entity.async_install(**kwargs)
        api.async_send_command.assert_not_awaited()

if __name__ == '__main__': unittest.main()
