import re
from collections.abc import Iterable

from ..utils import parse_datetime, slugify

PARSER_VERSION = '0.1.0'

KNOWN_KEYS = {
    ('DEVICE INFORMATION', 'Name'): 'device.name',
    ('DEVICE INFORMATION', 'Type'): 'device.type',
    ('VERSION INFORMATION', 'Application version'): 'version.application',
    ('VERSION INFORMATION', 'Application date/time'): 'version.application_datetime',
    ('VERSION INFORMATION', 'Application checksum'): 'version.application_checksum',
    ('NETWORK SETTINGS', 'IP address 1'): 'network.ip_address_1',
    ('NETWORK SETTINGS', 'IP address 2'): 'network.ip_address_2',
    ('NETWORK SETTINGS', 'Subnet mask 1'): 'network.subnet_mask_1',
    ('NETWORK SETTINGS', 'Subnet mask 2'): 'network.subnet_mask_2',
    ('SYSTEM DATA', 'Flow computer tag'): 'asset.flow_computer_tag',
    ('SYSTEM DATA', 'System tag'): 'asset.system_tag',
    ('SYSTEM DATA', 'System description'): 'asset.description',
    ('SYSTEM DATA', 'Company'): 'asset.company',
    ('SYSTEM DATA', 'Location'): 'asset.location',
}


def _extract_section_header(line: str) -> str | None:
    stripped = line.rstrip()
    if not stripped or len(stripped) > 160:
        return None
    match = re.match(r'^(?P<header>[A-Z0-9/\- ,&]+?)(?:\s{2,}Display:.*)?$', stripped.strip())
    if not match:
        return None
    header = match.group('header').strip()
    if not header or _looks_like_context_token(header):
        return None
    return header


def _is_section_header(line: str) -> bool:
    return _extract_section_header(line) is not None


def _iter_key_value_lines(lines: Iterable[str]) -> list[tuple[str | None, str, str]]:
    pairs: list[tuple[str | None, str, str]] = []
    current_section: str | None = None
    for line in lines:
        if section_header := _extract_section_header(line):
            current_section = section_header
            continue
        match = re.match(r'^(?P<label>.+?\S)\s{2,}(?P<value>\S.*)$', line.rstrip())
        if not match:
            continue
        label = match.group('label').strip()
        value = match.group('value').strip()
        pairs.append((current_section, label, value))
    return pairs


def _parameter_key(section: str | None, label: str) -> str:
    if section and (section, label) in KNOWN_KEYS:
        return KNOWN_KEYS[(section, label)]
    prefix = slugify(section or 'general')
    return f'{prefix}.{slugify(label)}'


def _lookup_value(pairs: list[tuple[str | None, str, str]], label: str, section: str | None = None) -> str | None:
    if section is not None:
        for pair_section, pair_label, value in pairs:
            if pair_section == section and pair_label == label:
                return value
    for _, pair_label, value in pairs:
        if pair_label == label:
            return value
    return None


def _split_columns(text: str) -> list[str]:
    return [part.strip() for part in re.split(r'\s{2,}', text.strip()) if part.strip()]


def _is_missing_value(value: str) -> bool:
    stripped = value.strip()
    return not stripped or all(char in {'-', ' '} for char in stripped)


def _normalize_value(value: str) -> str | None:
    return None if _is_missing_value(value) else value.strip()


def _looks_like_context_token(value: str) -> bool:
    normalized = value.strip()
    return bool(
        re.fullmatch(
            r'(Run \d+|Product \d+|Module \d+|COM\d+|Analog input \d+|Pt100 input \d+|Digital input \d+|Pulse input \d+)',
            normalized,
            flags=re.IGNORECASE,
        )
    )


def _extract_tabular_contexts(line: str) -> list[dict[str, str | None]]:
    tokens = _split_columns(line)
    if len(tokens) < 2 or not all(_looks_like_context_token(token) for token in tokens):
        return []
    return [
        {
            'label': token,
            'slug': slugify(token),
            'tag_label': None,
            'tag_slug': None,
        }
        for token in tokens
    ]


def _extract_block_context(line: str) -> dict[str, str | None] | None:
    stripped = line.strip()
    if not _looks_like_context_token(stripped):
        return None
    return {
        'label': stripped,
        'slug': slugify(stripped),
        'tag_label': None,
        'tag_slug': None,
    }


def _is_tag_label(label: str) -> bool:
    normalized = slugify(label)
    return normalized in {'tag', 'meter_tag', 'meter_id'}


def _ensure_unique_key(base_key: str, seen_counts: dict[str, int]) -> str:
    count = seen_counts.get(base_key, 0)
    seen_counts[base_key] = count + 1
    if count == 0:
        return base_key
    return f'{base_key}__{count + 1}'


def _build_contextual_key(section: str | None, context_segments: list[str], label: str, seen_counts: dict[str, int]) -> str:
    parts = [slugify(section or 'general'), *[segment for segment in context_segments if segment], slugify(label)]
    return _ensure_unique_key('.'.join(parts), seen_counts)


def _build_section_label(section: str | None, context_labels: list[str]) -> str | None:
    labels = [section, *[label for label in context_labels if label]]
    joined = ' / '.join([label for label in labels if label])
    return joined or None


