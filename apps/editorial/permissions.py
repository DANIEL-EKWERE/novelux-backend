"""
Editorial permission classes.
Used by both DRF API views and the web dashboard views.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSE(BasePermission):
    """Only Senior Editors."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'se'


class IsCE(BasePermission):
    """Only Chief Editors."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ce'


class IsSEOrAbove(BasePermission):
    """SE or CE only."""
    EDITOR_ROLES = {'se', 'ce'}

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in self.EDITOR_ROLES
        )


# Alias for backwards compatibility in views that imported IsAEOrAbove
IsAEOrAbove = IsSEOrAbove


class IsSEForReview(BasePermission):
    """
    The requesting SE must be assigned to this review (or a CE).
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == 'ce':
            return True
        if user.role == 'se':
            return obj.assigned_se == user
        return False


# ─── Django view helpers (not DRF) ───────────────────────────────────────────

def require_role(*roles):
    """
    Decorator for Django web views. Redirects to login if user does not
    have one of the specified roles.

    Usage:
        @require_role('se', 'ce')
        def my_view(request):
            ...
    """
    from functools import wraps
    from django.shortcuts import redirect

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/login/?next=' + request.path)
            if hasattr(request.user, 'role') and request.user.role not in roles:
                return redirect('/login/?next=' + request.path)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def editor_context(user):
    """
    Returns a dict of useful editorial context variables to inject into
    any editor dashboard template context.
    """
    from apps.editorial.models import ContentFlag

    ctx = {
        'editor_role': user.role,
        'editor_username': user.username,
        'editor_email': user.email,
    }

    if user.role == 'se':
        ctx['pending_count'] = 0  # populated by dashboard view
        try:
            ctx['supervisor_ce'] = user.editorial_assignment.supervisor
        except Exception:
            ctx['supervisor_ce'] = None

    elif user.role == 'ce':
        ctx['se_team'] = []
        from apps.editorial.models import EditorialPolicy
        ctx['pending_policies'] = EditorialPolicy.objects.filter(
            status='under_review',
        ).count()

    return ctx
