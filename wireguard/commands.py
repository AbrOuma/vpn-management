import logging
from .ssh_client import run_command, write_remote_script
from datetime import datetime, timezone as tz


logger = logging.getLogger('wireguard')


def wg_show(server, interface: str = 'wg0') -> str:
    out, _ = run_command(f'sudo wg show {interface}', server)
    return out


def wg_show_dump(server, interface: str = 'wg0') -> str:
    out, _ = run_command(f'sudo wg show {interface} dump', server)
    return out


def wg_is_running(server, interface: str = 'wg0') -> bool:
    try:
        wg_show(server, interface)
        return True
    except Exception:
        return False


def read_server_config(server, interface: str = 'wg0') -> str:
    out, _ = run_command(f'sudo cat /etc/wireguard/{interface}.conf', server)
    return out


def wg_down(server, interface: str = 'wg0') -> None:
    run_command(f'sudo wg-quick down {interface}', server)
    logger.info('WireGuard %s down', interface)


def wg_up(server, interface: str = 'wg0') -> None:
    run_command(f'sudo wg-quick up {interface}', server)
    logger.info('WireGuard %s up', interface)


def build_interface_section(server) -> str:
    from wireguard.key_manager import decrypt

    try:
        private_key = decrypt(server.private_key)
    except Exception:
        private_key = server.private_key

    return (
        f'[Interface]\n'
        f'Address = {server.address}\n'
        f'SaveConfig = true\n'
        f'PostUp = {server.post_up}\n'
        f'PostDown = {server.post_down}\n'
        f'ListenPort = {server.listen_port}\n'
        f'PrivateKey = {private_key}\n'
    )


def verify_interface_section(config_content: str, server) -> bool:
    required = [
        '[Interface]',
        'SaveConfig = true',
        'PostUp',
        'PostDown',
        f'ListenPort = {server.listen_port}',
        f'Address = {server.address}',
        'PrivateKey =',
    ]
    for line in required:
        if line not in config_content:
            logger.error('Interface verification failed — missing: %s', line)
            return False
    return True


def write_config(server, interface: str, content: str) -> None:
    script = f"""
content = {repr(content)}
with open('/etc/wireguard/{interface}.conf', 'w') as f:
    f.write(content)
print('Config written successfully')
"""
    write_remote_script(script, '/tmp/wg_write_config.py', server)
    run_command('sudo python3 /tmp/wg_write_config.py', server)
    run_command('sudo rm -f /tmp/wg_write_config.py', server)
    logger.info('wg0.conf written successfully')


def parse_wg_dump(dump_output: str) -> dict:
    peers = {}
    lines = dump_output.strip().splitlines()
    for line in lines[1:]:
        parts = line.split('\t')
        if len(parts) < 8:
            continue
        public_key = parts[0]
        peers[public_key] = {
            'endpoint':       parts[2],
            'allowed_ips':    parts[3],
            'last_handshake': datetime.fromtimestamp(int(parts[4]), tz=tz.utc) if parts[4] != '0' else None,
            'bytes_received': int(parts[5]),
            'bytes_sent':     int(parts[6]),
        }
    return peers


def ping_peers(server, ip_list: list) -> dict:
    if not ip_list:
        return {}

    import base64
    from wireguard.ssh_client import get_ssh_client

    lines = []
    for ip in ip_list:
        lines.append(
            f'ping -c 1 -W 1 {ip} > /dev/null 2>&1 '
            f'&& echo "{ip}:UP" || echo "{ip}:DOWN"'
        )
    script  = '\n'.join(lines)
    encoded = base64.b64encode(script.encode()).decode()
    cmd     = f'echo {encoded} | base64 -d | bash'

    client = get_ssh_client(server)
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    client.close()

    results = {}
    for line in out.splitlines():
        line = line.strip()
        if ':' in line:
            ip, status = line.rsplit(':', 1)
            results[ip.strip()] = (status.strip() == 'UP')

    return results

def wipe_all_peers(server, interface: str = 'wg0') -> int:
    """Remove every peer from the live WireGuard interface on the VM."""
    dump = wg_show_dump(server, interface)
    removed = 0
    for line in dump.strip().splitlines()[1:]:  # skip interface line
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        pubkey = parts[0].strip()
        if not pubkey:
            continue
        run_command(f'sudo wg set {interface} peer {pubkey} remove', server)
        logger.info('Removed peer %s from %s', pubkey, interface)
        removed += 1
    # Persist the change to the config file on disk
    run_command(f'sudo wg-quick save {interface}', server)
    logger.info('Wiped %d peers from %s', removed, interface)
    return removed
