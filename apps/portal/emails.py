from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger('wireguard')


def send_magic_link(vpnuser, login_url: str) -> None:
    """Send the magic login link email to a VPN user."""
    context = {
        'vpnuser':   vpnuser,
        'login_url': login_url,
    }

    html_body = render_to_string('emails/magic_link.html', context)

    msg = EmailMultiAlternatives(
        subject  = 'Your VPN Portal Login Link',
        body     = f'Log in here: {login_url}',
        from_email = settings.DEFAULT_FROM_EMAIL,
        to       = [vpnuser.email],
    )
    msg.attach_alternative(html_body, 'text/html')

    try:
        msg.send()
        logger.info('Magic link sent to %s', vpnuser.email)
    except Exception as e:
        logger.error('Failed to send magic link to %s: %s', vpnuser.email, e)
        raise