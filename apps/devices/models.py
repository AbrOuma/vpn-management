from django.db import models
from django.utils import timezone
import uuid


class Device(models.Model):
    """
    A single WireGuard peer - one device belonging to one user.
    Each device gets its own key pair and its own IP address.
    """

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Active'    # Working normally
        DISABLED = 'disabled', 'Disabled'  # Temporarily blocked
        REVOKED  = 'revoked',  'Revoked'   # Permanently blocked, keys invalid

    class DeviceType(models.TextChoices):
        LAPTOP  = 'laptop',  'Laptop'
        PHONE   = 'phone',   'Phone'
        TABLET  = 'tablet',  'Tablet'
        SERVER  = 'server',  'Server'
        OTHER   = 'other',   'Other'

    id          = models.UUIDField(
                    primary_key=True,
                    default=uuid.uuid4,
                    editable=False
                  )
    user        = models.ForeignKey(
                    'users.VPNUser',
                    on_delete=models.CASCADE,
                    related_name='devices',
                    null=True,
                    blank=True,
                    help_text='Leave blank for unassigned imported devices'
                  )
    server = models.ForeignKey(
        'server.ServerConfig',
        on_delete=models.CASCADE,
        related_name='devices',
        null=True,
        blank=True,
    )
    name        = models.CharField(
                    max_length=100,
                    help_text="e.g. John's iPhone"
                  )
    device_type = models.CharField(
                    max_length=10,
                    choices=DeviceType.choices,
                    default=DeviceType.OTHER
                  )

    # WireGuard keys
    # Public key is always stored as plain text
    # Private key is encrypted before saving — we will handle this later
    public_key              = models.TextField(unique=True)
    private_key_encrypted   = models.TextField(
                                blank=True,
                                help_text='AES encrypted private key'
                              )
    preshared_key_encrypted = models.TextField(
                                blank=True,
                                help_text='AES encrypted preshared key'
                              )

    # Each device gets one IP from the pool
    allocated_ip = models.OneToOneField(
                    'server.IPAllocation',
                    on_delete=models.PROTECT,
                    related_name='device'
                   )

    status   = models.CharField(
                max_length=10,
                choices=Status.choices,
                default=Status.ACTIVE
               )

    # These fields are updated by polling wg show on the server
    last_handshake = models.DateTimeField(null=True, blank=True)
    bytes_sent     = models.BigIntegerField(default=0)
    bytes_received = models.BigIntegerField(default=0)

    # Was this device imported from an existing wg0.conf file?
    imported   = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Device'

    def __str__(self):
        owner = self.user.full_name if self.user else 'Unassigned'
        return f'{self.name} ({owner}) — {self.ip_address}'

    @property
    def ip_address(self):
        """Shortcut to get the IP string directly."""
        return self.allocated_ip.ip_address

    @property
    def is_online(self):
        """
        A device is considered online if it had a handshake
        within the last 3 minutes.
        WireGuard handshakes happen every 2 minutes when connected.
        """
        if not self.last_handshake:
            return False
        seconds_since = (timezone.now() - self.last_handshake).total_seconds()
        return seconds_since < 180