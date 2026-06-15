# # # """
# # # apps/editorial/tasks.py
# # # =======================
# # # Email helpers for the editorial onboarding flow.
# # # Uses Django's built-in send_mail (no Celery required).
# # # """

# # # from django.core.mail import send_mail
# # # from django.conf import settings
# # # from django.template.loader import render_to_string


# # # ROLE_LABELS = {
# # #     'ae': 'Assistant Editor',
# # #     'se': 'Senior Editor',
# # #     'ce': 'Chief Editor',
# # # }


# # # def send_editor_invite_email(invite, request):
# # #     """
# # #     Send the onboarding invite email to the invitee.
# # #     The email contains a one-time link to /editorial/invite/<token>/.
# # #     """
# # #     scheme    = 'https' if request.is_secure() else 'http'
# # #     host      = request.get_host()
# # #     invite_url = f'{scheme}://{host}/editorial/invite/{invite.token}/'

# # #     role_label = ROLE_LABELS.get(invite.role, invite.role.upper())
# # #     platform   = 'Novelux'
# # #     from_email = settings.DEFAULT_FROM_EMAIL

# # #     subject = f'You have been invited to join {platform} as {role_label}'

# # #     # Plain-text version
# # #     text_body = f"""
# # # Hi,

# # # {invite.invited_by.get_full_name() or invite.invited_by.username} (Chief Editor at {platform}) has invited you to join the editorial team as a {role_label}.

# # # Use the link below to set up your account. This link expires in 7 days.

# # # {invite_url}

# # # If you did not expect this invitation, you can safely ignore this email.

# # # – The {platform} Team
# # # """.strip()

# # #     # HTML version
# # #     html_body = f"""
# # # <!DOCTYPE html>
# # # <html>
# # # <head>
# # # <meta charset="UTF-8"/>
# # # <style>
# # #   body {{ font-family: -apple-system, 'Geist', sans-serif; font-size: 14px; color: #111; background: #fff; margin: 0; padding: 0; }}
# # #   .wrap {{ max-width: 520px; margin: 40px auto; padding: 0 20px; }}
# # #   .logo {{ display: flex; align-items: center; gap: 8px; margin-bottom: 32px; }}
# # #   .logo-box {{ width: 28px; height: 28px; background: hsl(14 62% 38%); border-radius: 6px; display: flex; align-items: center; justify-content: center; }}
# # #   .logo-txt {{ font-size: 16px; font-weight: 700; letter-spacing: .04em; }}
# # #   h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 8px; letter-spacing: -.02em; }}
# # #   p {{ font-size: 14px; color: #444; line-height: 1.6; margin-bottom: 16px; }}
# # #   .role-badge {{ display: inline-block; padding: 4px 12px; font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; background: hsl(14 62% 38% / .1); color: hsl(14 62% 38%); margin-bottom: 20px; }}
# # #   .btn {{ display: inline-block; padding: 13px 28px; background: hsl(14 62% 38%); color: #fff !important; font-size: 14px; font-weight: 600; text-decoration: none; letter-spacing: .02em; }}
# # #   .btn:hover {{ opacity: .88; }}
# # #   .link-alt {{ font-size: 12px; color: #888; margin-top: 16px; word-break: break-all; }}
# # #   .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999; }}
# # #   .divider {{ border: none; border-top: 1px solid #eee; margin: 28px 0; }}
# # # </style>
# # # </head>
# # # <body>
# # # <div class="wrap">
# # #   <div class="logo">
# # #     <div class="logo-box">
# # #       <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
# # #     </div>
# # #     <span class="logo-txt">{platform}</span>
# # #   </div>

# # #   <h1>You're invited to the editorial team</h1>
# # #   <div class="role-badge">{role_label}</div>

# # #   <p>
# # #     <strong>{invite.invited_by.get_full_name() or invite.invited_by.username}</strong>
# # #     has invited you to join <strong>{platform}</strong> as a {role_label}.
# # #   </p>

# # #   <p>Click the button below to create your editor account. Your role will be pre-configured — you just need to set up a username and password.</p>

# # #   {'<p><strong>You will report to:</strong> ' + (invite.supervisor.get_full_name() or invite.supervisor.username) + '</p>' if invite.supervisor else ''}

# # #   <a href="{invite_url}" class="btn">Accept Invitation →</a>

