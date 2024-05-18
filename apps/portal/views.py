from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from apps.users.models import MagicLinkToken
from django.utils import timezone
from .services import create_magic_link, portal_login, portal_logout, get_portal_user


class PortalLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'your@email.com',
            'autofocus': True,
        })
    )


def portal_login_view(request):
    """
    Show the magic link request form.
    On POST, create a token and (for now) print the link to the terminal.
    """
    # Already logged in
    vpnuser = get_portal_user(request)
    if vpnuser:
        return redirect('portal:dashboard')

    form = PortalLoginForm()
    sent = False

    if request.method == 'POST':
        form = PortalLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            token = create_magic_link(email)

            if token:
                login_url = request.build_absolute_uri(
                    f'/portal/verify/{token.token}/'
                )
                from apps.portal.emails import send_magic_link
                try:
                    send_magic_link(token.user, login_url)
                except Exception:
                    # In development the console backend just prints it
                    pass

            # Always show success - never reveal if email exists
            sent = True

    return render(request, 'portal/login.html', {
        'form': form,
        'sent': sent,
    })


def portal_verify(request, token):
    """
    The user clicks their magic link and lands here.
    Validate the token, log them in, redirect to dashboard.
    """
    magic = get_object_or_404(MagicLinkToken, token=token)

    # Check if token is still valid
    if magic.used or magic.expires_at < timezone.now():
        messages.error(request, 'This login link has expired or already been used.')
        return redirect('portal:login')

    # Mark token as used
    magic.used    = True
    magic.used_at = timezone.now()
    magic.save(update_fields=['used', 'used_at'])

    # Log the user in via session
    portal_login(request, magic.user)

    return redirect('portal:dashboard')


def portal_dashboard_view(request):
    """The user's device list page."""
    vpnuser = get_portal_user(request)

    if not vpnuser:
        return redirect('portal:login')

    devices = vpnuser.devices.select_related(
        'allocated_ip'
    ).prefetch_related('invites').exclude(
        status='revoked'
    )

    return render(request, 'portal/dashboard.html', {
        'vpnuser': vpnuser,
        'devices': devices,
    })


def portal_logout_view(request):
    portal_logout(request)
    return redirect('portal:login')