from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Documento(db.Model):
    __tablename__ = 'documentos'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'factura' o 'albaran'
    numero = db.Column(db.String(100))
    fecha = db.Column(db.String(50))
    proveedor = db.Column(db.String(200))
    cif = db.Column(db.String(20))
    base_imponible = db.Column(db.Float, default=0.0)
    iva = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    porcentaje_iva = db.Column(db.Float, default=21.0)
    estado = db.Column(db.String(30), default='PENDIENTE')
    # Estados: PENDIENTE, PROCESADO, ERROR, FACTURA_ASOCIADA
    archivo_original = db.Column(db.String(500))
    texto_ocr = db.Column(db.Text)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    notas = db.Column(db.Text)

    # Relaciones de neteo: una factura puede tener muchos albaranes asociados
    factura_id = db.Column(db.Integer, db.ForeignKey('documentos.id'), nullable=True)
    albaranes_asociados = db.relationship(
        'Documento',
        backref=db.backref('factura_padre', remote_side=[id]),
        lazy='dynamic'
    )

    def to_dict(self):
        albaranes = []
        if self.tipo == 'factura':
            albaranes = [a.to_dict_simple() for a in self.albaranes_asociados.all()]

        return {
            'id': self.id,
            'tipo': self.tipo,
            'numero': self.numero,
            'fecha': self.fecha,
            'proveedor': self.proveedor,
            'cif': self.cif,
            'base_imponible': self.base_imponible,
            'iva': self.iva,
            'total': self.total,
            'porcentaje_iva': self.porcentaje_iva,
            'estado': self.estado,
            'archivo_original': self.archivo_original,
            'fecha_subida': self.fecha_subida.isoformat() if self.fecha_subida else None,
            'notas': self.notas,
            'factura_id': self.factura_id,
            'albaranes_asociados': albaranes,
        }

    def to_dict_simple(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'numero': self.numero,
            'fecha': self.fecha,
            'proveedor': self.proveedor,
            'total': self.total,
            'estado': self.estado,
        }