# # #   <p class="link-alt">Or copy this link: {invite_url}</p>

# # #   <hr class="divider"/>
# # #   <p style="font-size:13px;color:#666;">This invitation expires in <strong>7 days</strong>. If you didn't expect this email, you can safely ignore it.</p>

# # #   <div class="footer">© {platform}. This is an automated message — please do not reply.</div>
# # # </div>
# # # </body>
# # # </html>
# # # """

# # #     send_mail(
# # #         subject      = subject,
# # #         message      = text_body,
# # #         from_email   = from_email,
# # #         recipient_list = [invite.email],
# # #         html_message = html_body,
# # #         fail_silently = False,
# # #     )


# # """
# # apps/editorial/tasks.py
# # =======================
# # Email helpers for the editorial onboarding flow.
# # Uses Django's built-in send_mail (no Celery required).
# # """

# # from django.core.mail import send_mail
# # from django.conf import settings
# # from django.template.loader import render_to_string


# # ROLE_LABELS = {
# #     'ae': 'Assistant Editor',
# #     'se': 'Senior Editor',
# #     'ce': 'Chief Editor',
# # }


# # def send_editor_invite_email(invite, request):
# #     """
# #     Send the onboarding invite email to the invitee.
# #     The email contains a one-time link to /editorial/invite/<token>/.
# #     """
# #     # scheme    = 'https' if request.is_secure() else 'http'
# #     # host      = request.get_host()
# #     # invite_url = f'{scheme}://{host}/editorial/invite/{invite.token}/'
# #     from django.conf import settings

# #     site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
# #     if site_url:
# #         invite_url = f'{site_url}/editorial/invite/{invite.token}/'
# #     else:
# #         scheme = 'https' if request.is_secure() else 'http'
# #         invite_url = f'{scheme}://{request.get_host()}/editorial/invite/{invite.token}/'

# #     role_label = ROLE_LABELS.get(invite.role, invite.role.upper())
# #     platform   = 'Novelux'
# #     from_email = settings.DEFAULT_FROM_EMAIL

# #     subject = f'You have been invited to join {platform} as {role_label}'

# #     # Plain-text version
# #     text_body = f"""
# # Hi,

# # {invite.invited_by.get_full_name() or invite.invited_by.username} (Chief Editor at {platform}) has invited you to join the editorial team as a {role_label}.

# # Use the link below to set up your account. This link expires in 7 days.

# # {invite_url}

# # If you did not expect this invitation, you can safely ignore this email.

# # – The {platform} Team
# # """.strip()

# #     # HTML version
# #     supervisor_line = (
# #         f'<p style="font-size:14px;color:#555;margin:0 0 16px;">'
# #         f'<strong style="color:#111;">You will report to:</strong> '
# #         f'{invite.supervisor.get_full_name() or invite.supervisor.username}</p>'
# #         if invite.supervisor else ''
# #     )
# #     invited_by_name = invite.invited_by.get_full_name() or invite.invited_by.username

# #     html_body = f"""<!DOCTYPE html>
# # <html lang="en">
# # <head>
# # <meta charset="UTF-8"/>
# # <meta name="viewport" content="width=device-width,initial-scale=1"/>
# # <style>
# #   body{{margin:0;padding:0;background:#f5f4f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
# #   .outer{{background:#f5f4f0;padding:40px 16px;}}
# #   .card{{background:#ffffff;max-width:520px;margin:0 auto;border-radius:12px;overflow:hidden;border:1px solid #e8e6e0;}}
# #   .header{{padding:28px 32px 0;}}
# #   .logo{{display:flex;align-items:center;gap:8px;margin-bottom:28px;}}
# #   .logo-box{{width:28px;height:28px;background:hsl(14,62%,38%);border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
# #   .logo-txt{{font-size:16px;font-weight:700;letter-spacing:.04em;color:#111;}}
# #   .eyebrow{{font-size:12px;color:#888;letter-spacing:.06em;text-transform:uppercase;margin:0 0 10px;}}
# #   h1{{font-size:22px;font-weight:600;color:#111;margin:0 0 14px;letter-spacing:-.02em;line-height:1.3;}}
# #   .badge{{display:inline-block;padding:4px 12px;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;background:hsl(14,62%,38%,0.1);color:hsl(14,62%,30%);border-radius:4px;margin-bottom:22px;}}
# #   .body{{padding:0 32px 28px;}}
# #   p{{font-size:14px;color:#555;line-height:1.7;margin:0 0 16px;}}
# #   strong{{color:#111;}}
# #   .btn-wrap{{margin:4px 0 20px;}}
# #   .btn{{display:inline-block;padding:13px 28px;background:hsl(14,62%,38%);color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;border-radius:6px;letter-spacing:.02em;}}
# #   .link-alt{{font-size:12px;color:#999;margin:0 0 24px;word-break:break-all;}}
# #   .link-alt a{{color:#888;}}
# #   .notice{{background:#faf9f7;border-top:1px solid #eee;padding:16px 32px;}}
# #   .notice p{{font-size:13px;color:#777;margin:0;}}
# #   .footer{{background:#f0ede8;padding:14px 32px;border-top:1px solid #e8e6e0;}}
# #   .footer p{{font-size:12px;color:#aaa;margin:0;}}
# # </style>
# # </head>
# # <body>
# # <div class="outer">
# #   <div class="card">
# #     <div class="header">
# #       <div class="logo">
# #         <div class="logo-box">
# #           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
# #             <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
# #             <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
# #           </svg>
# #         </div>
# #         <span class="logo-txt">{platform}</span>
# #       </div>
# #       <p class="eyebrow">Editorial invitation</p>
# #       <h1>You're invited to the editorial team</h1>
# #       <div class="badge">{role_label}</div>
# #     </div>

