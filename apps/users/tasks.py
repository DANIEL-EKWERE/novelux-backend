import re
import logging
from datetime import date, datetime

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────

def _ocr_image(image_field):
    """Run pytesseract on an ImageField and return raw text."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_field)
        return pytesseract.image_to_string(img, config='--psm 6')
    except Exception as exc:
        logger.warning('OCR failed: %s', exc)
        return ''


def _extract_fields(text):
    """
    Parse name, DOB and ID number from raw OCR text.
    Returns dict with keys: name, dob (date|None), id_number.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # ── DOB: look for patterns like 12/05/1990, 1990-05-12, 12 May 1990
    dob = None
    dob_patterns = [
        r'\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b',   # DD/MM/YYYY or DD-MM-YYYY
        r'\b(\d{4})[/\-.](\d{2})[/\-.](\d{2})\b',   # YYYY-MM-DD
        r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b',
    ]
    month_map = {m: i+1 for i, m in enumerate(
        ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    )}
    for pat in dob_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                g = m.groups()
                if len(g) == 3:
                    if g[0].isdigit() and len(g[0]) == 4:      # YYYY-MM-DD
                        dob = date(int(g[0]), int(g[1]), int(g[2]))
                    elif g[1] in month_map or g[1].capitalize()[:3] in month_map:
                        mon = month_map.get(g[1].capitalize()[:3], int(g[1]))
                        dob = date(int(g[2]), mon, int(g[0]))
                    else:                                        # DD/MM/YYYY
                        dob = date(int(g[2]), int(g[1]), int(g[0]))
                break
            except (ValueError, TypeError):
                continue

    # ── ID number: 6-20 alphanumeric chars, often on its own line
    id_number = ''
    id_pat = re.search(r'\b([A-Z]{0,3}\d{6,20}[A-Z]{0,3})\b', text)
    if id_pat:
        id_number = id_pat.group(1)

    # ── Name: first line that looks like a full name (2+ capitalised words)
    name = ''
    name_pat = re.compile(r'^([A-Z][a-z]+(?: [A-Z][a-z]+){1,4})$')
    for line in lines:
        if name_pat.match(line):
            name = line
            break
    # fallback: longest all-caps line (some IDs print name in caps)
    if not name:
        caps_lines = [l for l in lines if l.isupper() and len(l.split()) >= 2]
        if caps_lines:
            name = max(caps_lines, key=len).title()

    return {'name': name, 'dob': dob, 'id_number': id_number}


def _fuzzy_score(a, b):
    """Return 0-100 similarity score between two strings."""
    try:
        from rapidfuzz import fuzz
        return fuzz.token_sort_ratio(a.lower(), b.lower())
    except ImportError:
        # Fallback: simple character overlap ratio
        a, b = a.lower(), b.lower()
        if not a or not b:
            return 0
        common = sum(1 for c in a if c in b)
        return int(common / max(len(a), len(b)) * 100)


def _run_ocr_and_match(kyc_id):
    """Core logic — runs synchronously (called by task or signal fallback)."""
    from apps.users.models import AuthorKYC

    try:
        kyc = AuthorKYC.objects.select_related('user').get(pk=kyc_id)
    except AuthorKYC.DoesNotExist:
        return

    kyc.status = AuthorKYC.STATUS_PROCESSING
    kyc.save(update_fields=['status'])

    # OCR the front image (primary source); merge back text if available
    front_text = _ocr_image(kyc.id_front) if kyc.id_front else ''
    back_text  = _ocr_image(kyc.id_back)  if kyc.id_back  else ''
    full_text  = f'{front_text}\n{back_text}'

    extracted = _extract_fields(full_text)

    # ── store raw OCR output
    kyc.ocr_name      = extracted['name']
    kyc.ocr_dob       = extracted['dob']
    kyc.ocr_id_number = extracted['id_number']
    kyc.ocr_raw       = {
        'front_text': front_text[:3000],
        'back_text':  back_text[:3000],
        'extracted':  {
            'name':      extracted['name'],
            'dob':       str(extracted['dob']) if extracted['dob'] else '',
            'id_number': extracted['id_number'],
        },
    }

    # ── name match
    name_score = _fuzzy_score(extracted['name'], kyc.full_name)
    kyc.name_match_score = float(name_score)

    # ── DOB match
    dob_match = False
    if extracted['dob'] and kyc.date_of_birth:
        dob_match = extracted['dob'] == kyc.date_of_birth
    kyc.dob_match = dob_match

    # ── age check (18 <= age <= 50) using the OCR DOB if available, else submitted DOB
    ref_dob = extracted['dob'] or kyc.date_of_birth
    age_valid = None
    if ref_dob:
        today = date.today()
        age = today.year - ref_dob.year - (
            (today.month, today.day) < (ref_dob.month, ref_dob.day)
        )
        age_valid = 18 <= age <= 50
    kyc.age_valid = age_valid

    # ── overall score: 60% name + 40% DOB
    dob_score = 100 if dob_match else 0
    kyc.overall_match_score = round(0.6 * name_score + 0.4 * dob_score, 1)

    # ── advance to SE review
    kyc.status = AuthorKYC.STATUS_REVIEW
    kyc.save(update_fields=[
        'ocr_name', 'ocr_dob', 'ocr_id_number', 'ocr_raw',
        'name_match_score', 'dob_match', 'overall_match_score',
        'age_valid', 'status',
    ])

    # notify the author's assigned SE
    try:
        from apps.editorial.models import AuthorEditorLink
        from apps.notifications.services import create_notification
        link = AuthorEditorLink.objects.filter(author=kyc.user).select_related('assigned_se').first()
        if link and link.assigned_se:
            create_notification(
                link.assigned_se,
                'kyc_review',
                f'{kyc.user.username} has submitted KYC for your review.',
            )
    except Exception:
        pass


# ── Celery task ────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_kyc_ocr(self, kyc_id):
    """Celery task: run OCR + matching for a KYC submission."""
    try:
        _run_ocr_and_match(kyc_id)
    except Exception as exc:
        logger.error('process_kyc_ocr failed for kyc_id=%s: %s', kyc_id, exc)
        raise self.retry(exc=exc)
