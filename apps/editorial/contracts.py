"""Contract templates and sending — shared by the SE and CE send paths."""
import html
import logging
import threading

import bleach
from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)

# Tags a template may use. Everything else (scripts, styles, attributes,
# links) is stripped, so a template can never inject code into the page the
# author signs on.
ALLOWED_TAGS = ['p', 'br', 'h2', 'h3', 'h4', 'strong', 'b', 'em', 'i', 'u',
                'ul', 'ol', 'li', 'blockquote', 'hr']

LICENCE_CLAUSES = {
    'exclusive': (
        'The Author grants HuxNovel an <strong>exclusive</strong> licence to publish, distribute, '
        'and monetise the Work on the HuxNovel platform and its affiliated channels. The Author '
        'may not publish the Work on any other platform during the term of this agreement '
        'without prior written consent.'
    ),
    'non_exclusive': (
        'The Author grants HuxNovel a <strong>non-exclusive</strong> licence to publish, '
        'distribute, and monetise the Work on the HuxNovel platform. The Author retains the '
        'right to publish the Work elsewhere.'
    ),
}

PLACEHOLDERS = ['author_name', 'pen_name', 'book_title', 'contract_type', 'date',
                'platform', 'licence_clause']


def clean_template_html(body):
    return bleach.clean(body or '', tags=ALLOWED_TAGS, attributes={}, strip=True).strip()


def render_contract(body, story, contract_type):
    """Fill a template's placeholders for one story. Values are escaped;
    only {licence_clause} contributes markup (fixed, trusted text)."""
    if contract_type not in LICENCE_CLAUSES:
        contract_type = 'non_exclusive'
    author  = story.author
    profile = getattr(author, 'author_profile', None)
    full    = author.get_full_name() or author.username
    pen     = (profile.pen_name or '').strip() if profile else ''
    values = {
        'author_name':   html.escape(full),
        'pen_name':      html.escape(pen or full),
        'book_title':    html.escape(story.title),
        'contract_type': 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive',
        'date':          timezone.localdate().strftime('%-d %B %Y'),
        'platform':      'HuxNovel',
        'licence_clause': LICENCE_CLAUSES[contract_type],
    }
    out = clean_template_html(body)
    for key, val in values.items():
        out = out.replace('{' + key + '}', val)
    return out


def send_contract(*, sender, story, contract_type, note='', template=None):
    """Send `story`'s author a contract built from `template` (or the default
    template). Freezes the rendered text on the ContractApplication, emails
    and notifies the author, and moves the story to awaiting_signature."""
    from .models import ContractApplication, ContractTemplate

    if contract_type not in LICENCE_CLAUSES:
        contract_type = 'non_exclusive'
    if template is None:
        template = ContractTemplate.objects.filter(is_active=True, is_default=True).first()
    body = render_contract(template.body, story, contract_type) if template else ''

    now = timezone.now()
    app, created = ContractApplication.objects.get_or_create(
        story=story, defaults={'author': story.author})
    app.status           = ContractApplication.STATUS_CONTRACT_SENT
    app.contract_sent_at = now
    app.ce_signed_by     = sender      # the editor countersigning for the platform
    app.ce_signed_at     = now
    app.contract_type    = contract_type
    app.template         = template
    app.contract_body    = body
    if note:
        app.se_note = (app.se_note + f'\n{sender.role.upper()} note: ' + note).strip()
    app.save()

    story.contract_status = 'awaiting_signature'
    story.save(update_fields=['contract_status'])

    _email_author_async(story, contract_type, note)
    try:
        from apps.notifications.services import on_contract_sent
        on_contract_sent(story.author, story, contract_type)
    except Exception:
        log.exception('Contract notification failed for %s', story.slug)
    return app


def _email_author_async(story, contract_type, note):
    # Sent in a background thread — SMTP can be slow and Render times out.
    slug, email = story.slug, story.author.email
    name, title = story.author.first_name or story.author.username, story.title

    def _send():
        try:
            from django.core.mail import send_mail
            label    = 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive'
            sign_url = f'https://www.novelux.app/my-books/{slug}/contract/'
            body = (
                f'Hello {name},\n\n'
                f'congratulations!\n\n'
                f'Your book "{title}" has been reviewed, and we are offering you a {label} contract.\n\n'
                f'You can review carefully and sign your contract successfully using the attached link below:\n{sign_url}\n\n'
                f"We're excited to have you as part of HuxNovel (formerly NoveluX) and looking forward to "
                f'supporting your journey as an author!\n\n'
                'Warm regards,\n'
                + (f'Editor note: {note}\n\n' if note else '')
                + '– The HuxNovel Editorial Team'
            )
            send_mail(subject=f'Your HuxNovel contract offer — "{title}"', message=body,
                      from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[email],
                      fail_silently=False)
            log.info('Contract email sent to %s for story %s', email, slug)
        except Exception as e:
            log.error('Contract email failed for %s: %s', slug, e)

    threading.Thread(target=_send, daemon=True).start()
