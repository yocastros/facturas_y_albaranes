import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Intentar importar librerías OCR opcionales
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    OCR_DISPONIBLE = True

    # Configurar rutas de Tesseract multiplataforma
    import platform
    _so = platform.system()

    # Usar variable de entorno si está definida (establecida por start.py)
    _cmd_env = os.environ.get('TESSERACT_CMD', '')
    if _cmd_env and os.path.exists(_cmd_env):
        pytesseract.pytesseract.tesseract_cmd = _cmd_env
    elif _so == 'Windows':
        _cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
        if os.path.exists(_cmd):
            pytesseract.pytesseract.tesseract_cmd = _cmd
        _data = 'C:/Program Files/Tesseract-OCR/tessdata'
        if os.path.exists(_data):
            os.environ['TESSDATA_PREFIX'] = _data
    elif _so == 'Darwin':  # macOS
        for _cmd in ['/usr/local/bin/tesseract', '/opt/homebrew/bin/tesseract']:
            if os.path.exists(_cmd):
                pytesseract.pytesseract.tesseract_cmd = _cmd
                break
    # Linux: tesseract normalmente en PATH, no necesita configuración extra

except ImportError:
    OCR_DISPONIBLE = False
    logger.warning("Tesseract/OpenCV no disponible.")

try:
    from pdf2image import convert_from_path
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False
    logger.warning("pdf2image no disponible.")


