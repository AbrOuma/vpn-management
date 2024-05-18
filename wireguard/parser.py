from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedInterface:
    """Holds the [Interface] section of a wg0.conf file."""
    private_key: str = ''
    address:     str = ''
    listen_port: int = 51820
    dns:         str = ''
    mtu:         int = 1420


@dataclass
class ParsedPeer:
    """Holds one [Peer] section of a wg0.conf file."""
    public_key:    str = ''
    preshared_key: str = ''
    allowed_ips:   str = ''
    endpoint:      str = ''
    keepalive:     int = 0
    ip_address:    str = ''  # Extracted from allowed_ips after parsing


@dataclass
class ParsedConfig:
    """The full parsed wg0.conf — one interface and many peers."""
    interface: ParsedInterface = field(default_factory=ParsedInterface)
    peers:     list            = field(default_factory=list)


class WireGuardConfigParser:
    """
    Reads a wg0.conf file and returns a ParsedConfig object.

    WireGuard config format looks like this:

        [Interface]
        PrivateKey = *****...
        Address = 10.0.0.1/24
        ListenPort = 51820

        [Peer]
        PublicKey = xyz789...
        AllowedIPs = 10.0.0.2/32
        PersistentKeepalive = 25
    """

    def parse_file(self, path: str) -> ParsedConfig:
        """Read a file from disk and parse it."""
        content = Path(path).read_text()
        return self.parse_string(content)

    def parse_string(self, content: str) -> ParsedConfig:
        """Parse a wg0.conf string directly."""
        config          = ParsedConfig()
        current_section = None
        current_peer    = None

        for raw_line in content.splitlines():
            line = raw_line.strip()

            # Skip blank lines and comments
            if not line or line.startswith('#'):
                continue

            # Section headers
            if line == '[Interface]':
                current_section = 'interface'
                current_peer    = None
                continue

            if line == '[Peer]':
                # Save the previous peer before starting a new one
                if current_peer:
                    config.peers.append(current_peer)
                current_section = 'peer'
                current_peer    = ParsedPeer()
                continue

            # All other lines are key = value pairs
            if '=' not in line:
                continue

            key, _, value = line.partition('=')
            key   = key.strip()
            value = value.strip()

            if current_section == 'interface':
                self._parse_interface_line(config.interface, key, value)

            elif current_section == 'peer' and current_peer:
                self._parse_peer_line(current_peer, key, value)

        # Save the last peer
        if current_peer:
            config.peers.append(current_peer)

        # Extract clean IP from AllowedIPs for each peer
        # e.g. "10.0.0.5/32" becomes "10.0.0.5"
        for peer in config.peers:
            peer.ip_address = self._extract_ip(peer.allowed_ips)

        return config

    def _parse_interface_line(self, iface: ParsedInterface, key: str, value: str):
        if key == 'PrivateKey':  iface.private_key = value
        elif key == 'Address':   iface.address     = value
        elif key == 'ListenPort':iface.listen_port  = int(value)
        elif key == 'DNS':       iface.dns          = value
        elif key == 'MTU':       iface.mtu          = int(value)

    def _parse_peer_line(self, peer: ParsedPeer, key: str, value: str):
        if key == 'PublicKey':            peer.public_key    = value
        elif key == 'PresharedKey':       peer.preshared_key = value
        elif key == 'AllowedIPs':         peer.allowed_ips   = value
        elif key == 'Endpoint':           peer.endpoint      = value
        elif key == 'PersistentKeepalive':peer.keepalive     = int(value)

    def _extract_ip(self, allowed_ips: str) -> str:
        """
        Turn '10.0.0.5/32' into '10.0.0.5'.
        Takes only the first IP if there are multiple.
        """
        if not allowed_ips:
            return ''
        first = allowed_ips.split(',')[0].strip()
        return first.split('/')[0]