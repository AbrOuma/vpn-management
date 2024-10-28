import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('wireguard')


class Command(BaseCommand):
    help = 'Check WireGuard health on all servers and notify admins on state change'

    def handle(self, *args, **options):
        from apps.server.models import ServerConfig, ServerHealthStatus
        from apps.server.notifications import notify_server_down, notify_server_up
        from wireguard.commands import wg_is_running

        servers = ServerConfig.objects.all()

        if not servers.exists():
            self.stdout.write('No servers configured.')
            return

        for server in servers:
            status, _ = ServerHealthStatus.objects.get_or_create(
                server=server,
                defaults={'is_up': True}
            )

            try:
                is_up = wg_is_running(server, server.interface_name)
            except Exception as e:
                logger.error('Health check failed for %s: %s', server.name, e)
                is_up = False

            was_up = status.is_up

            if was_up and not is_up:
                # Server just went down
                self.stdout.write(f'DOWN: {server.name}')
                notify_server_down(server)
                status.is_up      = False
                status.alerted_at = timezone.now()
                status.save()
                from apps.accounts.utils import log_action_system
                log_action_system('Server Down Detected', server.name, 'Automated health check')

            elif not was_up and is_up:
                # Server just came back up
                self.stdout.write(f'RECOVERED: {server.name}')
                notify_server_up(server)
                status.is_up      = True
                status.alerted_at = timezone.now()
                status.save()
                from apps.accounts.utils import log_action_system
                log_action_system('Server Recovered', server.name, 'Automated health check')

            else:
                self.stdout.write(f'OK: {server.name} ({"up" if is_up else "still down"})')

        self.stdout.write('Health check complete.')