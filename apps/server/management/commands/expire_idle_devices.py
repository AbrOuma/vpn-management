import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('wireguard')

EXPIRY_DAYS = 30


class Command(BaseCommand):
    help = f'Disable active devices with no WireGuard handshake in {EXPIRY_DAYS} days'

    def handle(self, *args, **options):
        from apps.server.models import ServerConfig
        from apps.devices.models import Device
        from apps.server.notifications import notify_device_disabled
        from apps.accounts.utils import log_action_system
        from wireguard.commands import wg_show_dump, parse_wg_dump

        threshold = timezone.now() - timedelta(days=EXPIRY_DAYS)
        servers   = ServerConfig.objects.all()
        count     = 0

        for server in servers:
            try:
                dump  = wg_show_dump(server, server.interface_name)
                peers = parse_wg_dump(dump)
            except Exception as e:
                logger.error('Could not fetch peers from %s: %s', server.name, e)
                continue

            active_devices = Device.objects.filter(
                server=server,
                status=Device.Status.ACTIVE,
            ).select_related('user')

            for device in active_devices:
                peer           = peers.get(device.public_key)
                last_handshake = peer.get('last_handshake') if peer else None

                if last_handshake is None or last_handshake < threshold:
                    device.status = Device.Status.DISABLED
                    device.save(update_fields=['status', 'updated_at'])

                    lh_str = last_handshake.strftime('%d %b %Y %H:%M UTC') if last_handshake else 'Never'

                    log_action_system(
                        'Device Auto-Disabled',
                        device.name,
                        f'No handshake in {EXPIRY_DAYS} days. Last: {lh_str}'
                    )

                    notify_device_disabled(device, lh_str)
                    count += 1

                    self.stdout.write(
                        f'Disabled: {device.name} on {server.name} '
                        f'(last handshake: {lh_str}) '
                        f'{"- owner notified" if device.user else "- no owner assigned"}'
                    )

        if count:
            self.stdout.write(f'{count} device(s) disabled.')
        else:
            self.stdout.write('No idle devices found.')