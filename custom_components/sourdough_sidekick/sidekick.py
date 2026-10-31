"""Pure helpers for capability-driven Sidekick features."""
from datetime import time

SOURDOUGH = 'cloud.smarthq.service.sourdoughstarter.v1'
FIRMWARE = 'cloud.smarthq.service.firmware.v1'
UPGRADE = 'cloud.smarthq.command.firmware.v1.upgrade'


def is_sidekick(item):
    return item.get('deviceType') == 'cloud.smarthq.device.sourdoughstarter' or any(
        s.get('serviceType') == SOURDOUGH for s in item.get('services', []) if isinstance(s, dict)
    )


def setting_label(domain, config=None):
    text = (domain + ' ' + str((config or {}).get('label', ''))).lower()
    if 'brightness' in text:
        return 'Display Brightness', 'display_brightness', 'mdi:brightness-6'
    if any(word in text for word in ('tone', 'sound', 'volume')):
        return 'Tone Volume', 'tone_volume', 'mdi:volume-high'
    if 'temperatureunits' in text:
        return 'Temperature Unit', 'temperature_unit', 'mdi:temperature-celsius'
    return None


def goal_schedule(state):
    """The API gives a weekday, not a calendar date: do not invent a date."""
    day = state.get('goalDay', '').removeprefix('cloud.smarthq.type.weekday.') if isinstance(state.get('goalDay'), str) else ''
    if day not in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'):
        return None
    hour, minute = state.get('goalTimeHours'), state.get('goalTimeMinutes')
    for value in (hour, minute):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if isinstance(value, float) and not value.is_integer():
            return None
    try:
        clock = time(int(hour), int(minute))
    except ValueError:
        return None
    return f'{day.title()} {clock:%H:%M}'


def timer_label(domain, key):
    tail = domain.removeprefix('cloud.smarthq.domain.')
    if tail == 'feed':
        return 'Until Next Feed' if key == 'secondsRemaining' else 'Since Last Feed'
    if tail == 'full':
        return 'Until Crock Full' if key == 'secondsRemaining' else 'Since Crock Full'
    if tail == 'complete':
        return 'Since Done'
    return 'Time Remaining' if key == 'secondsRemaining' else 'Time Elapsed'


def firmware_status(state):
    return str(state.get('upgradeStatus', '')).removeprefix('cloud.smarthq.type.upgrade.')


def firmware_install_error(service, item):
    """Validate freshly fetched device state before issuing an upgrade command."""
    if not is_sidekick(item):
        return 'This firmware control is limited to Sourdough Sidekick devices.'
    if item.get('presence') != 'ONLINE':
        return 'Sidekick must be online before installing firmware.'
    if UPGRADE not in (service.get('supportedCommands') or []):
        return 'This firmware service does not advertise the upgrade command.'
    if not all(service.get(key) for key in ('serviceType', 'domainType', 'serviceDeviceType')):
        return 'Firmware service metadata is incomplete.'
    state = service.get('state') or {}
    if state.get('disabled') is not False:
        return 'Firmware installation is disabled or its availability is unknown.'
    if firmware_status(state) not in ('available', 'error.busy'):
        return 'No installable firmware update is currently advertised.'
    main = next((s for s in item.get('services', []) if s.get('serviceType') == SOURDOUGH), {})
    run = (main.get('state') or {}).get('state', '')
    if run not in {f'cloud.smarthq.type.runstatus.{x}' for x in ('idle', 'off', 'stopped', 'standby')}:
        return 'Cancel the active Sidekick mode on the appliance before updating; an idle state must be confirmed.'
    return None


def mode_setting_command(service, item, token):
    """Validate a fresh sound/brightness/units service and construct its command."""
    if not service or not is_sidekick(item) or item.get('presence') != 'ONLINE':
        raise ValueError('Sidekick setting is unavailable or offline.')
    # In service.mode, disabled is optional. Omission does not disable an
    # advertised command. Explicit true and malformed values remain blocked.
    state = service.get('state') or {}
    if state.get('disabled') is True:
        raise ValueError('Sidekick reports this setting is disabled.')
    if 'disabled' in state and state['disabled'] is not False:
        raise ValueError('Sidekick returned an invalid setting availability flag.')
    if not all(service.get(k) for k in ('serviceType', 'domainType', 'serviceDeviceType')):
        raise ValueError('Sidekick setting metadata is incomplete.')
    modes = (service.get('config') or {}).get('supportedModes') or []
    tokens = [m if isinstance(m, str) else m.get('token') for m in modes if isinstance(m, (str, dict))]
    command = 'cloud.smarthq.command.mode.set'
    if service.get('serviceType') != 'cloud.smarthq.service.mode' or command not in (service.get('supportedCommands') or []) or token not in tokens:
        raise ValueError('The device does not advertise this setting option.')
    return {'commandType': command, 'mode': token}
