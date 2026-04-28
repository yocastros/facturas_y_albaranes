import os
import uuid
import logging
from datetime import datetime
from pathlib import Path

# ── Variables de entorno para Windows (Tesseract + Poppler) ──────────────
_tesseract_data = r"C:\Program Files\Tesseract-OCR\tessdata"
if os.path.exists(_tesseract_data):
    os.environ.setdefault('TESSDATA_PREFIX', _tesseract_data)

_tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
try:
    import pytesseract
    if os.path.exists(_tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd
except ImportError:
    pass
# ─────────────────────────────────────────────────────────────────────────

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from models import db, Documento
from ocr_processor import procesar_documento
from report_generator import generar_reporte_excel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuración
BASE_DIR = Path(__file__).parent.parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
REPORTS_FOLDER = BASE_DIR / 'reports'
DB_PATH = BASE_DIR / 'sistema_facturas.db'

UPLOAD_FOLDER.mkdir(exist_ok=True)
REPORTS_FOLDER.mkdir(exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB

EXTENSIONES_PERMITIDAS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp'}

db.init_app(app)

with app.app_context():
    db.create_all()
    logger.info("Base de datos inicializada")


def extension_permitida(filename):
    return Path(filename).suffix.lower() in EXTENSIONES_PERMITIDAS


# ═══════════════════════════════════════════════════════════
# ENDPOINTS DE DOCUMENTOS
# ═══════════════════════════════════════════════════════════

@app.route('/api/escanear', methods=['POST'])
def escanear_documento():
    """Sube y procesa un documento con OCR."""
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se proporcionó archivo'}), 400

    archivo = request.files['archivo']
    if not archivo.filename:
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    if not extension_permitida(archivo.filename):
        return jsonify({'error': f'Formato no soportado. Use: PDF, PNG, JPG, TIFF'}), 400

    # Guardar archivo
    ext = Path(archivo.filename).suffix.lower()
    nombre_unico = f"{uuid.uuid4().hex}{ext}"
    ruta_archivo = UPLOAD_FOLDER / nombre_unico
    archivo.save(str(ruta_archivo))

    # Procesar con OCR
    try:
        resultado = procesar_documento(str(ruta_archivo))
    except Exception as e:
        logger.error(f"Error OCR: {e}")
        # Eliminar archivo si hubo error técnico
        if ruta_archivo.exists():
            ruta_archivo.unlink()
        return jsonify({'error': f'Error procesando documento: {str(e)}'}), 500

    if resultado.get('estado') == 'ERROR':
        # Eliminar archivo si no es una factura/albarán válido
        if ruta_archivo.exists():
            ruta_archivo.unlink()
            logger.info(f"Archivo eliminado por validación fallida: {nombre_unico}")
        return jsonify({'error': resultado.get('error', 'Error desconocido')}), 422

    # Crear registro en BD
    doc = Documento(
        tipo=resultado['tipo'],
        numero=resultado.get('numero'),
        fecha=resultado.get('fecha'),
        proveedor=resultado.get('proveedor'),
        cif=resultado.get('cif'),
        base_imponible=resultado.get('base_imponible', 0),
        iva=resultado.get('iva', 0),
        total=resultado.get('total', 0),
        porcentaje_iva=resultado.get('porcentaje_iva', 21.0),
        estado='PROCESADO',
        archivo_original=nombre_unico,  # nombre uuid para recuperar el archivo
        texto_ocr=resultado.get('texto_ocr', ''),
    )
    db.session.add(doc)
    db.session.flush()  # Para obtener el ID

    # Neteo automático si es factura
    albaranes_referenciados = resultado.get('albaranes_referenciados', [])
    albaranes_neteados = []

    if doc.tipo == 'factura':
        albaranes_neteados = _netear_factura(doc, albaranes_referenciados)

    db.session.commit()

    response = doc.to_dict()
    response['albaranes_neteados_automaticamente'] = len(albaranes_neteados)
    return jsonify(response), 201


def _netear_factura(factura, numeros_albaran_ref):
    """Intenta asociar albaranes a una factura automáticamente."""
    asociados = []

    # Buscar por número de albarán mencionado en la factura
    for num_alb in numeros_albaran_ref:
        alb = Documento.query.filter(
            Documento.tipo == 'albaran',
            Documento.numero.ilike(f'%{num_alb}%'),
            Documento.factura_id.is_(None)
        ).first()
        if alb:
            alb.factura_id = factura.id
            alb.estado = 'FACTURA_ASOCIADA'
            asociados.append(alb)

    # Si no encontró por número, buscar por proveedor y fecha próxima
    if not asociados and factura.proveedor:
        albaranes_candidatos = Documento.query.filter(
            Documento.tipo == 'albaran',
            Documento.factura_id.is_(None),
            Documento.proveedor.ilike(f'%{factura.proveedor[:10]}%')
        ).all()

        for alb in albaranes_candidatos:
            if _fechas_proximas(factura.fecha, alb.fecha, dias=30):
                alb.factura_id = factura.id
                alb.estado = 'FACTURA_ASOCIADA'
                asociados.append(alb)

    if asociados:
        factura.estado = 'FACTURA_ASOCIADA'

    return asociados


def _fechas_proximas(fecha1_str, fecha2_str, dias=30):
    """Comprueba si dos fechas están dentro de N días de diferencia."""
    if not fecha1_str or not fecha2_str:
        return False
    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']
    f1 = f2 = None
    for fmt in formatos:
        try:
            f1 = datetime.strptime(fecha1_str, fmt)
            break
        except ValueError:
            continue
    for fmt in formatos:
        try:
            f2 = datetime.strptime(fecha2_str, fmt)
            break
        except ValueError:
            continue
    if f1 and f2:
        return abs((f1 - f2).days) <= dias
    return False



@app.route('/api/documentos/<int:doc_id>/archivo', methods=['GET'])
def ver_archivo(doc_id):
    """Sirve el archivo original para visualizarlo en el navegador."""
    doc = Documento.query.get_or_404(doc_id)
    if not doc.archivo_original:
        return jsonify({'error': 'Sin archivo asociado'}), 404
    ruta = UPLOAD_FOLDER / doc.archivo_original
    if not ruta.exists():
        return jsonify({'error': 'Archivo no encontrado en disco'}), 404
    ext = ruta.suffix.lower()
    mimes = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.bmp': 'image/bmp',
    }
    mime = mimes.get(ext, 'application/octet-stream')
    return send_file(str(ruta), mimetype=mime)


@app.route('/api/documentos', methods=['GET'])
def listar_documentos():
    """Lista todos los documentos con filtros opcionales."""
    tipo = request.args.get('tipo')
    estado = request.args.get('estado')
    busqueda = request.args.get('q')
    pagina = int(request.args.get('pagina', 1))
    por_pagina = int(request.args.get('por_pagina', 50))

    query = Documento.query

    if tipo:
        query = query.filter(Documento.tipo == tipo)
    if estado:
        query = query.filter(Documento.estado == estado)
    if busqueda:
        busq = f'%{busqueda}%'
        query = query.filter(
            db.or_(
                Documento.numero.ilike(busq),
                Documento.proveedor.ilike(busq),
                Documento.cif.ilike(busq),
            )
        )

    total = query.count()
    docs = query.order_by(Documento.fecha_subida.desc()) \
                .offset((pagina - 1) * por_pagina) \
                .limit(por_pagina).all()

    return jsonify({
        'documentos': [d.to_dict() for d in docs],
        'total': total,
        'pagina': pagina,
        'por_pagina': por_pagina,
        'paginas': (total + por_pagina - 1) // por_pagina,
    })


@app.route('/api/documentos/<int:doc_id>', methods=['GET'])
def obtener_documento(doc_id):
    doc = Documento.query.get_or_404(doc_id)
    return jsonify(doc.to_dict())


@app.route('/api/documentos/<int:doc_id>', methods=['PUT'])
def actualizar_documento(doc_id):
    doc = Documento.query.get_or_404(doc_id)
    datos = request.get_json()

    campos = ['tipo', 'numero', 'fecha', 'proveedor', 'cif',
              'base_imponible', 'iva', 'total', 'notas']
    for campo in campos:
        if campo in datos:
            setattr(doc, campo, datos[campo])

    db.session.commit()
    return jsonify(doc.to_dict())


@app.route('/api/documentos/<int:doc_id>', methods=['DELETE'])
def eliminar_documento(doc_id):
    doc = Documento.query.get_or_404(doc_id)
    # Desasociar albaranes hijos
    for alb in doc.albaranes_asociados.all():
        alb.factura_id = None
        alb.estado = 'PROCESADO'
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'mensaje': 'Documento eliminado correctamente'})


