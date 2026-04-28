#!/usr/bin/env python3
"""
Sistema de Gestión de Facturas y Albaranes
Arranque multiplataforma: Windows, macOS, Linux
"""
import os
import sys
import subprocess
import webbrowser
import time
import threading
import platform
from pathlib import Path

BASE_DIR = Path(__file__).parent
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_INDEX = BASE_DIR / 'frontend' / 'index.html'
SO = platform.system()  # 'Windows', 'Darwin', 'Linux'

# ── Configurar Tesseract según SO ─────────────────────────────────────────────
def configurar_tesseract():
    rutas = {
        'Windows': {
            'cmd': 'C:/Program Files/Tesseract-OCR/tesseract.exe',
            'data': 'C:/Program Files/Tesseract-OCR/tessdata',
        },
        'Darwin': {
            'cmd': '/usr/local/bin/tesseract',
            'data': '/usr/local/share/tessdata',
            'alt_cmd': '/opt/homebrew/bin/tesseract',
            'alt_data': '/opt/homebrew/share/tessdata',
        },
        'Linux': {
            'cmd': '/usr/bin/tesseract',
            'data': '/usr/share/tesseract-ocr/5/tessdata',
            'alt_data': '/usr/share/tessdata',
        },
    }
    config = rutas.get(SO, rutas['Linux'])
    cmd = config.get('cmd', '')
    data = config.get('data', '')

    # macOS Homebrew puede estar en /opt/homebrew (Apple Silicon)
    if SO == 'Darwin' and not Path(cmd).exists():
        cmd = config.get('alt_cmd', cmd)
        data = config.get('alt_data', data)

    # Linux: buscar tessdata en varias rutas posibles
    if SO == 'Linux' and not Path(data).exists():
        for ruta in ['/usr/share/tesseract-ocr/4/tessdata',
                     '/usr/share/tessdata',
                     '/usr/local/share/tessdata']:
            if Path(ruta).exists():
                data = ruta
                break

    if Path(cmd).exists():
        os.environ['TESSERACT_CMD'] = cmd
    if Path(data).exists():
        os.environ['TESSDATA_PREFIX'] = data
    os.environ['PYTHONIOENCODING'] = 'utf-8'


# ── Configurar Poppler según SO ───────────────────────────────────────────────
def obtener_poppler_path():
    if SO == 'Windows':
        for ruta in ['C:/poppler/Library/bin', 'C:/poppler/bin',
                     'C:/Program Files/poppler/Library/bin']:
            if Path(ruta).exists():
                return ruta
    # En Mac y Linux poppler está en el PATH del sistema, no hace falta ruta explícita
    return None


# ── Arrancar backend ──────────────────────────────────────────────────────────
backend_process = None

def arrancar_backend():
    global backend_process
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    poppler = obtener_poppler_path()
    if poppler:
        env['POPPLER_PATH'] = poppler

    log_path = BASE_DIR / 'backend_error.log'

    if SO == 'Windows':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        python_exe = Path(sys.executable)
        pythonw = python_exe.parent / 'pythonw.exe'
        ejecutable = str(pythonw) if pythonw.exists() else str(python_exe)
    else:
        si = None
        ejecutable = sys.executable

    with open(str(log_path), 'w', encoding='utf-8') as log_file:
        backend_process = subprocess.Popen(
            [ejecutable, str(BACKEND_DIR / 'app.py')],
            stdout=log_file,
            stderr=log_file,
            startupinfo=si,
            cwd=str(BACKEND_DIR),
            env=env
        )


