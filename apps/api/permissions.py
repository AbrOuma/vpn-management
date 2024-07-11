from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Full access — admins only."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsAdminOrDeviceOwner(BasePermission):
    """
    Admins: full access.
    Regular users: only allowed on safe methods (GET),
    and only for their own devices (enforced at queryset level).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        # Non-admins allowed only on GET
        return request.method in ('GET', 'HEAD', 'OPTIONS')