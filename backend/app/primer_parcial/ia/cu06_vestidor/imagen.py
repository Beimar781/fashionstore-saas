"""CU-06 · Validación de la imagen de la prenda: un PNG que ya viene recortado (fondo transparente). No se recorta el fondo automáticamente."""
import io

from PIL import Image, UnidentifiedImageError

from app.core.errors import DatosInvalidos

MSG_PNG = "El archivo debe ser una imagen PNG con fondo transparente."
ANCHO_MAXIMO = 800  # el PNG se reduce a este ancho: pesa menos y se dibuja más rápido en el celular
PIXELES_MAXIMOS = 16_000_000
TRANSPARENCIA_MINIMA = 0.02  # al menos el 2 % de la imagen debe ser transparente: un PNG con fondo sólido no sirve


def preparar_png(contenido: bytes) -> tuple[bytes, int, int]:
    """Devuelve el PNG listo para guardar (RGBA, de hasta 800 px de ancho) y sus medidas, o rechaza el archivo."""
    if contenido[:8] != b"\x89PNG\r\n\x1a\n":  # se confía en la firma del archivo, no en el nombre ni en el Content-Type
        raise DatosInvalidos(MSG_PNG)
    try:
        imagen = Image.open(io.BytesIO(contenido))
        if imagen.format != "PNG" or imagen.width * imagen.height > PIXELES_MAXIMOS:
            raise DatosInvalidos(MSG_PNG)
        imagen = imagen.convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as e:
        raise DatosInvalidos(MSG_PNG) from e
    alfa = imagen.getchannel("A")
    transparentes = sum(1 for valor in alfa.getdata() if valor < 255)
    if transparentes < imagen.width * imagen.height * TRANSPARENCIA_MINIMA:
        raise DatosInvalidos(MSG_PNG)
    if imagen.width > ANCHO_MAXIMO:
        imagen = imagen.resize((ANCHO_MAXIMO, max(1, round(imagen.height * ANCHO_MAXIMO / imagen.width))), Image.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue(), imagen.width, imagen.height
