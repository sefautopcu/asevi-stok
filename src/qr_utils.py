"""QR image serialization helpers shared by stock-label screens."""
from io import BytesIO


def qr_png_bytesi_olustur(qrcode_modulu, deger):
    """Generate a standard QR-code PNG using the app's established settings."""
    qr = qrcode_modulu.QRCode(version=1, box_size=10, border=4)
    qr.add_data(deger)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    return image_buffer.getvalue()