# #     <div class="body">
# #       <p><strong>{invited_by_name}</strong> has invited you to join <strong>{platform}</strong> as a {role_label}.</p>
# #       <p>Click the button below to create your editor account. Your role will be pre-configured — you just need to set up a username and password.</p>
# #       {supervisor_line}
# #       <div class="btn-wrap">
# #         <a href="{invite_url}" class="btn">Accept invitation &rarr;</a>
# #       </div>
# #       <p class="link-alt">Or copy this link: <a href="{invite_url}">{invite_url}</a></p>
# #     </div>

# #     <div class="notice">
# #       <p>This invitation expires in <strong>7 days</strong>. If you didn't expect this email, you can safely ignore it.</p>
# #     </div>

# #     <div class="footer">
# #       <p>&copy; {platform}. This is an automated message &mdash; please do not reply.</p>
# #     </div>
# #   </div>
# # </div>
# # </body>
# # </html>"""

# #     send_mail(
# #         subject      = subject,
# #         message      = text_body,
# #         from_email   = from_email,
# #         recipient_list = [invite.email],
# #         html_message = html_body,
# #         fail_silently = False,
# #     )

# """
# apps/editorial/tasks.py
# =======================
# Email helpers for the editorial onboarding flow.
# Uses Django's built-in send_mail (no Celery required).
# """

# from django.core.mail import send_mail
# from django.conf import settings
# from django.template.loader import render_to_string


# ROLE_LABELS = {
#     'ae': 'Acquisition Editor',
#     'se': 'Senior Editor',
#     'ce': 'Chief Editor',
# }


# def send_editor_invite_email(invite, request):
#     """
#     Send the onboarding invite email to the invitee.
#     The email contains a one-time link to /editorial/invite/<token>/.
#     """
#     scheme    = 'https' if request.is_secure() else 'http'
#     host      = request.get_host()
#     invite_url = f'{scheme}://{host}/editorial/invite/{invite.token}/'

#     role_label = ROLE_LABELS.get(invite.role, invite.role.upper())
#     platform   = 'Novelux'
#     from_email = settings.DEFAULT_FROM_EMAIL

#     subject = f'You have been invited to join {platform} as {role_label}'

#     # Plain-text version
#     text_body = f"""
# Hi,

# {invite.invited_by.get_full_name() or invite.invited_by.username} (Chief Editor at {platform}) has invited you to join the editorial team as a {role_label}.

# Use the link below to set up your account. This link expires in 7 days.

# {invite_url}

# If you did not expect this invitation, you can safely ignore this email.

# – The {platform} Team
# """.strip()

#     # HTML version
#     supervisor_line = (
#         f'<p style="font-size:14px;color:#555;margin:0 0 16px;">'
#         f'<strong style="color:#111;">You will report to:</strong> '
#         f'{invite.supervisor.get_full_name() or invite.supervisor.username}</p>'
#         if invite.supervisor else ''
#     )
#     invited_by_name = invite.invited_by.get_full_name() or invite.invited_by.username

