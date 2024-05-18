from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import DeviceInvite
from .services import generate_client_config, generate_qr_code


def redeem_invite(request, token):
    """
    The page users land on when they click their invite link.
    Shows QR code and download button.
    """
    invite = get_object_or_404(DeviceInvite, token=token)

    # Check if the invite is still valid
    if not invite.is_valid:
        reasons = {
            DeviceInvite.Status.USED:    'This link has already been used.',
            DeviceInvite.Status.EXPIRED: 'This link has expired.',
            DeviceInvite.Status.REVOKED: 'This link has been revoked.',
        }
        reason = reasons.get(invite.status, 'This link is no longer valid.')
        return render(request, 'invites/invalid.html', {'reason': reason})

    device        = invite.device
    config_text   = generate_client_config(device)
    qr_code       = generate_qr_code(config_text)

    # Mark invite as used
    ip = request.META.get('REMOTE_ADDR')
    invite.mark_used(ip_address=ip)

    return render(request, 'invites/redeem.html', {
        'invite':  invite,
        'device':  device,
        'qr_code': qr_code,
    })


def download_config(request, token):
    """
    Returns the raw .conf file as a download.
    Only works if the invite was already redeemed on this same page load.
    We regenerate the config from the device - the invite token
    just identifies which device to generate it for.
    """
    invite = get_object_or_404(DeviceInvite, token=token)
    device = invite.device

    config_text = generate_client_config(device)

    # Return as a downloadable file
    filename = f'{device.name.replace(" ", "_")}.conf'
    response = HttpResponse(config_text, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response