import logging
from django.db import transaction
from wireguard.key_manager import generate_keypair, encrypt
from wireguard.ip_allocator import IPAllocator
from apps.server.models import ServerConfig
from apps.invites.models import DeviceInvite
from .models import Device

logger = logging.getLogger('wireguard')


def create_device(name: str, device_type: str,
                  server, user=None,
                  base_url: str = '') -> Device:
    """
    Create a new device on a specific server.
    Keys generated, IP allocated from that server's pool,
    WireGuard updated on that server only.
    """
    from apps.invites.models import DeviceInvite
    from wireguard.key_manager import generate_keypair, encrypt
    from wireguard.ip_allocator import IPAllocator

    # Step 1 — Generate keys
    keypair               = generate_keypair()
    private_key_encrypted = encrypt(keypair['private_key'])
    public_key            = keypair['public_key']

    # Step 2 — Allocate IP from this server's pool
    allocator  = IPAllocator(server)
    allocation = allocator.allocate()

    # Step 3 — Create device
    with transaction.atomic():
        device = Device.objects.create(
            server                  = server,
            name                    = name,
            device_type             = device_type,
            user                    = user,
            public_key              = public_key,
            private_key_encrypted   = private_key_encrypted,
            preshared_key_encrypted = '',
            allocated_ip            = allocation,
            status                  = Device.Status.ACTIVE,
        )

        invite = DeviceInvite.objects.create(device=device)

    logger.info(
        'Device "%s" created on server "%s" with IP %s',
        device.name, server.name, device.ip_address
    )

    # Step 4 — Push to this server's WireGuard
    try:
        from wireguard.manager import WireGuardManager
        WireGuardManager(server).add_device(device)
    except Exception as e:
        logger.error(
            'Device saved but failed to push to WireGuard: %s', e
        )

    # Step 5 — Send invite email
    if user:
        from apps.invites.emails import send_device_invite
        try:
            send_device_invite(invite, base_url=base_url)
        except Exception:
            pass

    return device