def esperar_backend(intentos=25):
    import urllib.request
    for _ in range(intentos):
        try:
            urllib.request.urlopen('http://localhost:5000/api/health', timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def abrir_navegador():
    if SO == 'Windows':
        webbrowser.open(f'file:///{FRONTEND_INDEX.resolve()}')
    else:
        webbrowser.open(f'file://{FRONTEND_INDEX.resolve()}')


def detener_sistema(icon=None, item=None):
    global backend_process
    if backend_process:
        backend_process.terminate()
    if icon:
        icon.stop()
    sys.exit(0)


# ── Icono en bandeja del sistema ──────────────────────────────────────────────
def crear_icono_bandeja():
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont

        # Icono: fondo azul oscuro con letras FA doradas
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size-1, size-1], radius=10,
                                fill='#1B3A5C', outline='#C9A84C', width=3)
        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            font = ImageFont.load_default()
        draw.text((10, 18), 'FA', fill='#C9A84C', font=font)

        menu = pystray.Menu(
            pystray.MenuItem('Abrir Sistema', lambda icon, item: abrir_navegador()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Detener y Salir', detener_sistema),
        )
        icon = pystray.Icon('facturas', img,
                            'Facturas y Albaranes\nIniciando...', menu)
        return icon
    except ImportError:
        return None


def arranque_con_bandeja():
    icon = crear_icono_bandeja()

    def proceso():
        configurar_tesseract()
        arrancar_backend()
        ok = esperar_backend()
        if ok:
            if icon:
                icon.title = 'Facturas y Albaranes\nSistema listo'
            abrir_navegador()
        else:
            if icon:
                icon.title = 'Facturas y Albaranes\nError al iniciar'
            mostrar_error_inicio()

    if icon:
        threading.Thread(target=proceso, daemon=True).start()
        icon.run()
    else:
        # Fallback a ventana tkinter si pystray no está disponible
        configurar_tesseract()
        arranque_con_ventana()


def mostrar_error_inicio():
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error de inicio",
            "No se pudo arrancar el servidor.\n\n"
            "Ejecuta el instalador de nuevo o revisa:\n"
            "backend_error.log")
        root.destroy()
    except Exception:
        pass


def arranque_con_ventana():
    """Fallback con ventana tkinter para sistemas sin pystray."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Facturas y Albaranes")
    root.resizable(False, False)

    w, h = 360, 200
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f'{w}x{h}+{x}+{y}')
    root.configure(bg='#1B3A5C')

    tk.Label(root, text="Sistema de Facturas y Albaranes",
             bg='#1B3A5C', fg='white',
             font=('Helvetica', 12, 'bold')).pack(pady=(20, 2))
    tk.Label(root, text="v1.0  -  Esenex",
             bg='#1B3A5C', fg='#C9A84C',
             font=('Helvetica', 8)).pack()

    estado_var = tk.StringVar(value="Arrancando...")
    tk.Label(root, textvariable=estado_var,
             bg='#1B3A5C', fg='#aabbcc',
             font=('Helvetica', 9)).pack(pady=10)

    canvas = tk.Canvas(root, width=300, height=8,
                       bg='#2A4A6C', highlightthickness=0)
    canvas.pack()
    barra = canvas.create_rectangle(0, 0, 0, 8, fill='#C9A84C', outline='')

    frame = tk.Frame(root, bg='#1B3A5C')
    frame.pack(pady=14)

    btn_abrir = tk.Button(frame, text="Abrir",
                          command=abrir_navegador,
                          bg='#C9A84C', fg='#1B3A5C',
                          font=('Helvetica', 9, 'bold'),
                          relief='flat', padx=14, pady=6,
                          state='disabled', cursor='hand2')
    btn_abrir.pack(side='left', padx=8)

    def confirmar_detener():
        if messagebox.askyesno("Detener", "Detener el sistema?"):
            detener_sistema()

    tk.Button(frame, text="Detener",
              command=confirmar_detener,
              bg='#2A4A6C', fg='white',
              font=('Helvetica', 9),
              relief='flat', padx=14, pady=6,
              cursor='hand2').pack(side='left', padx=8)

    def proceso():
        canvas.coords(barra, 0, 0, 100, 8)
        estado_var.set("Iniciando servidor...")
        arrancar_backend()
        canvas.coords(barra, 0, 0, 180, 8)
        estado_var.set("Esperando conexion...")
        ok = esperar_backend()
        canvas.coords(barra, 0, 0, 300, 8)
        if ok:
            estado_var.set("Sistema listo")
            btn_abrir.config(state='normal')
            root.attributes('-topmost', False)
            time.sleep(0.3)
            abrir_navegador()
        else:
            estado_var.set("Error al iniciar")
            messagebox.showerror("Error",
                "No se pudo arrancar.\nRevisa backend_error.log")

    threading.Thread(target=proceso, daemon=True).start()
    root.protocol("WM_DELETE_WINDOW", confirmar_detener)
    root.mainloop()


if __name__ == '__main__':
    arranque_con_bandeja()