def _record_from_context(
    *,
    section: str | None,
    label: str,
    value: str,
    context: dict[str, str | None] | None,
    seen_counts: dict[str, int],
) -> dict:
    context_segments: list[str] = []
    context_labels: list[str] = []
    if context:
        if context.get('slug'):
            context_segments.append(str(context['slug']))
        if context.get('tag_slug'):
            context_segments.append(str(context['tag_slug']))
        if context.get('label'):
            context_labels.append(str(context['label']))
        if context.get('tag_label'):
            context_labels.append(str(context['tag_label']))
    parameter_key = _build_contextual_key(section, context_segments, label, seen_counts)
    section_label = _build_section_label(section, context_labels)
    normalized_value = _normalize_value(value)
    return {
        'section': section_label,
        'parameter_key': parameter_key,
        'parameter_label': label,
        'raw_value': value.strip(),
        'normalized_value': normalized_value,
        'unit': None,
        'evidence_excerpt': f'{label} {value.strip()}',
    }


def _collect_parameter_records(lines: Iterable[str]) -> list[dict]:
    records: list[dict] = []
    current_section: str | None = None
    table_contexts: list[dict[str, str | None]] = []
    block_context: dict[str, str | None] | None = None
    seen_counts: dict[str, int] = {}

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue

        if contexts := _extract_tabular_contexts(raw_line):
            table_contexts = contexts
            block_context = None
            continue

        if context := _extract_block_context(raw_line):
            block_context = context
            continue

        if section_header := _extract_section_header(raw_line):
            current_section = section_header
            table_contexts = []
            block_context = None
            continue

        match = re.match(r'^(?P<label>.+?\S)\s{2,}(?P<value>\S.*)$', raw_line.rstrip())
        if not match:
            continue

        label = match.group('label').strip()
        value = match.group('value').strip()

        if table_contexts:
            value_columns = _split_columns(value)
            if len(table_contexts) == 1:
                if _is_tag_label(label) and value_columns:
                    current_value = _normalize_value(value_columns[0])
                    if current_value:
                        table_contexts[0]['tag_label'] = current_value
                        table_contexts[0]['tag_slug'] = slugify(current_value)
                records.append(
                    _record_from_context(
                        section=current_section,
                        label=label,
                        value=value_columns[0] if value_columns else value,
                        context=table_contexts[0],
                        seen_counts=seen_counts,
                    )
                )
                continue

            if len(value_columns) >= 2:
                for index, context in enumerate(table_contexts):
                    if index >= len(value_columns):
                        break
                    column_value = value_columns[index]
                    normalized_column_value = _normalize_value(column_value)
                    if _is_tag_label(label) and normalized_column_value:
                        context['tag_label'] = normalized_column_value
                        context['tag_slug'] = slugify(normalized_column_value)
                    records.append(
                        _record_from_context(
                            section=current_section,
                            label=label,
                            value=column_value,
                            context=context,
                            seen_counts=seen_counts,
                        )
                    )
                continue

        if block_context and _is_tag_label(label):
            normalized_value = _normalize_value(value)
            if normalized_value:
                block_context['tag_label'] = normalized_value
                block_context['tag_slug'] = slugify(normalized_value)

        records.append(
            _record_from_context(
                section=current_section,
                label=label,
                value=value,
                context=block_context,
                seen_counts=seen_counts,
            )
        )

    return records


def parse_configuration(content: str) -> dict:
    lines = content.splitlines()
    pairs = _iter_key_value_lines(lines)
    parameter_records = _collect_parameter_records(lines)
    snapshot_at = parse_datetime(
        _lookup_value(pairs, 'Start')
        or _lookup_value(pairs, 'Start date/time')
        or _lookup_value(pairs, 'Period start')
        or _lookup_value(pairs, 'Date / time')
        or ''
    )
    return {
        'parser_name': 'configuration_parser',
        'parser_version': PARSER_VERSION,
        'document_type': 'configuration_report',
        'metadata': {
            'snapshot_at': snapshot_at,
            'device_name': _lookup_value(pairs, 'Name', 'DEVICE INFORMATION'),
            'device_type': _lookup_value(pairs, 'Type', 'DEVICE INFORMATION'),
            'application_version': _lookup_value(pairs, 'Application version', 'VERSION INFORMATION'),
            'serial_number': _lookup_value(pairs, 'Serial nr.', 'VERSION INFORMATION')
            or _lookup_value(pairs, 'Serial nr', 'VERSION INFORMATION'),
            'ip_address_1': _lookup_value(pairs, 'IP address 1', 'NETWORK SETTINGS'),
            'ip_address_2': _lookup_value(pairs, 'IP address 2', 'NETWORK SETTINGS'),
        },
        'asset': {
            'flow_computer_tag': _lookup_value(pairs, 'Flow computer tag', 'SYSTEM DATA')
            or _lookup_value(pairs, 'Name', 'DEVICE INFORMATION'),
            'system_tag': _lookup_value(pairs, 'System tag', 'SYSTEM DATA'),
            'location': _lookup_value(pairs, 'Location', 'SYSTEM DATA'),
            'company': _lookup_value(pairs, 'Company', 'SYSTEM DATA'),
            'description': _lookup_value(pairs, 'System description', 'SYSTEM DATA'),
        },
        'records': parameter_records,
        'warnings': [],
    }