# ═══════════════════════════════════════════════════════════
# ENDPOINTS DE NETEO
# ═══════════════════════════════════════════════════════════

@app.route('/api/neteo/asociar', methods=['POST'])
def asociar_manualmente():
    """Asocia manualmente una factura con uno o varios albaranes."""
    datos = request.get_json()
    factura_id = datos.get('factura_id')
    albaran_ids = datos.get('albaran_ids', [])

    if not factura_id:
        return jsonify({'error': 'factura_id requerido'}), 400

    factura = Documento.query.filter_by(id=factura_id, tipo='factura').first()
    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    asociados = []
    for alb_id in albaran_ids:
        alb = Documento.query.filter_by(id=alb_id, tipo='albaran').first()
        if alb:
            alb.factura_id = factura_id
            alb.estado = 'FACTURA_ASOCIADA'
            asociados.append(alb.to_dict_simple())

    if asociados:
        factura.estado = 'FACTURA_ASOCIADA'

    db.session.commit()
    return jsonify({
        'mensaje': f'{len(asociados)} albarán(es) asociado(s)',
        'factura': factura.to_dict(),
        'asociados': asociados,
    })


@app.route('/api/neteo/desasociar/<int:albaran_id>', methods=['POST'])
def desasociar_albaran(albaran_id):
    """Desasocia un albarán de su factura."""
    alb = Documento.query.filter_by(id=albaran_id, tipo='albaran').first()
    if not alb:
        return jsonify({'error': 'Albarán no encontrado'}), 404

    factura_id_anterior = alb.factura_id
    alb.factura_id = None
    alb.estado = 'PROCESADO'

    # Revisar si la factura padre sigue teniendo albaranes
    if factura_id_anterior:
        factura = Documento.query.get(factura_id_anterior)
        if factura and factura.albaranes_asociados.count() == 0:
            factura.estado = 'PROCESADO'

    db.session.commit()
    return jsonify({'mensaje': 'Albarán desasociado correctamente', 'albaran': alb.to_dict()})


