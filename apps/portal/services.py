import secrets
from django.utils import timezone
from datetime import timedelta
from apps.users.models import VPNUser, MagicLinkToken


def create_magic_link(email: str) -> MagicLinkToken | None:
    """
    Look up a VPN user by email and create a magic link token.
    Returns None if no user exists with that email.
    We never reveal whether the email exists — the caller
    should always show the same success message either way.
    """
    try:
        vpnuser = VPNUser.objects.get(
            email=email,
            status=VPNUser.Status.ACTIVE
        )
    except VPNUser.DoesNotExist:
        return None

    token = MagicLinkToken.objects.create(
        user=vpnuser,
        token=secrets.token_urlsafe(64),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    return token


SESSION_KEY = 'portal_user_id'


def portal_login(request, vpnuser):
    """Store the VPN user's ID in the session."""
    request.session[SESSION_KEY] = str(vpnuser.pk)


def portal_logout(request):
    """Remove the VPN user from the session."""
    request.session.pop(SESSION_KEY, None)


def get_portal_user(request):
    """
    Return the currently logged-in VPN user from the session.
    Returns None if not logged in.
    """
    user_id = request.session.get(SESSION_KEY)
    if not user_id:
        return None
    try:
        return VPNUser.objects.get(pk=user_id, status=VPNUser.Status.ACTIVE)
    except VPNUser.DoesNotExist:
        return None