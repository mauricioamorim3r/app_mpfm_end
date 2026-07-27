from __future__ import annotations

import re

from ..utils import parse_datetime, slugify

PARSER_VERSION = '0.1.0'
HEADER_LABELS = ('Meter ID', 'Flow computer', 'Period start', 'Period end', 'Company', 'Location')


def _extract_label_value(text: str, label: str) -> str | None:
    other_labels = [re.escape(other) for other in HEADER_LABELS if other != label]
    lookahead = '|'.join(other_labels)
    pattern = rf'{re.escape(label)}\s{{2,}}(?P<value>.*?)(?=\s{{2,}}(?:{lookahead})\s{{2,}}|$)'
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group('value').strip()
    return value or None


def _iter_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    current_section = 'Run report'
    seen: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in {'Totals', 'Time weighted averages', 'Flow weighted averages', 'Flow weighted average composition [mol-%]'}:
            current_section = stripped
            continue
        if stripped.startswith('# indicates') or stripped.startswith('* indicates'):
            continue
        if any(label in line for label in HEADER_LABELS):
            for label in HEADER_LABELS:
                value = _extract_label_value(line, label)
                if value is not None:
                    key = f'run_report.header.{slugify(label)}'
                    records.append(_record(current_section, key, label, value, seen))
            continue
        parts = [part.strip() for part in re.split(r'\s{2,}', stripped) if part.strip()]
        if len(parts) < 2:
            continue
        if len(parts) >= 4:
            records.append(_record(current_section, f'run_report.{slugify(parts[0])}', parts[0], _join_unit_value(parts[1], parts[2]), seen))
            records.append(_record(current_section, f'run_report.{slugify(parts[-2])}', parts[-2], parts[-1], seen))
            continue
        label = parts[0]
        value = _join_unit_value(*parts[1:])
        records.append(_record(current_section, f'run_report.{slugify(label)}', label, value, seen))
    return records


def _join_unit_value(*parts: str) -> str:
    return ' '.join(part for part in parts if part).strip()


def _record(section: str, base_key: str, label: str, value: str, seen: dict[str, int]) -> dict:
    count = seen.get(base_key, 0)
    seen[base_key] = count + 1
    key = base_key if count == 0 else f'{base_key}__{count + 1}'
    return {
        'section': section,
        'parameter_key': key,
        'parameter_label': label,
        'normalized_value': value,
        'raw_value': value,
        'unit': None,
        'evidence_excerpt': f'{label} {value}',
    }


def parse_run_report(content: str) -> dict:
    lines = content.splitlines()
    full_text = '\n'.join(lines[:12])
    meter_id = _extract_label_value(full_text, 'Meter ID')
    flow_computer = _extract_label_value(full_text, 'Flow computer')
    period_start = _extract_label_value(full_text, 'Period start')
    period_end = _extract_label_value(full_text, 'Period end')
    return {
        'parser_name': 'run_report_parser',
        'parser_version': PARSER_VERSION,
        'document_type': 'run_report',
        'metadata': {
            'snapshot_at': parse_datetime(period_start or ''),
            'period_start': parse_datetime(period_start or ''),
            'period_end': parse_datetime(period_end or ''),
            'device_name': meter_id,
            'device_type': 'Run report',
            'application_version': None,
            'serial_number': None,
            'ip_address_1': None,
            'ip_address_2': None,
        },
        'asset': {
            'flow_computer_tag': flow_computer,
            'system_tag': meter_id,
            'location': _extract_label_value(full_text, 'Location'),
            'company': _extract_label_value(full_text, 'Company'),
            'description': 'CV run report',
        },
        'records': _iter_records(lines),
        'warnings': [],
    }