@app.route('/api/neteo/sin-asociar', methods=['GET'])
def documentos_sin_asociar():
    """Lista facturas sin albaranes y albaranes sin factura."""
    facturas_sin = Documento.query.filter_by(tipo='factura', estado='PROCESADO').all()
    albaranes_sin = Documento.query.filter_by(tipo='albaran', factura_id=None).all()

    return jsonify({
        'facturas_sin_albaran': [f.to_dict_simple() for f in facturas_sin],
        'albaranes_sin_factura': [a.to_dict_simple() for a in albaranes_sin],
    })


# ═══════════════════════════════════════════════════════════
# ESTADÍSTICAS Y REPORTES
# ═══════════════════════════════════════════════════════════

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Estadísticas generales del sistema."""
    total = Documento.query.count()
    facturas = Documento.query.filter_by(tipo='factura').count()
    albaranes = Documento.query.filter_by(tipo='albaran').count()
    procesados = Documento.query.filter_by(estado='PROCESADO').count()
    pendientes = Documento.query.filter_by(estado='PENDIENTE').count()
    errores = Documento.query.filter_by(estado='ERROR').count()
    neteados = Documento.query.filter_by(estado='FACTURA_ASOCIADA').count()

    # Importes
    from sqlalchemy import func
    total_facturas_importe = db.session.query(
        func.sum(Documento.total)
    ).filter_by(tipo='factura').scalar() or 0

    total_albaranes_importe = db.session.query(
        func.sum(Documento.total)
    ).filter_by(tipo='albaran').scalar() or 0

    return jsonify({
        'total_documentos': total,
        'facturas': facturas,
        'albaranes': albaranes,
        'procesados': procesados,
        'pendientes': pendientes,
        'errores': errores,
        'neteados': neteados,
        'importe_facturas': round(total_facturas_importe, 2),
        'importe_albaranes': round(total_albaranes_importe, 2),
        'importe_total': round(total_facturas_importe + total_albaranes_importe, 2),
    })


@app.route('/api/reportes/generar', methods=['POST'])
def generar_reporte():
    """Genera y devuelve un reporte Excel."""
    datos = request.get_json() or {}
    fecha_desde = datos.get('fecha_desde')
    fecha_hasta = datos.get('fecha_hasta')

    # Obtener documentos
    docs = Documento.query.order_by(Documento.fecha_subida.desc()).all()
    docs_dict = [d.to_dict() for d in docs]

    # Generar reporte
    nombre = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ruta_salida = str(REPORTS_FOLDER / nombre)

    ruta, error = generar_reporte_excel(docs_dict, ruta_salida, fecha_desde, fecha_hasta)

    if error:
        return jsonify({'error': error}), 500

    return send_file(
        ruta,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nombre
    )


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


if __name__ == '__main__':
    print("Sistema de Facturas y Albaranes iniciado")
    print("   Backend: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
