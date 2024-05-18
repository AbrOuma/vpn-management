import qrcode
import qrcode.image.svg
import io
import base64
from django.template.loader import render_to_string


def generate_client_config(device) -> str:
    """
    Render the WireGuard client config file for a device.
    Returns the config as a plain text string.
    """
    server = device.server

    from wireguard.key_manager import decrypt

    # Decrypt private key
    if device.private_key_encrypted:
        private_key = decrypt(device.private_key_encrypted)
    else:
        private_key = ''

    return render_to_string('wireguard/client.conf', {
        'device':      device,
        'server':      server,
        'private_key': private_key,
    })


def generate_qr_code(config_text: str) -> str:
    """
    Generate a QR code from a WireGuard config string.
    Returns a base64 encoded PNG image string safe to embed in HTML.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=4,
    )
    qr.add_data(config_text)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{encoded}'