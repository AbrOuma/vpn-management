from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets
import uuid


def default_expiry():
    """Invite links expire after 48 hours by default."""
    return timezone.now() + timedelta(hours=48)


def generate_token():
    """
    Generate a cryptographically secure random token.
    secrets module is specifically designed for this —
    never use random module for security tokens.
    """
    return secrets.token_urlsafe(48)


class DeviceInvite(models.Model):
    """
    A signed, expiring, single-use link that delivers the
    WireGuard config to the end user.

    When an admin adds a device, this record is created and
    an email is sent to the user with a link containing the token.
    The user clicks the link, downloads their config or scans
    the QR code, and the token is marked as used.

    After that the link stops working — it cannot be replayed.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'  # Sent, waiting for user
        USED    = 'used',    'Used'     # User downloaded the config
        EXPIRED = 'expired', 'Expired'  # Past expiry date
        REVOKED = 'revoked', 'Revoked'  # Admin cancelled it

    id         = models.UUIDField(
                    primary_key=True,
                    default=uuid.uuid4,
                    editable=False
                 )
    device     = models.ForeignKey(
                    'devices.Device',
                    on_delete=models.CASCADE,
                    related_name='invites'
                 )
    token      = models.CharField(
                    max_length=128,
                    unique=True,
                    default=generate_token
                 )
    status     = models.CharField(
                    max_length=10,
                    choices=Status.choices,
                    default=Status.PENDING
                 )
    expires_at = models.DateTimeField(default=default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    # Recorded when the user redeems the invite
    used_at    = models.DateTimeField(null=True, blank=True)
    used_ip    = models.GenericIPAddressField(
                    null=True,
                    blank=True,
                    help_text='IP address that redeemed this invite'
                 )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Invite for {self.device.name} [{self.status}]'

    @property
    def is_valid(self):
        """
        An invite is only valid if it is still pending
        AND has not expired yet.
        """
        return (
            self.status == self.Status.PENDING and
            self.expires_at > timezone.now()
        )

    def mark_used(self, ip_address=None):
        """Call this when the user redeems the invite."""
        self.status = self.Status.USED
        self.used_at = timezone.now()
        self.used_ip = ip_address
        self.save(update_fields=['status', 'used_at', 'used_ip'])

    def revoke(self):
        """Call this when an admin cancels the invite."""
        self.status = self.Status.REVOKED
        self.save(update_fields=['status'])