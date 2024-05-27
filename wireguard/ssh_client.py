import paramiko
import logging

logger = logging.getLogger('wireguard')


def get_ssh_client(server=None) -> paramiko.SSHClient:
    if not server:
        from apps.server.models import ServerConfig
        server = ServerConfig.objects.first()
    if not server:
        raise RuntimeError('No server configured.')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Option 1 — encrypted key stored in DB
    if server.ssh_key_encrypted:
        import tempfile
        import os
        from wireguard.key_manager import decrypt

        key_content = decrypt(server.ssh_key_encrypted)

        # Write to temp file, connect, delete immediately
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='_ssh_key',
            delete=False
        ) as tmp:
            tmp.write(key_content)
            tmp_path = tmp.name

        # Set correct permissions
        os.chmod(tmp_path, 0o600)

        try:
            client.connect(
                hostname     = server.ssh_host,
                username     = server.ssh_user,
                key_filename = tmp_path,
                timeout      = 10,
            )
        finally:
            os.unlink(tmp_path)  # Delete immediately after connect

        return client

    # Option 2 — fallback to key file path
    if server.ssh_key_path:
        client.connect(
            hostname     = server.ssh_host,
            username     = server.ssh_user,
            key_filename = server.ssh_key_path,
            timeout      = 10,
        )
        return client

    raise RuntimeError(
        f'No SSH key configured for server "{server.name}". '
        'Upload a key or set a key path.'
    )


def run_command(command: str) -> tuple:
    """
    Run a command on the active server via SSH.
    Returns (stdout, stderr).
    Raises RuntimeError if the command fails.
    """
    client = get_ssh_client()

    try:
        logger.debug('Remote command: %s', command)
        stdin, stdout, stderr = client.exec_command(command)

        out       = stdout.read().decode().strip()
        err       = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            logger.error(
                'Command failed: %s\nError: %s', command, err
            )
            raise RuntimeError(
                f'Command failed (exit {exit_code}): {err}'
            )

        return out, err

    finally:
        client.close()


def write_remote_script(script_content: str, path: str) -> None:
    """
    Write a script to the remote server via SFTP.
    Avoids shell escaping issues entirely.
    """
    client = get_ssh_client()
    try:
        sftp = client.open_sftp()
        with sftp.open(path, 'w') as f:
            f.write(script_content)
    finally:
        client.close()