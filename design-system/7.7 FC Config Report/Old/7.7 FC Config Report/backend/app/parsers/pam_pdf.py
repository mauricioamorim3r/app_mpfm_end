from __future__ import annotations

from io import BytesIO

PAM_TOPIC_KEYS = {
    'pam007126_model_approval',
    'pam007126_environment_limits',
    'pam007126_software_version',
    'pam007126_pulse_frequency_limits',
    'pam007126_calculation_standards',
    'pam007126_power_supply_requirement',
}


def extract_pdf_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('Dependencia pypdf nao instalada; execute pip install -r backend/requirements.txt.') from exc

    reader = PdfReader(BytesIO(payload))
    pages = [(page.extract_text() or '') for page in reader.pages]
    return '\n\n'.join(pages).strip()


def parse_pam007126_pdf(payload: bytes, filename: str) -> dict:
    text = extract_pdf_text(payload)
    lowered = f'{filename}\n{text[:4000]}'.lower()
    is_pam = 'dimel' in lowered and ('64' in lowered or '064' in lowered) and 'flow x/c' in lowered
    if not is_pam:
        return {'parser_name': 'pam_pdf', 'references': [], 'text_excerpt': text[:2000]}
    return {
        'parser_name': 'pam_pdf',
        'references': sorted(PAM_TOPIC_KEYS),
        'text_excerpt': text[:2000],
    }
