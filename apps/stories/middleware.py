"""Request context for the mature-content gate.

The gate needs to know two things about the caller that a `user` object does
not carry: which store the request came from (the iOS build must never receive
18+ or explicit fiction, so the App Store rating can stay below 18+) and which
territory it came from (several regulators do not accept a self-declared
birthdate as age assurance).

Both live on the request, but the queryset helpers in `apps.stories.views` are
called from ~30 places that do not all have one to hand. A contextvar keeps the
active request reachable without threading it through every signature, and —
unlike a thread-local — stays correct under ASGI.
"""

import contextvars

_current_request = contextvars.ContextVar('novelux_current_request', default=None)


def get_current_request():
    """The request being served, or None outside a request (shell, Celery)."""
    return _current_request.get()


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)
