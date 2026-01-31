"""
Helper para generación de códigos QR para tickets
"""
import logging
import io
import base64
from typing import Optional
try:
    import qrcode
    from qrcode.image.pil import PilImage
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logging.warning("qrcode no está instalado. Instalar con: pip install qrcode[pil]")

logger = logging.getLogger(__name__)


def generate_ticket_qr(ticket_code: str, size: int = 200) -> Optional[str]:
    """
    Genera un código QR para el ticket en formato base64
    
    Args:
        ticket_code: Código del ticket
        size: Tamaño del QR en píxeles
        
    Returns:
        String base64 de la imagen QR o None si hay error
    """
    if not QR_AVAILABLE:
        logger.warning("qrcode no está disponible. No se generará QR.")
        return None
    
    try:
        # Crear QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Agregar datos
        qr.add_data(ticket_code)
        qr.make(fit=True)
        
        # Crear imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Redimensionar si es necesario
        if size != 200:
            img = img.resize((size, size))
        
        # Convertir a base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        logger.error(f"Error al generar QR para ticket {ticket_code}: {e}", exc_info=True)
        return None


def generate_ticket_qr_url(ticket_code: str) -> str:
    """
    Genera URL para el QR del ticket (para usar en templates)
    
    Args:
        ticket_code: Código del ticket
        
    Returns:
        URL del QR o string vacío si no está disponible
    """
    qr_data = generate_ticket_qr(ticket_code)
    return qr_data or ''

