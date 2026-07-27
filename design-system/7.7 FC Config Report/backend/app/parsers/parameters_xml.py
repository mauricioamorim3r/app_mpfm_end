from __future__ import annotations

from datetime import datetime
from xml.etree import ElementTree

PARSER_VERSION = '0.1.0'


def _extract_run_number(parameter_name: str) -> int | None:
    marker = 'RUN'
    upper_name = parameter_name.upper()
    index = upper_name.find(marker)
    if index == -1:
        return None
    digits: list[str] = []
    for character in upper_name[index + len(marker) :]:
        if character.isdigit():
            digits.append(character)
            continue
        break
    if not digits:
        return None
    return int(''.join(digits))


def _build_parameter_key(namespace: str, name: str) -> str:
    compact_namespace = namespace.strip().replace(' ', '_') or 'XML'
    compact_name = name.strip().replace(' ', '_') or 'UNNAMED'
    return f'{compact_namespace}.{compact_name}'


def parse_parameters_xml(content: str) -> dict:
    root = ElementTree.fromstring(content)
    cache_id = root.attrib.get('cacheid')
    records: list[dict] = []

    for index, tag in enumerate(root.findall('t'), start=1):
        full_name = tag.attrib.get('n', '').strip()
        label = tag.attrib.get('t', '').strip() or full_name or f'XML parameter {index}'
        unit = tag.attrib.get('u', '').strip() or None
        value = tag.attrib.get('v')
        namespace, _, parameter_name = full_name.partition('!')
        run_number = _extract_run_number(parameter_name or full_name)
        section_parts = ['Parameters.xml']
        if namespace:
            section_parts.append(namespace)
        if run_number is not None:
            section_parts.append(f'Run {run_number}')
        evidence = f'<t n="{full_name}" t="{label}" u="{unit or ""}" v="{value or ""}" />'
        records.append(
            {
                'section': ' / '.join(section_parts),
                'parameter_key': _build_parameter_key(namespace, parameter_name or full_name),
                'parameter_label': label,
                'normalized_value': value,
                'raw_value': value,
                'unit': unit,
                'evidence_excerpt': evidence,
            }
        )

    return {
        'parser_name': 'flowx_parameters_xml',
        'parser_version': PARSER_VERSION,
        'document_type': 'parameters_xml',
        'metadata': {
            'snapshot_at': None,
            'device_name': None,
            'device_type': 'Flow-X Parameters.xml',
            'application_version': None,
            'serial_number': None,
            'ip_address_1': None,
            'ip_address_2': None,
            'cache_id': cache_id,
            'parsed_at': datetime.utcnow(),
        },
        'asset': {
            'flow_computer_tag': f'parameters-{cache_id}' if cache_id else 'unknown-parameters-xml',
            'system_tag': None,
            'location': None,
            'company': None,
            'description': 'Flow-X Parameters.xml',
        },
        'records': records,
        'warnings': [],
    }
