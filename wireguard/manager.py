import logging
import time

logger = logging.getLogger('wireguard')


class WireGuardManager:

    def __init__(self, server=None):
        from apps.server.models import ServerConfig
        if server:
            self.server = server
        else:
            self.server = ServerConfig.objects.first()
        if not self.server:
            raise RuntimeError('No server configured.')
        self.interface = self.server.interface_name

    def _get_active_peers(self) -> list:
        from apps.devices.models import Device
        devices = Device.objects.filter(
            server=self.server,
            status=Device.Status.ACTIVE,
        ).select_related('allocated_ip')

        peer_blocks = []
        for device in devices:
            block = (
                f'[Peer]\n'
                f'PublicKey = {device.public_key}\n'
                f'AllowedIPs = {device.ip_address}/32\n'
                f'PersistentKeepalive = 25\n'
            )
            peer_blocks.append(block)
        return peer_blocks

    def _build_full_config(self) -> str:
        from wireguard.commands import build_interface_section
        interface_section = build_interface_section(self.server)
        peer_blocks       = self._get_active_peers()
        return f'{interface_section}\n' + '\n'.join(peer_blocks)

    def _safe_restart(self) -> None:
        from wireguard.commands import (
            wg_down, wg_up, write_config,
            verify_interface_section, wg_is_running,
        )

        config = self._build_full_config()

        if not verify_interface_section(config, self.server):
            raise RuntimeError(
                'Interface section verification failed. '
                'Check server config in the database.'
            )

        logger.info('Config verified — proceeding with restart')

        if wg_is_running(self.server, self.interface):
            wg_down(self.server, self.interface)
            time.sleep(1)

        try:
            write_config(self.server, self.interface, config)
        except Exception as e:
            logger.error('Failed to write config: %s — bringing up anyway', e)

        time.sleep(1)
        wg_up(self.server, self.interface)
        logger.info('Server back up cleanly')

    def add_device(self, device) -> None:
        logger.info('Adding device %s', device.name)
        self._safe_restart()
        logger.info('Device %s added', device.name)

    def remove_device(self, device) -> None:
        logger.info('Removing device %s', device.name)
        self._safe_restart()
        logger.info('Device %s removed', device.name)

    def sync_all(self) -> None:
        logger.info('Syncing all peers to server')
        self._safe_restart()
        logger.info('Sync complete')

    def refresh_stats(self) -> int:
        from wireguard.commands import wg_show_dump, parse_wg_dump
        from apps.devices.models import Device
        from datetime import datetime
        from django.utils import timezone

        dump       = wg_show_dump(self.server, self.interface)
        peer_stats = parse_wg_dump(dump)
        updated    = 0

        for device in Device.objects.filter(
            server=self.server,
            status=Device.Status.ACTIVE
        ):
            stats = peer_stats.get(device.public_key)
            if not stats:
                continue
            if stats['last_handshake']:
                device.last_handshake = datetime.fromtimestamp(
                    stats['last_handshake'], tz=timezone.utc
                )
            device.bytes_received = stats['bytes_received']
            device.bytes_sent     = stats['bytes_sent']
            device.save(update_fields=[
                'last_handshake', 'bytes_received',
                'bytes_sent', 'updated_at'
            ])
            updated += 1

        logger.info('Stats refreshed for %d devices', updated)
        return updated

    def is_running(self) -> bool:
        from wireguard.commands import wg_is_running
        return wg_is_running(self.server, self.interface)