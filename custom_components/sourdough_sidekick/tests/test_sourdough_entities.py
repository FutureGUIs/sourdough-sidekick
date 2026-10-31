"""Entity wiring checks to run inside a Home Assistant test environment."""
from unittest.mock import MagicMock
from custom_components.sourdough_sidekick.const import DOMAIN
from custom_components.sourdough_sidekick.sensor import _build_standard_sensors
from custom_components.sourdough_sidekick.service_registry import SOURDOUGHSTARTER_SERVICE
from custom_components.sourdough_sidekick.binary_sensor import SmartHQCrockPresenceSensor


def runtime(state):
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = 'test-entry'
    hass.data = {DOMAIN: {'test-entry': {'store': {'device': {'snapshot': {'services': {'service': state}}}}}}}
    return hass, entry


def test_sidekick_entity_wiring_and_deduplication():
    hass, entry = runtime({'state': 'cloud.smarthq.type.runstatus.active', 'goalAmount': 1000})
    uids, pairs = set(), set()
    args = (hass, entry, 'device', 'service', 'Sidekick', SOURDOUGHSTARTER_SERVICE, uids, pairs)
    entities = _build_standard_sensors(*args, service_config={'weightUnits': 'cloud.smarthq.type.weightunits.grams'})
    assert len(entities) == 14
    by_key = {entity._state_key: entity for entity in entities if type(entity).__name__ == 'SmartHQSourdoughSensor'}
    assert by_key['state'].native_value == 'active'
    assert by_key['state'].available
    assert by_key['goalAmount'].native_value == 1000
    assert by_key['goalAmount'].native_unit_of_measurement == 'g'
    assert not by_key['flourMass'].available
    assert len(pairs) == 13
    assert _build_standard_sensors(*args) == []


def test_crock_snapshot_changes_and_unavailable():
    state = {'on': True}
    hass, entry = runtime(state)
    entity = SmartHQCrockPresenceSensor(hass, entry, 'device', 'service', 'Crock Present', 'crock-test')
    assert entity.is_on is True
    assert entity.available
    state['on'] = False
    assert entity.is_on is False
    assert entity.available
    state.clear()
    assert entity.is_on is None
    assert not entity.available
    state.update({'on': True, 'disabled': True})
    assert entity.is_on is None
    assert not entity.available