def preprocesar_imagen(ruta_imagen):
    """Preprocesa imagen para mejorar precisión OCR."""
    if not OCR_DISPONIBLE:
        return None
    img = cv2.imread(str(ruta_imagen))
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Umbral adaptativo gaussiano
    umbral = cv2.adaptiveThreshold(
        gris, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    # Reducción de ruido
    kernel = np.ones((1, 1), np.uint8)
    procesada = cv2.morphologyEx(umbral, cv2.MORPH_CLOSE, kernel)
    return procesada


def _get_poppler_path():
    """Detecta la ruta de Poppler en Windows automáticamente."""
    rutas_posibles = [
        r"C:\poppler\Library\bin",
        r"C:\poppler\bin",
        r"C:\Program Files\poppler\Library\bin",
        r"C:\Program Files (x86)\poppler\Library\bin",
    ]
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ruta
    return None  # En Linux/Mac no hace falta


def extraer_texto_pdf(ruta_pdf):
    """Convierte PDF a imágenes y extrae texto OCR."""
    if not PDF_DISPONIBLE or not OCR_DISPONIBLE:
        return None

    import tempfile
    poppler_path = _get_poppler_path()

    try:
        kwargs = {'dpi': 300}
        if poppler_path:
            kwargs['poppler_path'] = poppler_path

        paginas = convert_from_path(str(ruta_pdf), **kwargs)
        texto_total = ""

        for i, pagina in enumerate(paginas):
            # Usar carpeta temporal del sistema (funciona en Windows y Linux)
            with tempfile.NamedTemporaryFile(suffix=f'_pag{i}.png', delete=False) as tmp:
                img_path = tmp.name
            pagina.save(img_path, "PNG")

            img_proc = preprocesar_imagen(img_path)
            if img_proc is not None:
                texto = pytesseract.image_to_string(
                    img_proc,
                    lang='spa',
                    config='--psm 6'
                )
            else:
                texto = pytesseract.image_to_string(
                    Image.open(img_path),
                    lang='spa',
                    config='--psm 6'
                )
            texto_total += texto + "\n"
            if os.path.exists(img_path):
                os.remove(img_path)

        return texto_total
    except Exception as e:
        logger.error(f"Error procesando PDF: {e}")
        return None


def extraer_texto_imagen(ruta_imagen):
    """Extrae texto de imagen con preprocesamiento."""
    if not OCR_DISPONIBLE:
        return None
    try:
        img_proc = preprocesar_imagen(ruta_imagen)
        if img_proc is not None:
            texto = pytesseract.image_to_string(
                img_proc, lang='spa', config='--psm 6'
            )
        else:
            texto = pytesseract.image_to_string(
                Image.open(str(ruta_imagen)),
                lang='spa', config='--psm 6'
            )
        return texto
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        return None


# Modo simulación eliminado — el sistema solo acepta documentos reales


def detectar_tipo_documento(texto):
    """Detecta si es factura o albarán por análisis de patrones."""
    texto_lower = texto.lower()
    patrones_albaran = [
        r'\balbaran\b', r'\balbar[aá]n\b', r'\bdelivery note\b',
        r'\bnota de entrega\b', r'\bpart[eé] de entrega\b',
        r'\bnº\s*alb', r'\bnumero\s*alb'
    ]
    patrones_factura = [
        r'\bfactura\b', r'\binvoice\b', r'\bfra\b',
        r'\bnº\s*fac', r'\bnumero\s*fac', r'\bfactura\s+n[uú]mero\b'
    ]
    score_albaran = sum(1 for p in patrones_albaran if re.search(p, texto_lower))
    score_factura = sum(1 for p in patrones_factura if re.search(p, texto_lower))

    if score_albaran > score_factura:
        return 'albaran'
    elif score_factura > 0:
        return 'factura'
    else:
        return 'factura'  # Default


def extraer_numero_documento(texto):
    """Extrae número de documento del texto OCR."""
    patrones = [
        r'(?:factura|fra|albar[aá]n|albaran)[^\d]*[:\s#Nº°nNº.]*\s*([A-Z]{0,5}[-/]?\d{2,4}[-/]?\d{2,6})',
        r'(?:n[uú]mero|n[°º]|num|no\.?)[:\s]*([A-Z]{0,5}[-/]?\d{2,4}[-/]?\d{2,6})',
        r'\b([A-Z]{2,5}[-/]\d{4}[-/]\d{2,6})\b',
        r'\b([A-Z]{1,3}\d{4,10})\b',
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extraer_fecha(texto):
    """Extrae fecha del documento."""
    patrones = [
        r'(?:fecha|date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b',
        r'\b(\d{1,2}\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4})\b',
        r'\b(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b',
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extraer_proveedor(texto):
    """Extrae nombre del proveedor."""
    patrones = [
        r'(?:proveedor|empresa|raz[oó]n social|emisor)[:\s]+([^\n\r]{5,80})',
        r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s,\.]{4,60}(?:S\.?L\.?|S\.?A\.?|S\.?L\.?U\.?|S\.?A\.?U\.|S\.?C\.?|S\.?L\.?P\.?))',
        r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{4,40}(?:S\.?L\.?|S\.?A\.?|S\.?L\.?U\.?))',
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            nombre = match.group(1).strip()
            if len(nombre) > 3:
                return nombre[:100]
    return None


def extraer_cif(texto):
    """Extrae CIF/NIF del proveedor."""
    patron = r'\b([A-HJ-NP-SUVW]\d{7}[0-9A-J]|[0-9]{8}[A-Z]|\d{8}[A-Z])\b'
    patrones_contexto = [
        r'(?:CIF|NIF|C\.I\.F|N\.I\.F)[:\s.]*([A-Z]\d{7}[0-9A-J]|\d{8}[A-Z])',
        patron
    ]
    for p in patrones_contexto:
        match = re.search(p, texto, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def extraer_importe(texto, tipo='total'):
    """Extrae importes del documento."""
    patrones_total = [
        r'total\s+(?:a\s+pagar|factura|albar[aá]n)?[:\s]*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'(?:importe\s+total|total\s+iva\s+incluido)[:\s]*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'total[:\s€$]*\s*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
    ]
    patrones_base = [
        r'base\s+imponible[:\s]*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'base[:\s€]*\s*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'subtotal[:\s€]*\s*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
    ]
    patrones_iva = [
        r'(?:iva|i\.v\.a\.?)\s*(?:\d{1,2}%)?[:\s]*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'(?:impuesto)[:\s]*([0-9]{1,3}(?:[.,]\d{3})*[.,]\d{2})',
    ]

    if tipo == 'total':
        patrones = patrones_total
    elif tipo == 'base':
        patrones = patrones_base
    elif tipo == 'iva':
        patrones = patrones_iva
    else:
        patrones = patrones_total

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            importe_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(importe_str)
            except ValueError:
                continue
    return 0.0


def extraer_numeros_albaranes_referenciados(texto):
    """Extrae números de albaranes mencionados en una factura."""
    patrones = [
        r'albaran[es]*[:\s#Nº°.]*\s*([A-Z]{0,5}[-/]?\d{2,4}[-/]?\d{2,6})',
        r'albar[aá]n[es]*[:\s#Nº°.]*\s*([A-Z]{0,5}[-/]?\d{2,4}[-/]?\d{2,6})',
        r'ref(?:erencia)?[.\s]*alb[:\s]*([A-Z0-9/-]{4,20})',
        r'seg[uú]n\s+albar[aá]n[:\s]*([A-Z0-9/-]{4,20})',
    ]
    numeros = []
    for patron in patrones:
        for match in re.finditer(patron, texto, re.IGNORECASE):
            num = match.group(1).strip()
            if num and num not in numeros:
                numeros.append(num)
    return numeros


def procesar_documento(ruta_archivo):
    """Función principal: procesa un documento y retorna datos extraídos."""
    ruta = Path(ruta_archivo)
    extension = ruta.suffix.lower()

    # Extraer texto según tipo de archivo
    if extension == '.pdf':
        texto = extraer_texto_pdf(ruta)
    elif extension in ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp']:
        texto = extraer_texto_imagen(ruta)
    else:
        return {'error': f'Formato no soportado: {extension}', 'estado': 'ERROR'}

    if not texto or len(texto.strip()) < 10:
        return {'error': 'No se pudo extraer texto del documento. Comprueba que el archivo no está vacío o protegido.', 'estado': 'ERROR'}

    # Extraer campos
    tipo = detectar_tipo_documento(texto)
    numero = extraer_numero_documento(texto)
    fecha = extraer_fecha(texto)
    proveedor = extraer_proveedor(texto)
    cif = extraer_cif(texto)
    base_imponible = extraer_importe(texto, 'base')
    iva_importe = extraer_importe(texto, 'iva')
    total = extraer_importe(texto, 'total')

    # ── VALIDACIÓN ESTRICTA ────────────────────────────────────────────────
    texto_lower = texto.lower()

    # 1. El documento debe mencionar "factura" o "albarán"
    tiene_palabra_clave = any(p in texto_lower for p in [
        'factura', 'albarán', 'albaran', 'albarán', 'fra.', 'fra ',
        'invoice', 'nota de entrega', 'delivery note'
    ])

    # 2. Debe tener al menos un importe económico real
    tiene_importe = total > 0 or base_imponible > 0 or iva_importe > 0

    # 3. Debe tener CIF o número de documento
    tiene_identificador = bool(cif) or bool(numero)

    # Construir mensaje de error detallado si falla
    errores = []
    if not tiene_palabra_clave:
        errores.append('no contiene la palabra "factura" ni "albarán"')
    if not tiene_importe:
        errores.append('no se han encontrado importes económicos (base, IVA, total)')
    if not tiene_identificador:
        errores.append('no se ha encontrado número de documento ni CIF')

    # Rechazar si falla la palabra clave Y al menos otro criterio
    if not tiene_palabra_clave or (not tiene_importe and not tiene_identificador):
        return {
            'error': (
                'El documento no es una factura ni un albarán: ' +
                ', '.join(errores) + '. '
                'Por favor sube únicamente facturas o albaranes.'
            ),
            'estado': 'ERROR',
        }
    # ─────────────────────────────────────────────────────────────────────────

    # Si tenemos base y total pero no IVA → calcularlo por diferencia
    if base_imponible > 0 and total > 0 and iva_importe == 0:
        iva_importe = round(total - base_imponible, 2)

    # Si solo tenemos total → calcular base e IVA asumiendo 21%
    if total > 0 and base_imponible == 0:
        base_imponible = round(total / 1.21, 2)
        iva_importe = round(total - base_imponible, 2)

    # Si tenemos base e IVA pero no total → calcularlo
    if base_imponible > 0 and iva_importe > 0 and total == 0:
        total = round(base_imponible + iva_importe, 2)

    # Calcular % IVA
    porcentaje_iva = 21.0
    if base_imponible > 0 and iva_importe > 0:
        porcentaje_iva = round((iva_importe / base_imponible) * 100, 1)

    # Albaranes referenciados (si es factura)
    albaranes_ref = []
    if tipo == 'factura':
        albaranes_ref = extraer_numeros_albaranes_referenciados(texto)

    return {
        'tipo': tipo,
        'numero': numero,
        'fecha': fecha,
        'proveedor': proveedor,
        'cif': cif,
        'base_imponible': base_imponible,
        'iva': iva_importe,
        'total': total,
        'porcentaje_iva': porcentaje_iva,
        'texto_ocr': texto,
        'albaranes_referenciados': albaranes_ref,
        'estado': 'PROCESADO',
    }