#     html_body = f"""<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="UTF-8"/>
# <meta name="viewport" content="width=device-width,initial-scale=1"/>
# <style>
#   body{{margin:0;padding:0;background:#f5f4f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
#   .outer{{background:#f5f4f0;padding:40px 16px;}}
#   .card{{background:#ffffff;max-width:520px;margin:0 auto;border-radius:12px;overflow:hidden;border:1px solid #e8e6e0;}}
#   .header{{padding:28px 32px 0;}}
#   .logo{{display:flex;align-items:center;gap:8px;margin-bottom:28px;}}
#   .logo-box{{width:28px;height:28px;background:hsl(14,62%,38%);border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
#   .logo-txt{{font-size:16px;font-weight:700;letter-spacing:.04em;color:#111;}}
#   .eyebrow{{font-size:12px;color:#888;letter-spacing:.06em;text-transform:uppercase;margin:0 0 10px;}}
#   h1{{font-size:22px;font-weight:600;color:#111;margin:0 0 14px;letter-spacing:-.02em;line-height:1.3;}}
#   .badge{{display:inline-block;padding:4px 12px;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;background:hsl(14,62%,38%,0.1);color:hsl(14,62%,30%);border-radius:4px;margin-bottom:22px;}}
#   .body{{padding:0 32px 28px;}}
#   p{{font-size:14px;color:#555;line-height:1.7;margin:0 0 16px;}}
#   strong{{color:#111;}}
#   .btn-wrap{{margin:4px 0 20px;}}
#   .btn{{display:inline-block;padding:13px 28px;background:hsl(14,62%,38%);color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;border-radius:6px;letter-spacing:.02em;}}
#   .link-alt{{font-size:12px;color:#999;margin:0 0 24px;word-break:break-all;}}
#   .link-alt a{{color:#888;}}
#   .notice{{background:#faf9f7;border-top:1px solid #eee;padding:16px 32px;}}
#   .notice p{{font-size:13px;color:#777;margin:0;}}
#   .footer{{background:#f0ede8;padding:14px 32px;border-top:1px solid #e8e6e0;}}
#   .footer p{{font-size:12px;color:#aaa;margin:0;}}
# </style>
# </head>
# <body>
# <div class="outer">
#   <div class="card">
#     <div class="header">
#       <div class="logo">
#         <div class="logo-box">
#           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
#             <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
#             <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
#           </svg>
#         </div>
#         <span class="logo-txt">{platform}</span>
#       </div>
#       <p class="eyebrow">Editorial invitation</p>
#       <h1>You're invited to the editorial team</h1>
#       <div class="badge">{role_label}</div>
#     </div>

#     <div class="body">
#       <p><strong>{invited_by_name}</strong> has invited you to join <strong>{platform}</strong> as a {role_label}.</p>
#       <p>Click the button below to create your editor account. Your role will be pre-configured — you just need to set up a username and password.</p>
#       {supervisor_line}
#       <div class="btn-wrap">
#         <a href="{invite_url}" class="btn">Accept invitation &rarr;</a>
#       </div>
#       <p class="link-alt">Or copy this link: <a href="{invite_url}">{invite_url}</a></p>
#     </div>

#     <div class="notice">
#       <p>This invitation expires in <strong>7 days</strong>. If you didn't expect this email, you can safely ignore it.</p>
#     </div>

#     <div class="footer">
#       <p>&copy; {platform}. This is an automated message &mdash; please do not reply.</p>
#     </div>
#   </div>
# </div>
# </body>
# </html>"""

#     send_mail(
#         subject      = subject,
#         message      = text_body,
#         from_email   = from_email,
#         recipient_list = [invite.email],
#         html_message = html_body,
#         fail_silently = False,
#     )



from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


ROLE_LABELS = {
    'se': 'Senior Editor',
    'ce': 'Chief Editor',
}


