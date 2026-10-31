"""Create a dashboard with actual Sidekick entity IDs using read-only HA state data.

Run: python tools/make_dashboard.py --url https://homeassistant.example.com
A Home Assistant long-lived access token is requested privately and never saved.
"""
import argparse
import getpass
import json
from pathlib import Path
import urllib.request
import urllib.parse


def make_dashboard(states, device_id):
    tagged = [s for s in states if s.get('attributes', {}).get('sidekick_device_id') == device_id]
    roles = {}
    for state in tagged:
        role = state['attributes'].get('sidekick_role')
        if role:
            roles.setdefault(role, []).append(state['entity_id'])
    cards = [{'type': 'picture', 'image': '/local/sourdough_sidekick/logo.png', 'alt_text': 'Sourdough Sidekick', 'tap_action': {'action': 'url', 'url_path': 'https://www.sourdoughsidekick.com/'}}, {'type': 'markdown', 'content': 'Your starter, ready when you are.\n\nSet cycles and feeding modes on your Sidekick.'}]

    def group(title, fields):
        entities = [eid for role in fields for eid in roles.get(role, [])]
        return {'type': 'entities', 'title': title, 'show_header_toggle': False, 'entities': entities} if entities else None

    status = group('Starter', ['state', 'mode', 'crock_present', 'timer_feed', 'timer_full', 'timer_complete'])
    if status: cards.append(status)
    mode_id = (roles.get('mode') or [None])[0]
    for mode, title, fields in [
        ('auto', 'Auto Goal', ['goal_schedule', 'goalAmount']),
        ('ratio', 'By Ratio', ['starterRatio', 'flourRatio', 'waterRatio', 'feedingFrequency']),
        ('custom', 'Custom Feeding', ['starterMass', 'flourMass', 'waterMass', 'feedingFrequency']),
    ]:
        card = group(title, fields)
        if card and mode_id:
            cards.append({'type': 'conditional', 'conditions': [{'condition': 'state', 'entity': mode_id, 'state': mode}], 'card': card})
    settings = group('Settings', ['tone_volume', 'display_brightness', 'temperature_unit'])
    if settings: cards.append(settings)
    firmware = group('Firmware', ['firmware'])
    if firmware: cards.append(firmware)
    return {'title': 'Sourdough Sidekick', 'views': [{'title': 'Sidekick', 'path': 'sidekick', 'icon': 'mdi:bread-slice', 'theme': 'Sourdough Sidekick', 'cards': cards}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='https://homeassistant.example.com')
    parser.add_argument('--states-file', help='Use an existing states JSON export instead of contacting HA')
    parser.add_argument('--device-id', help='Select one Sidekick if there are multiple')
    parser.add_argument('--output', default='sidekick-dashboard.yaml')
    args = parser.parse_args()
    if args.states_file:
        states = json.loads(Path(args.states_file).read_text(encoding='utf-8-sig'))
    else:
        parsed = urllib.parse.urlparse(args.url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            parser.error('Provide a valid Home Assistant http(s) URL.')
        if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            parser.error('Use HTTPS to keep the Home Assistant access token private.')
        token = getpass.getpass('Home Assistant long-lived access token: ')
        request = urllib.request.Request(args.url.rstrip('/') + '/api/states', headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(request, timeout=30) as response:
            states = json.load(response)
        del token
    if not isinstance(states, list):
        parser.error('Expected a Home Assistant states array.')
    devices = sorted({s.get('attributes', {}).get('sidekick_device_id') for s in states if s.get('attributes', {}).get('sidekick_device_id')})
    if not devices:
        parser.error('No tagged Sidekick entities found. Install this build and restart Home Assistant first.')
    device_id = args.device_id
    if not device_id and len(devices) == 1: device_id = devices[0]
    if device_id not in devices:
        print('Available Sidekick device IDs:\n' + '\n'.join(devices))
        parser.error('Run again with --device-id selecting a device from this list.')
    # JSON is valid YAML and avoids requiring extra Python packages.
    Path(args.output).write_text(json.dumps(make_dashboard(states, device_id), indent=2) + '\n', encoding='utf8')
    print('Saved', args.output)

if __name__ == '__main__':
    main()
