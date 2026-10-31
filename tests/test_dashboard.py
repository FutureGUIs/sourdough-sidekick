"""Dashboard generation tests using actual IDs, without network requests."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('make_dashboard', Path(__file__).parents[1] / 'tools/make_dashboard.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestDashboard(unittest.TestCase):
    def state(self, entity, role, device='my-device'):
        return {'entity_id': entity, 'state': 'auto', 'attributes': {'sidekick_device_id': device, 'sidekick_role': role}}

    def test_real_ids_modes_settings_and_firmware(self):
        states = [self.state('sensor.renamed_status', 'state'), self.state('sensor.renamed_mode', 'mode'),
                  self.state('sensor.my_goal', 'goal_schedule'), self.state('sensor.flour', 'flourRatio'),
                  self.state('sensor.water', 'waterMass'), self.state('select.brightness', 'display_brightness'),
                  self.state('select.sound', 'tone_volume'), self.state('update.wifi', 'firmware'),
                  self.state('update.device', 'firmware'), self.state('sensor.other', 'state', 'other-device')]
        dashboard = module.make_dashboard(states, 'my-device')
        cards = dashboard['views'][0]['cards']
        conditions = [card['conditions'][0] for card in cards if card['type'] == 'conditional']
        self.assertEqual({c['state'] for c in conditions}, {'auto', 'ratio', 'custom'})
        self.assertTrue(all(c['entity'] == 'sensor.renamed_mode' for c in conditions))
        self.assertEqual(next(c for c in cards if c.get('title') == 'Settings')['entities'], ['select.sound', 'select.brightness'])
        self.assertEqual(next(c for c in cards if c.get('title') == 'Firmware')['entities'], ['update.wifi', 'update.device'])
        self.assertNotIn('sensor.other', str(dashboard))

    def test_missing_capabilities_omitted(self):
        result = module.make_dashboard([self.state('sensor.mode', 'mode')], 'my-device')
        self.assertNotIn('Settings', str(result))
        self.assertNotIn('Firmware', str(result))

if __name__ == '__main__': unittest.main()