def send_editor_invite_email(invite, request):
    """
    Send the onboarding invite email to the invitee.
    The email contains a one-time link to /editorial/invite/<token>/.
    """
    scheme    = 'https' if request.is_secure() else 'http'
    host      = request.get_host()
    # invite_url = f'{scheme}://{host}/editorial/invite/{invite.token}/'
    invite_url = f'https://novelux.onrender.com/editorial/invite/{invite.token}/'

    role_label = ROLE_LABELS.get(invite.role, invite.role.upper())
    platform   = 'Novelux'
    from_email = settings.DEFAULT_FROM_EMAIL

    subject = f'You have been invited to join {platform} as {role_label}'

    # Plain-text version
    text_body = f"""
Hi,

{invite.invited_by.get_full_name() or invite.invited_by.username} (Chief Editor at {platform}) has invited you to join the editorial team as a {role_label}.

Use the link below to set up your account. This link expires in 7 days.

{invite_url}

If you did not expect this invitation, you can safely ignore this email.

– The {platform} Team
""".strip()

    # HTML version
    supervisor_line = (
        f'<p style="font-size:14px;color:#555;margin:0 0 16px;">'
        f'<strong style="color:#111;">You will report to:</strong> '
        f'{invite.supervisor.get_full_name() or invite.supervisor.username}</p>'
        if invite.supervisor else ''
    )
    invited_by_name = invite.invited_by.get_full_name() or invite.invited_by.username

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
  body{{margin:0;padding:0;background:#f5f4f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
  .outer{{background:#f5f4f0;padding:40px 16px;}}
  .card{{background:#ffffff;max-width:520px;margin:0 auto;border-radius:12px;overflow:hidden;border:1px solid #e8e6e0;}}
  .header{{padding:28px 32px 0;}}
  .logo{{display:flex;align-items:center;gap:8px;margin-bottom:28px;}}
  .logo-box{{width:28px;height:28px;background:hsl(14,62%,38%);border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
  .logo-txt{{font-size:16px;font-weight:700;letter-spacing:.04em;color:#111;}}
  .eyebrow{{font-size:12px;color:#888;letter-spacing:.06em;text-transform:uppercase;margin:0 0 10px;}}
  h1{{font-size:22px;font-weight:600;color:#111;margin:0 0 14px;letter-spacing:-.02em;line-height:1.3;}}
  .badge{{display:inline-block;padding:4px 12px;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;background:hsl(14,62%,38%,0.1);color:hsl(14,62%,30%);border-radius:4px;margin-bottom:22px;}}
  .body{{padding:0 32px 28px;}}
  p{{font-size:14px;color:#555;line-height:1.7;margin:0 0 16px;}}
  strong{{color:#111;}}
  .btn-wrap{{margin:4px 0 20px;}}
  .btn{{display:inline-block;padding:13px 28px;background:hsl(14,62%,38%);color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;border-radius:6px;letter-spacing:.02em;}}
  .link-alt{{font-size:12px;color:#999;margin:0 0 24px;word-break:break-all;}}
  .link-alt a{{color:#888;}}
  .notice{{background:#faf9f7;border-top:1px solid #eee;padding:16px 32px;}}
  .notice p{{font-size:13px;color:#777;margin:0;}}
  .footer{{background:#f0ede8;padding:14px 32px;border-top:1px solid #e8e6e0;}}
  .footer p{{font-size:12px;color:#aaa;margin:0;}}
</style>
</head>
<body>
<div class="outer">
  <div class="card">
    <div class="header">
      <div class="logo">
        <div class="logo-box">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
        </div>
        <span class="logo-txt">{platform}</span>
      </div>
      <p class="eyebrow">Editorial invitation</p>
      <h1>You're invited to the editorial team</h1>
      <div class="badge">{role_label}</div>
    </div>

    <div class="body">
      <p><strong>{invited_by_name}</strong> has invited you to join <strong>{platform}</strong> as a {role_label}.</p>
      <p>Click the button below to create your editor account. Your role will be pre-configured — you just need to set up a username and password.</p>
      {supervisor_line}
      <div class="btn-wrap">
        <a href="{invite_url}" class="btn">Accept invitation &rarr;</a>
      </div>
      <p class="link-alt">Or copy this link: <a href="{invite_url}">{invite_url}</a></p>
    </div>

    <div class="notice">
      <p>This invitation expires in <strong>7 days</strong>. If you didn't expect this email, you can safely ignore it.</p>
    </div>

    <div class="footer">
      <p>&copy; {platform}. This is an automated message &mdash; please do not reply.</p>
    </div>
  </div>
</div>
</body>
</html>"""

    send_mail(
        subject      = subject,
        message      = text_body,
        from_email   = from_email,
        recipient_list = [invite.email],
        html_message = html_body,
        fail_silently = False,
    )