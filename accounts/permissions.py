from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view):
    @wraps(view)
    @login_required
    def checked(request, *args, **kwargs):
        if not request.user.is_administrator:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return checked
