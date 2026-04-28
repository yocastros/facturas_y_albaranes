# Sistema de Gestión de Facturas y Albaranes

Sistema web completo para gestión, OCR y neteo de facturas y albaranes.

---

## 🚀 Instalación Rápida

### 1. Instalar Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
- Descarga el instalador: https://github.com/UB-Mannheim/tesseract/wiki
- Instala con el paquete de idioma español
- Añade Tesseract al PATH del sistema

### 2. Instalar dependencias Python

```bash
cd sistema_facturas/backend
pip install -r requirements.txt
```

> **Nota:** Si estás en Linux y pip da error de entorno:
> ```bash
> pip install -r requirements.txt --break-system-packages
> ```

### 3. Iniciar el sistema

**Opción A — Script automático:**
```bash
cd sistema_facturas
python start.py
```

**Opción B — Manual (dos terminales):**
```bash
# Terminal 1 — Backend
cd sistema_facturas/backend
python app.py

# Terminal 2 — Frontend
# Abre el archivo directamente en el navegador:
# sistema_facturas/frontend/index.html
```

---

## 📌 Uso del Sistema

### Interfaz Web
Abre `frontend/index.html` en cualquier navegador moderno.
El backend debe estar corriendo en `http://localhost:5000`.

### Flujo de trabajo
1. **Escanear** → Sube facturas y/o albaranes (PDF, PNG, JPG, TIFF)
2. El OCR extrae automáticamente: número, fecha, proveedor, CIF, importes
3. El sistema intenta **netear automáticamente** factura ↔ albarán si:
   - El número de albarán está mencionado en la factura (prioritario)
   - Mismo proveedor + fecha dentro de ±30 días
4. **Documentos** → Revisa y edita los datos extraídos
5. **Neteo** → Asocia manualmente los que no se netearon solos
6. **Reportes** → Genera Excel con portada, listado, resumen y tabla de neteo

---

## 🔌 API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/escanear` | Subir y procesar documento con OCR |
| GET | `/api/documentos` | Listar documentos (con filtros) |
| GET | `/api/documentos/:id` | Obtener detalle |
| PUT | `/api/documentos/:id` | Actualizar documento |
| DELETE | `/api/documentos/:id` | Eliminar documento |
| POST | `/api/neteo/asociar` | Asociar albaranes a factura |
| POST | `/api/neteo/desasociar/:id` | Desasociar albarán |
| GET | `/api/neteo/sin-asociar` | Documentos sin netear |
| GET | `/api/estadisticas` | KPIs del sistema |
| POST | `/api/reportes/generar` | Generar Excel |

---

## 🏗️ Estructura del Proyecto

```
sistema_facturas/
├── backend/
│   ├── app.py              # API REST Flask principal
│   ├── models.py           # Modelos SQLAlchemy
│   ├── ocr_processor.py    # Motor OCR + extracción de campos
│   ├── report_generator.py # Generador Excel profesional
│   └── requirements.txt
├── frontend/
│   └── index.html          # Interfaz web completa (sin dependencias)
├── uploads/                # Archivos subidos
├── reports/                # Reportes Excel generados
├── start.py                # Script de inicio
└── README.md
```

---

## ⚙️ Tecnologías

- **Backend:** Python 3.8+, Flask, SQLAlchemy, SQLite
- **OCR:** Tesseract, OpenCV, Pillow, pdf2image
- **Reportes:** OpenPyXL
- **Frontend:** HTML5/CSS3/JS vanilla (sin dependencias externas)

---

## 📝 Modo sin Tesseract

Si Tesseract no está instalado, el sistema funciona en **modo simulación**: 
genera datos OCR de ejemplo para que puedas probar toda la interfaz, 
el neteo y los reportes Excel.

---

## 🤝 Soporte

raul.castro@esenex.es
