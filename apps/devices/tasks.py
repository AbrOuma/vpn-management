import threading
import logging

logger = logging.getLogger('wireguard')


def run_in_background(fn, *args, **kwargs):
    thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread


def remove_device_from_server(device_public_key: str,
                               device_name: str,
                               interface: str = 'wg0'):
    """
    Runs in background after device is deleted from DB.
    Uses WireGuardManager which reads active server from DB.
    Interface section always comes from DB - never corrupted.
    """
    try:
        from wireguard.manager import WireGuardManager
        logger.info('Background: removing peer %s', device_name)
        WireGuardManager().sync_all()
        logger.info('Background: done - server back up', )
    except Exception as e:
        logger.error('Background task failed for %s: %s', device_name, e)