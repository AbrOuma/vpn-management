import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('wireguard')


def notify_server_down(server):
    from apps.accounts.models import Account
    superadmins = Account.objects.filter(is_superuser=True, is_active=True)
    emails = [a.email for a in superadmins if a.email]
    if not emails:
        return

    subject = f'[WireGuard Manager] Server Down: {server.name}'
    message = (
        f'The WireGuard service on server "{server.name}" ({server.ssh_host}) '
        f'has been detected as DOWN.\n\n'
        f'Please log in to the dashboard to investigate and restart the service.\n\n'
        f'This is an automated alert from WireGuard Manager.'
    )

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=False)
        logger.info('Downtime alert sent for server %s to %s', server.name, emails)
    except Exception as e:
        logger.error('Failed to send downtime alert for %s: %s', server.name, e)


def notify_server_up(server):
    from apps.accounts.models import Account
    superadmins = Account.objects.filter(is_superuser=True, is_active=True)
    emails = [a.email for a in superadmins if a.email]
    if not emails:
        return

    subject = f'[WireGuard Manager] Server Recovered: {server.name}'
    message = (
        f'The WireGuard service on server "{server.name}" ({server.ssh_host}) '
        f'is back UP.\n\n'
        f'No further action is required.\n\n'
        f'This is an automated alert from WireGuard Manager.'
    )

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=False)
        logger.info('Recovery alert sent for server %s to %s', server.name, emails)
    except Exception as e:
        logger.error('Failed to send recovery alert for %s: %s', server.name, e)