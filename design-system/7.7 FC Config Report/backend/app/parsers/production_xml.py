from __future__ import annotations

import re
from datetime import datetime
from xml.etree import ElementTree

PARSER_VERSION = '0.1.0'
DATE_FORMATS = ('%d/%m/%Y %H:%M:%S', '%d/%m/%y %H:%M:%S')


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    return None


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if ',' in text:
        compact = text.replace('.', '').replace(',', '.', 1)
    else:
        compact = text
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?', compact):
        try:
            return str(float(compact))
        except ValueError:
            return text
    return text


def _leaf_records(element: ElementTree.Element, path: list[str]) -> list[dict]:
    children = list(element)
    if not children:
        return []
    records: list[dict] = []
    for child in children:
        child_path = [*path, child.tag]
        grandchildren = list(child)
        if grandchildren:
            records.extend(_leaf_records(child, child_path))
            continue
        raw_value = child.text.strip() if child.text else None
        parameter_key = '.'.join(child_path)
        records.append(
            {
                'section': ' / '.join(child_path[:-1]),
                'parameter_key': parameter_key,
                'parameter_label': child.tag,
                'normalized_value': _normalize_value(raw_value),
                'raw_value': raw_value,
                'unit': None,
                'evidence_excerpt': f'<{child.tag}>{raw_value or ""}</{child.tag}>',
            }
        )
    return records


def _extract_run_number(message: str | None) -> int | None:
    match = re.search(r'run\s+(\d+)', message or '', flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_alarm_values(message: str | None) -> tuple[str | None, str | None]:
    match = re.search(r'from\s+(.+?)\s+to\s+(.+?)(?:\s+-|\s+\[|$)', message or '', flags=re.IGNORECASE)
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).strip()


def _xml004_event_severity(description: str | None) -> str:
    text = (description or '').lower()
    if any(token in text for token in ('limit', 'limite', 'alarm', 'alarme', 'k-factor', 'meter factor', 'cutoff', 'density', 'densidade', 'override')):
        return 'warning'
    return 'info'


def parse_production_xml(content: str, filename: str = '') -> dict:
    root = ElementTree.fromstring(content)
    document_type = root.tag.lower()
    configs: list[dict] = []
    events: list[dict] = []

    for dados in root.findall('.//DADOS_BASICOS'):
        tag = dados.attrib.get('COD_TAG_PONTO_MEDICAO')
        cv_serial = dados.attrib.get('NUM_SERIE_COMPUTADOR_VAZAO')
        installation_code = dados.attrib.get('COD_INSTALACAO')
        primary_serial = dados.attrib.get('NUM_SERIE_ELEMENTO_PRIMARIO')

        if document_type == 'a004':
            asset_key = cv_serial or tag or f'{document_type}-unknown'
            for alarm in dados.findall('.//ALARMES'):
                message = (alarm.findtext('DSC_DADO_ALARMADO') or '').strip()
                occurred_at = _parse_datetime(alarm.findtext('DHA_ALARME'))
                measure = (alarm.findtext('DSC_MEDIDA_ALARMADA') or '').strip() or None
                old_value, new_value = _extract_alarm_values(message)
                events.append(
                    {
                        'asset': {
                            'flow_computer_tag': asset_key,
                            'system_tag': asset_key,
                            'location': f'Instalacao {installation_code}' if installation_code else None,
                            'company': None,
                            'description': f'Production XML {document_type}',
                        },
                        'record': {
                            'occurred_at': occurred_at,
                            'run_number': _extract_run_number(message),
                            'event_type': 'alarm_state_changed',
                            'category': 'alarm',
                            'severity': 'warning' if 'alarm' in message.lower() else 'info',
                            'actor': None,
                            'source_ip': None,
                            'message': message,
                            'old_value': old_value,
                            'new_value': new_value,
                            'evidence_excerpt': f'{message} [{measure}]' if measure else message,
                        },
                    }
                )
            for event in dados.findall('.//EVENTOS'):
                changed_data = (event.findtext('DSC_DADO_ALTERADO') or '').strip()
                old_value = (event.findtext('DSC_CONTEUDO_ORIGINAL') or '').strip() or None
                new_value = (event.findtext('DSC_CONTEUDO_ATUAL') or '').strip() or None
                occurred_at = _parse_datetime(event.findtext('DHA_OCORRENCIA_EVENTO'))
                message = changed_data or 'Evento XML 004 sem descricao do dado alterado'
                events.append(
                    {
                        'asset': {
                            'flow_computer_tag': asset_key,
                            'system_tag': asset_key,
                            'location': f'Instalacao {installation_code}' if installation_code else None,
                            'company': None,
                            'description': f'Production XML {document_type}',
                        },
                        'record': {
                            'occurred_at': occurred_at,
                            'run_number': _extract_run_number(message),
                            'event_type': 'parameter_changed',
                            'category': 'xml_event',
                            'severity': _xml004_event_severity(message),
                            'actor': None,
                            'source_ip': None,
                            'message': message,
                            'old_value': old_value,
                            'new_value': new_value,
                            'evidence_excerpt': f'{message}: {old_value or ""} -> {new_value or ""}',
                        },
                    }
                )
            continue

        records = _leaf_records(dados, [document_type, 'DADOS_BASICOS'])
        snapshot_at = None
        for record in records:
            if record['parameter_label'] == 'DHA_COLETA':
                snapshot_at = _parse_datetime(record['raw_value'])
                break
        asset_key = tag or cv_serial or f'{document_type}-unknown'
        asset = {
            'flow_computer_tag': asset_key,
            'system_tag': cv_serial,
            'location': f'Instalacao {installation_code}' if installation_code else None,
            'company': None,
            'description': f'Production XML {document_type}',
        }
        metadata = {
            'snapshot_at': snapshot_at,
            'device_name': tag,
            'device_type': f'Production XML {document_type}',
            'application_version': next(
                (record['normalized_value'] for record in records if record['parameter_label'] == 'DSC_VERSAO_SOFTWARE'),
                None,
            ),
            'serial_number': cv_serial or primary_serial,
            'ip_address_1': None,
            'ip_address_2': None,
            'installation_code': installation_code,
            'primary_serial': primary_serial,
            'measurement_tag': tag,
        }
        records.insert(
            0,
            {
                'section': f'{document_type} / DADOS_BASICOS',
                'parameter_key': f'{document_type}.DADOS_BASICOS.COD_TAG_PONTO_MEDICAO',
                'parameter_label': 'COD_TAG_PONTO_MEDICAO',
                'normalized_value': tag,
                'raw_value': tag,
                'unit': None,
                'evidence_excerpt': f'COD_TAG_PONTO_MEDICAO="{tag or ""}"',
            },
        )
        configs.append({'asset': asset, 'metadata': metadata, 'records': records})

    return {
        'parser_name': 'production_xml',
        'parser_version': PARSER_VERSION,
        'document_type': document_type,
        'configs': configs,
        'events': events,
        'warnings': [],
    }
