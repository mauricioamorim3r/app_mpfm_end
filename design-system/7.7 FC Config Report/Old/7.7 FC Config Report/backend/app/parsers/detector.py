import re


def detect_document_type(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith('.zip'):
        return 'zip_archive'
    if re.match(r'configuration-.*\.txt$', lowered):
        return 'configuration_report'
    if re.match(r'events_snapshot-.*\.txt$', lowered):
        return 'events_snapshot'
    if lowered == 'parameters.xml':
        return 'parameters_xml'
    if re.match(r'00[1-4]_.*\.xml$', lowered):
        return 'production_xml'
    if lowered == 'security.xml':
        return 'security_xml'
    if re.match(r'alarmsandevents_daily-.*\.txt$', lowered):
        return 'alarms_events_daily'
    if re.match(r'run_(daily|hourly|24hours).*\.txt$', lowered):
        return 'run_report'
    if lowered.endswith('.pdf'):
        return 'pdf_report'
    if lowered.endswith('.txt'):
        return 'plain_text'
    return 'unknown'
