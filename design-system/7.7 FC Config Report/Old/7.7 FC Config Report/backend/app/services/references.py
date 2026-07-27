import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import ReferenceRecord, TechnicalReference


REFERENCE_DIR = Path(__file__).resolve().parent.parent / 'reference_data'
BACALHAU_REFERENCE_PATH = REFERENCE_DIR / 'bacalhau_reference.json'
FLOWX_REFERENCE_PATH = REFERENCE_DIR / 'flowx_reference.json'


def _load_seed_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))


def seed_reference_records(session: Session) -> None:
    seed_records = _load_seed_records(BACALHAU_REFERENCE_PATH)
    seed_records.append(
        {
            'entity_type': 'metering_reference',
            'record_key': 'gc_component_profile',
            'name': 'Perfil esperado de cromatografia / GC',
            'description': 'Componentes padrão de cromatografia usados como referência inicial para GC.',
            'metadata': {
                'reference_kind': 'chromatography_profile',
                'components': [
                    'methane',
                    'ethane',
                    'propane',
                    'i-butane',
                    'n-butane',
                    'i-pentane',
                    'n-pentane',
                    'hexane+',
                    'nitrogen',
                    'carbon dioxide',
                ],
                'compare_mode': 'component_percent',
            },
            'source_label': 'flowx-default',
            'is_default': True,
        }
    )
    for record in seed_records:
        existing = (
            session.query(ReferenceRecord)
            .filter(
                ReferenceRecord.entity_type == record['entity_type'],
                ReferenceRecord.record_key == record['record_key'],
            )
            .one_or_none()
        )
        if existing is not None:
            continue
        session.add(
            ReferenceRecord(
                entity_type=record['entity_type'],
                record_key=record['record_key'],
                name=record['name'],
                description=record.get('description'),
                metadata_json=json.dumps(record.get('metadata', {}), ensure_ascii=False),
                source_label=record.get('source_label', 'seed'),
                is_default=record.get('is_default', True),
            )
        )
    session.commit()


def seed_technical_references(session: Session, commit: bool = True) -> None:
    for record in _load_seed_records(FLOWX_REFERENCE_PATH):
        existing = session.query(TechnicalReference).filter(TechnicalReference.topic_key == record['topic_key']).one_or_none()
        if existing is not None:
            continue
        session.add(
            TechnicalReference(
                topic_key=record['topic_key'],
                category=record['category'],
                title=record['title'],
                summary=record['summary'],
                guidance=record['guidance'],
                source_ref=record['source_ref'],
                source_excerpt=record['source_excerpt'],
                severity=record.get('severity', 'medium'),
                is_default=record.get('is_default', True),
            )
        )
    if commit:
        session.commit()


def seed_reference_catalog(session: Session) -> None:
    seed_reference_records(session)
    seed_technical_references(session)
