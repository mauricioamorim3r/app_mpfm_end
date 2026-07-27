from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import ConfigDiff, ConfigSnapshot, QaFlag


def _classify(parameter_key: str, parameter_label: str) -> tuple[str, str, str]:
    label = f'{parameter_key} {parameter_label}'.lower()
    if any(token in label for token in ('density', 'k_factor', 'k-factor', 'meter_factor', 'correction_factor')):
        return 'metrological', 'critical', 'Potential direct impact on fiscal or metrological calculation.'
    if any(token in label for token in ('override', 'pulse', 'flow_rate_alarm', 'range')):
        return 'metrological', 'high', 'Sensitive metrological behavior changed and requires validation.'
    if any(token in label for token in ('ip_address', 'gateway', 'subnet', 'baud', 'parity', 'com', 'port')):
        return 'network', 'medium', 'Communication or network setting changed.'
    if any(token in label for token in ('description', 'label', 'location', 'company')):
        return 'cosmetic', 'low', 'Informational field changed.'
    if any(token in label for token in ('alarm', 'run', 'mode', 'station')):
        return 'operational', 'medium', 'Operational behavior changed and should be reviewed in context.'
    return 'operational', 'medium', 'Operational configuration changed.'


def compute_diff(session: Session, left_snapshot_id: int, right_snapshot_id: int) -> list[ConfigDiff]:
    left_snapshot = session.get(ConfigSnapshot, left_snapshot_id)
    right_snapshot = session.get(ConfigSnapshot, right_snapshot_id)
    if left_snapshot is None or right_snapshot is None:
        raise ValueError('Snapshot not found.')

    left_map = {parameter.parameter_key: parameter for parameter in left_snapshot.parameters}
    right_map = {parameter.parameter_key: parameter for parameter in right_snapshot.parameters}
    all_keys = sorted(set(left_map) | set(right_map))

    session.execute(
        delete(ConfigDiff).where(
            ConfigDiff.left_snapshot_id == left_snapshot_id,
            ConfigDiff.right_snapshot_id == right_snapshot_id,
        )
    )
    session.execute(
        delete(QaFlag).where(
            QaFlag.related_entity_type == 'diff_pair',
            QaFlag.related_entity_id == right_snapshot_id,
        )
    )

    records: list[ConfigDiff] = []
    for key in all_keys:
        left_parameter = left_map.get(key)
        right_parameter = right_map.get(key)
        left_value = left_parameter.normalized_value if left_parameter else None
        right_value = right_parameter.normalized_value if right_parameter else None
        if left_value == right_value:
            continue
        change_type = 'modified'
        if left_parameter is None:
            change_type = 'added'
        elif right_parameter is None:
            change_type = 'removed'
        label = (right_parameter or left_parameter).parameter_label
        category, severity, impact_summary = _classify(key, label)
        record = ConfigDiff(
            left_snapshot_id=left_snapshot_id,
            right_snapshot_id=right_snapshot_id,
            parameter_key=key,
            parameter_label=label,
            left_value=left_value,
            right_value=right_value,
            change_type=change_type,
            category=category,
            severity=severity,
            impact_summary=impact_summary,
        )
        session.add(record)
        records.append(record)
        if severity in {'critical', 'high'}:
            session.add(
                QaFlag(
                    related_entity_type='diff_pair',
                    related_entity_id=right_snapshot_id,
                    flag_type=f'diff_{category}',
                    severity=severity,
                    message=f'{label}: {impact_summary} ({left_value} -> {right_value})',
                )
            )
    session.commit()
    return records
