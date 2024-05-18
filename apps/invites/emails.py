from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger('wireguard')


def send_device_invite(invite, base_url: str = '') -> None:
    """
    Send the device invite email to the user.
    base_url should be the full domain e.g. http://127.0.0.1:8000
    """
    device  = invite.device
    vpnuser = device.user

    if not vpnuser or not vpnuser.email:
        logger.warning(
            'Device %s has no assigned user — skipping invite email',
            device.name
        )
        return

    invite_url = f'{base_url}/connect/{invite.token}/'

    context = {
        'vpnuser':    vpnuser,
        'device':     device,
        'invite_url': invite_url,
    }

    html_body = render_to_string('emails/device_invite.html', context)

    msg = EmailMultiAlternatives(
        subject    = 'You have been granted VPN access',
        body       = f'Set up your VPN device here: {invite_url}',
        from_email = settings.DEFAULT_FROM_EMAIL,
        to         = [vpnuser.email],
    )
    msg.attach_alternative(html_body, 'text/html')

    try:
        msg.send()
        logger.info(
            'Invite email sent to %s for device %s',
            vpnuser.email,
            device.name
        )
    except Exception as e:
        logger.error(
            'Failed to send invite to %s: %s',
            vpnuser.email, e
        )
        raise