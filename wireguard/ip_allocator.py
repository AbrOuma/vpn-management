import logging
from django.db import transaction

logger = logging.getLogger('wireguard')


class IPAllocator:
    """
    Finds and assigns free IP addresses from the VPN subnet pool.
    Uses database-level locking to prevent two devices from ever
    getting the same IP at the same time.
    """

    def __init__(self, server_config):
        self.server = server_config

    def allocate(self):
        """
        Find the next free IP and mark it as assigned.
        Returns the IPAllocation instance.
        Raises ValueError if no IPs are available.
        """
        from apps.server.models import IPAllocation

        with transaction.atomic():
            # select_for_update locks the row until the transaction ends
            # This prevents two requests from grabbing the same IP
            allocation = (
                IPAllocation.objects
                .select_for_update()
                .filter(
                    server=self.server,
                    status=IPAllocation.Status.FREE
                )
                .order_by('ip_address')
                .first()
            )

            if not allocation:
                raise ValueError(
                    'No free IP addresses available in the pool.'
                )

            allocation.status = IPAllocation.Status.ASSIGNED
            allocation.save(update_fields=['status', 'updated_at'])

            logger.info('Allocated IP %s', allocation.ip_address)
            return allocation

    def release(self, allocation):
        """
        Return an IP back to the free pool.
        Call this when a device is deleted or revoked.
        """
        allocation.status = allocation.Status.FREE
        allocation.save(update_fields=['status', 'updated_at'])
        logger.info('Released IP %s back to pool', allocation.ip_address)

    def populate_pool(self):
        """
        Fill the IP pool from the server subnet.
        Run this once during setup.
        Skips IPs that are already in the database.
        """
        from apps.server.models import IPAllocation

        network = self.server.network
        server_ip = self.server.server_ip
        created = 0

        for ip in network.hosts():
            ip_str = str(ip)

            # Skip the server's own VPN IP
            if ip_str == server_ip:
                continue

            _, was_created = IPAllocation.objects.get_or_create(
                server=self.server,
                ip_address=ip_str,
                defaults={'status': IPAllocation.Status.FREE}
            )

            if was_created:
                created += 1

        logger.info('IP pool populated with %d new addresses', created)
        return created

    def release(self, allocation):
            """
            Return an IP back to the free pool.
            Call this when a device is deleted.
            """
            from apps.server.models import IPAllocation
            allocation.status = IPAllocation.Status.FREE
            allocation.save(update_fields=['status', 'updated_at'])
            logger.info('Released IP %s back to pool', allocation.ip_address)