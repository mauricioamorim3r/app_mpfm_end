import re

from ..utils import parse_datetime

PARSER_VERSION = '0.1.0'


def _header_pairs(content: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in content.splitlines():
        if line.strip().startswith('Amount'):
            break
        match = re.match(r'^(?P<label>.+?\S)\s{2,}(?P<value>\S.*)$', line.rstrip())
        if match:
            result[match.group('label').strip()] = match.group('value').strip()
    return result


def _classify_event(message: str) -> tuple[str, str, str]:
    lowered = message.lower()
    if 'has logged in' in lowered:
        return 'login', 'operational', 'info'
    if 'logged off' in lowered:
        return 'logout', 'operational', 'info'
    if 'was changed from' in lowered:
        if any(keyword in lowered for keyword in ('density', 'k-factor', 'override', 'pulse')):
            return 'parameter_changed', 'metrological', 'warning'
        return 'parameter_changed', 'operational', 'warning'
    if 'alarm' in lowered or 'failure' in lowered:
        return 'alarm_state_changed', 'operational', 'warning'
    if 'executed' in lowered:
        return 'command_executed', 'operational', 'info'
    return 'generic_event', 'operational', 'info'


def _extract_actor_and_ip(message: str) -> tuple[str | None, str | None]:
    login_match = re.search(r'User (?P<actor>.+?) \(Web: (?P<ip>[^)]+)\)', message)
    if login_match:
        return login_match.group('actor').strip(), login_match.group('ip').strip()
    change_match = re.search(r' by (?P<actor>.+)$', message)
    if change_match:
        return change_match.group('actor').strip(), None
    return None, None


def _extract_values(message: str) -> tuple[str | None, str | None]:
    change_match = re.search(r'changed from (?P<old>.+?) to (?P<new>.+?) by ', message)
    if change_match:
        return change_match.group('old').strip(), change_match.group('new').strip()
    state_match = re.search(r'from (?P<old>.+?) to (?P<new>.+?)(?: \[|$)', message)
    if state_match:
        return state_match.group('old').strip(), state_match.group('new').strip()
    return None, None


def parse_events(content: str) -> dict:
    header = _header_pairs(content)
    records: list[dict] = []
    for line in content.splitlines():
        match = re.match(r'^(?P<ts>\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s{2,}(?P<message>.+)$', line.rstrip())
        if not match:
            continue
        message = match.group('message').strip()
        event_type, category, severity = _classify_event(message)
        actor, source_ip = _extract_actor_and_ip(message)
        old_value, new_value = _extract_values(message)
        run_match = re.search(r'Run (?P<run>\d+)', message)
        records.append(
            {
                'occurred_at': parse_datetime(match.group('ts')),
                'run_number': int(run_match.group('run')) if run_match else None,
                'event_type': event_type,
                'category': category,
                'severity': severity,
                'actor': actor,
                'source_ip': source_ip,
                'message': message,
                'old_value': old_value,
                'new_value': new_value,
                'evidence_excerpt': line.strip(),
            }
        )
    return {
        'parser_name': 'events_parser',
        'parser_version': PARSER_VERSION,
        'document_type': 'events_snapshot',
        'metadata': {
            'start_at': parse_datetime(header.get('Start date/time', '')),
            'end_at': parse_datetime(header.get('End date/time', '')),
            'flow_computer_tag': header.get('Flow computer'),
            'system_tag': header.get('System'),
            'description': header.get('Description'),
            'company': header.get('Company'),
            'location': header.get('Location'),
        },
        'asset': {
            'flow_computer_tag': header.get('Flow computer'),
            'system_tag': header.get('System'),
            'location': header.get('Location'),
            'company': header.get('Company'),
            'description': header.get('Description'),
        },
        'records': records,
        'warnings': [],
    }
