from collections import Counter, defaultdict

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import Event, QaFlag


def _normalize_message(message: str) -> str:
    normalized = message
    for token in ('changed from', 'has logged in', 'has been automatically logged off', 'executed by'):
        if token in normalized:
            return normalized
    return normalized


def summarize_event_patterns(session: Session, asset_id: int | None = None, batch_id: int | None = None) -> dict:
    query = session.query(Event)
    if asset_id is not None:
        query = query.filter(Event.asset_id == asset_id)
    if batch_id is not None:
        query = query.filter(Event.file.has(batch_id=batch_id))
    events = query.order_by(Event.occurred_at.asc(), Event.id.asc()).all()

    recurring_counter: Counter[tuple[str, int | None]] = Counter()
    chattering_counter: Counter[tuple[str, int | None]] = Counter()
    operator_windows: dict[str, list[str]] = defaultdict(list)

    last_by_signature: dict[tuple[str, int | None], Event] = {}
    last_login_by_actor: dict[str, Event] = {}

    for event in events:
        signature = (_normalize_message(event.message), event.run_number)
        recurring_counter[signature] += 1

        previous = last_by_signature.get(signature)
        if (
            previous is not None
            and previous.occurred_at is not None
            and event.occurred_at is not None
            and (event.occurred_at - previous.occurred_at).total_seconds() <= 120
            and event.category == previous.category
        ):
            chattering_counter[signature] += 1
        last_by_signature[signature] = event

        if event.event_type == 'login' and event.actor:
            last_login_by_actor[event.actor] = event
        elif event.event_type == 'logout' and event.actor:
            login_event = last_login_by_actor.get(event.actor)
            if login_event and login_event.occurred_at and event.occurred_at:
                seconds = int((event.occurred_at - login_event.occurred_at).total_seconds())
                operator_windows[event.actor].append(f'{seconds // 60} min')

    recurring_patterns = [
        {
            'title': signature[0],
            'count': count,
            'severity': 'warning' if count >= 3 else 'info',
            'detail': f'Run {signature[1]}' if signature[1] is not None else 'Sem run especifico',
        }
        for signature, count in recurring_counter.most_common(5)
        if count >= 2
    ]

    chattering_patterns = [
        {
            'title': signature[0],
            'count': count,
            'severity': 'high' if count >= 2 else 'warning',
            'detail': f'Repeticao em janela curta no run {signature[1]}' if signature[1] is not None else 'Repeticao em janela curta',
        }
        for signature, count in chattering_counter.most_common(5)
    ]

    operator_items = [
        {
            'title': actor,
            'count': len(windows),
            'severity': 'info',
            'detail': ', '.join(windows),
        }
        for actor, windows in operator_windows.items()
    ]

    return {
        'asset_id': asset_id,
        'batch_id': batch_id,
        'total_events': len(events),
        'recurring_patterns': recurring_patterns,
        'chattering_patterns': chattering_patterns,
        'operator_windows': operator_items,
    }


def persist_event_flags(session: Session, summary: dict) -> None:
    asset_id = summary.get('asset_id')
    if asset_id is None or summary.get('batch_id') is not None:
        return

    session.execute(
        delete(QaFlag).where(
            QaFlag.related_entity_type == 'asset',
            QaFlag.related_entity_id == asset_id,
            QaFlag.flag_type.in_(['event_recurring', 'event_chattering', 'operator_window']),
        )
    )

    for item in summary['recurring_patterns']:
        session.add(
            QaFlag(
                related_entity_type='asset',
                related_entity_id=asset_id,
                flag_type='event_recurring',
                severity=item['severity'],
                message=f"{item['title']} ({item['count']}x) - {item['detail']}",
            )
        )

    for item in summary['chattering_patterns']:
        session.add(
            QaFlag(
                related_entity_type='asset',
                related_entity_id=asset_id,
                flag_type='event_chattering',
                severity=item['severity'],
                message=f"{item['title']} ({item['count']}x) - {item['detail']}",
            )
        )

    for item in summary['operator_windows']:
        session.add(
            QaFlag(
                related_entity_type='asset',
                related_entity_id=asset_id,
                flag_type='operator_window',
                severity=item['severity'],
                message=f"{item['title']} - {item['detail']}",
            )
        )

    session.commit()
