from django.core.management.base import BaseCommand
from django.db import transaction
from wireguard.parser import WireGuardConfigParser
from wireguard.key_manager import encrypt
from wireguard.ip_allocator import IPAllocator
from apps.server.models import ServerConfig, IPAllocation
from apps.devices.models import Device


class Command(BaseCommand):
    help = 'Import existing WireGuard peers from a wg0.conf file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            default='/etc/wireguard/wg0.conf',
            help='Path to the wg0.conf file (default: /etc/wireguard/wg0.conf)'
        )
        parser.add_argument(
            '--server-public-ip',
            help='Your GCP server external IP address'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be imported without saving anything'
        )

    def handle(self, *args, **options):
        config_path    = options['config']
        server_ip      = options.get('server_public_ip')
        dry_run        = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN — nothing will be saved\n')
            )

        # ── Step 1: Parse the config file ──────────────────────────────
        self.stdout.write(f'Reading config from {config_path}...')

        try:
            parser = WireGuardConfigParser()
            config = parser.parse_file(config_path)
        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(
                    f'File not found: {config_path}\n'
                    f'Make sure the path is correct and the file exists.'
                )
            )
            return

        iface = config.interface
        peers = config.peers

        self.stdout.write(
            f'Found interface with {len(peers)} peers.\n'
        )

        # Preview
        self.stdout.write('\n── Interface ──────────────────────────')
        self.stdout.write(f'  Address:     {iface.address}')
        self.stdout.write(f'  Listen Port: {iface.listen_port}')
        self.stdout.write(f'  DNS:         {iface.dns}')

        self.stdout.write('\n── Peers found ────────────────────────')
        for i, peer in enumerate(peers, 1):
            self.stdout.write(
                f'  {i:>3}. IP: {peer.ip_address:<16} '
                f'Key: {peer.public_key[:20]}...'
            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nDry run complete. '
                    f'{len(peers)} peers would be imported.'
                )
            )
            return

        # ── Step 2: Get or create ServerConfig ─────────────────────────
        server = ServerConfig.objects.first()
        if not server:
            self.stderr.write(
                self.style.ERROR(
                    'No server configured in the database.\n'
                    'Go to /server/setup/ first and save your server details.'
                )
            )
            return

        # Update public IP if provided
        if server_ip:
            server.public_ip = server_ip
            server.save(update_fields=['public_ip'])
            self.stdout.write(f'\nUpdated server public IP to {server_ip}')

        # Encrypt and store the server private key if not set
        if iface.private_key and not server.private_key:
            server.private_key = encrypt(iface.private_key)
            server.save(update_fields=['private_key'])
            self.stdout.write('Stored encrypted server private key.')

        # ── Step 3: Populate IP pool ────────────────────────────────────
        self.stdout.write('\nPopulating IP pool...')
        allocator = IPAllocator(server)
        created   = allocator.populate_pool()
        self.stdout.write(f'  {created} IP addresses added to pool.')

        # ── Step 4: Import each peer ────────────────────────────────────
        self.stdout.write('\nImporting peers...')
        imported = 0
        skipped  = 0

        with transaction.atomic():
            for peer in peers:

                # Skip peers with no public key
                if not peer.public_key:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Skipping peer with no public key'
                        )
                    )
                    skipped += 1
                    continue

                # Skip if already in the database
                if Device.objects.filter(public_key=peer.public_key).exists():
                    self.stdout.write(
                        f'  Skipping {peer.ip_address} — already exists'
                    )
                    skipped += 1
                    continue

                # Get or create the IP allocation for this peer
                if peer.ip_address:
                    allocation, _ = IPAllocation.objects.get_or_create(
                        server=server,
                        ip_address=peer.ip_address,
                        defaults={'status': IPAllocation.Status.ASSIGNED}
                    )
                    # Mark it as assigned
                    allocation.status = IPAllocation.Status.ASSIGNED
                    allocation.save(update_fields=['status'])
                else:
                    # No IP in config — allocate one from the pool
                    try:
                        allocation = allocator.allocate()
                    except ValueError:
                        self.stderr.write(
                            self.style.ERROR('IP pool exhausted.')
                        )
                        break

                # Encrypt preshared key if present
                psk_encrypted = ''
                if peer.preshared_key:
                    psk_encrypted = encrypt(peer.preshared_key)

                # Create the device
                device = Device.objects.create(
                    name=f'Imported Device ({peer.ip_address})',
                    device_type=Device.DeviceType.OTHER,
                    public_key=peer.public_key,
                    private_key_encrypted='',
                    preshared_key_encrypted=psk_encrypted,
                    allocated_ip=allocation,
                    status=Device.Status.ACTIVE,
                    imported=True,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Imported {device.name} '
                        f'({peer.ip_address})'
                    )
                )
                imported += 1

        # ── Summary ─────────────────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f'\nImport complete: '
                f'{imported} imported, '
                f'{skipped} skipped.'
            )
        )