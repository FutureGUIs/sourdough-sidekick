"""Run without Home Assistant: python -m unittest discover -s tests -v."""
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).parents[1] / 'custom_components/sourdough_sidekick/sourdough.py'
spec = importlib.util.spec_from_file_location('sidekick_fields', MODULE)
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)
FIELDS = {f.key: f for f in model.FIELDS}


class TestSourdoughReadings(unittest.TestCase):
    def test_documented_state_fields(self):
        self.assertEqual(set(FIELDS), {
            'feedingFrequency', 'flourMass', 'flourRatio', 'goalAmount',
            'goalDay', 'goalTimeHours', 'goalTimeMinutes', 'mode',
            'starterMass', 'starterRatio', 'state', 'waterMass', 'waterRatio',
        })

    def test_numeric_zero_is_preserved(self):
        self.assertEqual(model.field_value(FIELDS['goalTimeMinutes'], {'goalTimeMinutes': 0}), 0)

    def test_ratios_stay_numeric(self):
        value = model.field_value(FIELDS['flourRatio'], {'flourRatio': 2})
        self.assertIsInstance(value, int)
        self.assertEqual(value, 2)

    def test_goal_amount_stays_numeric(self):
        self.assertEqual(model.field_value(FIELDS['goalAmount'], {'goalAmount': 1000}), 1000)

    def test_missing_value_is_unknown(self):
        self.assertIsNone(model.field_value(FIELDS['goalAmount'], {}))

    def test_bad_numeric_values_are_unknown(self):
        for value in [True, False, '1000', None, float('inf'), float('nan'), [], {}]:
            with self.subTest(value=value):
                self.assertIsNone(model.field_value(FIELDS['goalAmount'], {'goalAmount': value}))

    def test_enum_prefix_removed_without_losing_words(self):
        self.assertEqual(model.field_value(FIELDS['state'], {'state': 'cloud.smarthq.type.runstatus.in.progress'}), 'in.progress')
        self.assertEqual(model.field_value(FIELDS['mode'], {'mode': 'cloud.smarthq.type.mode.ratio'}), 'ratio')
        self.assertEqual(model.field_value(FIELDS['goalDay'], {'goalDay': 'cloud.smarthq.type.weekday.sunday'}), 'sunday')

    def test_unknown_enum_is_preserved(self):
        self.assertEqual(model.field_value(FIELDS['mode'], {'mode': 'future-mode'}), 'future-mode')

    def test_bad_enum_is_unknown(self):
        for value in [None, '', 0, False]:
            self.assertIsNone(model.field_value(FIELDS['state'], {'state': value}))

    def test_declared_mass_units(self):
        for source, expected in [('grams', 'g'), ('ounces', 'oz'), ('pounds', 'lb')]:
            with self.subTest(source=source):
                self.assertEqual(model.field_unit(FIELDS['goalAmount'], {'weightUnits': 'cloud.smarthq.type.weightunits.' + source}), expected)

    def test_missing_or_unknown_units_not_assumed(self):
        for config in [{}, {'weightUnits': 'cloud.smarthq.type.weightunits.unknown'}]:
            self.assertIsNone(model.field_unit(FIELDS['goalAmount'], config))

    def test_ratios_and_clock_fields_are_not_masses(self):
        for key in ['flourRatio', 'waterRatio', 'starterRatio', 'goalTimeHours', 'goalTimeMinutes', 'feedingFrequency']:
            self.assertIsNone(model.field_unit(FIELDS[key], {'weightUnits': 'cloud.smarthq.type.weightunits.grams'}))

    def test_unique_id_suffixes_preserved(self):
        expected = {'state': 'sourdough_state', 'mode': 'sourdough_mode', 'goalTimeHours': 'sourdough_goal_h', 'goalTimeMinutes': 'sourdough_goal_m', 'flourRatio': 'sourdough_flour', 'waterRatio': 'sourdough_water', 'starterRatio': 'sourdough_starter'}
        for key, suffix in expected.items():
            self.assertEqual(FIELDS[key].uid, suffix)
        self.assertEqual(len({f.uid for f in model.FIELDS}), len(model.FIELDS))

    def test_crock_exact_service_tuple(self):
        service = {'serviceType': 'cloud.smarthq.service.toggle', 'domainType': 'cloud.smarthq.domain.presence', 'serviceDeviceType': 'cloud.smarthq.device.crock'}
        self.assertTrue(model.is_crock_presence(service))
        for key in service:
            changed = dict(service)
            changed[key] = 'another.service'
            self.assertFalse(model.is_crock_presence(changed))

    def test_crock_present_and_absent(self):
        self.assertIs(model.crock_present({'on': True}), True)
        self.assertIs(model.crock_present({'on': False}), False)

    def test_unknown_crock_never_reported_absent(self):
        for state in [{}, {'on': None}, {'on': 'false'}, {'on': 0}, {'on': True, 'disabled': True}]:
            self.assertIsNone(model.crock_present(state))


if __name__ == '__main__':
    unittest.main()
