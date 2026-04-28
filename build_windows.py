#!/usr/bin/env python3
"""
Empaquetador Windows - Facturas y Albaranes v1.0
Genera instalador .exe autocontenido.
Uso: python build_windows.py
"""
import os, sys, shutil, subprocess, zipfile, base64
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
DIST_DIR   = BASE_DIR / 'dist'
TEMP_DIR   = Path('C:/temp_facturas_build')

# ── 1. Limpiar ────────────────────────────────────────────
def limpiar():
    print("[1/5] Limpiando builds anteriores...")
    for d in [DIST_DIR, BASE_DIR/'build', TEMP_DIR]:
        if d.exists(): shutil.rmtree(d, ignore_errors=True)
    for f in BASE_DIR.glob('*.spec'): f.unlink()
    print("      OK")

# ── 2. Crear zip del programa ─────────────────────────────
def crear_zip():
    print("[2/5] Creando zip del programa...")
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TEMP_DIR / 'programa.zip'
    count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for carpeta in ['backend', 'frontend']:
            src = BASE_DIR / carpeta
            if src.exists():
                for item in src.rglob('*'):
                    if item.is_file() and '__pycache__' not in str(item) and '.pyc' not in str(item):
                        zf.write(item, item.relative_to(BASE_DIR))
                        count += 1
        for archivo in ['start.py', 'crear_acceso_directo.py']:
            src = BASE_DIR / archivo
            if src.exists():
                zf.write(src, archivo)
                count += 1
    size_kb = zip_path.stat().st_size // 1024
    print(f"      {count} archivos, {size_kb} KB")
    return zip_path

# ── 3. Crear launcher con zip embebido ────────────────────
def crear_launcher(zip_path):
    print("[3/5] Creando launcher...")
    zip_b64 = base64.b64encode(zip_path.read_bytes()).decode('ascii')
    print(f"      ZIP embebido: {len(zip_b64)} bytes base64")

    code = r"""
import os, sys, subprocess, shutil, zipfile, base64, tempfile
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading, winreg, urllib.request

INSTALL_DIR  = Path("C:/FacturasAlbaranes")
TESSDATA_DIR = Path("C:/Program Files/Tesseract-OCR")
POPPLER_DIR  = Path("C:/poppler")

PROGRAMA_ZIP_B64 = "PLACEHOLDER_B64"

def get_zip():
    data = base64.b64decode(PROGRAMA_ZIP_B64)
    tmp  = Path(tempfile.gettempdir()) / "facturas_inst.zip"
    tmp.write_bytes(data)
    return tmp

def es_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def instalar_tesseract(log):
    if (TESSDATA_DIR / "tesseract.exe").exists():
        log("Tesseract ya instalado"); return
    log("Descargando Tesseract OCR...")
    url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    tmp = Path(tempfile.gettempdir()) / "tess.exe"
    urllib.request.urlretrieve(url, tmp)
    subprocess.run([str(tmp), "/S"], check=True)
    tmp.unlink(missing_ok=True)
    spa = TESSDATA_DIR / "tessdata" / "spa.traineddata"
    if not spa.exists():
        log("Descargando idioma espanol...")
        urllib.request.urlretrieve("https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata", str(spa))
    log("Tesseract instalado")

def instalar_poppler(log):
    if (POPPLER_DIR / "Library" / "bin" / "pdftoppm.exe").exists():
        log("Poppler ya instalado"); return
    log("Descargando Poppler...")
    url = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
    tmp = Path(tempfile.gettempdir()) / "poppler.zip"
    urllib.request.urlretrieve(url, tmp)
    ext = Path(tempfile.gettempdir()) / "poppler_ext"
    with zipfile.ZipFile(tmp, "r") as z: z.extractall(ext)
    if POPPLER_DIR.exists(): shutil.rmtree(POPPLER_DIR)
    for sub in ext.iterdir():
        if sub.is_dir(): shutil.copytree(sub, POPPLER_DIR); break
    shutil.rmtree(ext, ignore_errors=True); tmp.unlink(missing_ok=True)
    log("Poppler instalado")

def instalar_programa(log):
    log("Instalando programa...")
    zip_path = get_zip()
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(zip_path), "r") as z: z.extractall(str(INSTALL_DIR))
    (INSTALL_DIR / "uploads").mkdir(exist_ok=True)
    (INSTALL_DIR / "reports").mkdir(exist_ok=True)
    zip_path.unlink(missing_ok=True)
    log("Programa instalado en C:/FacturasAlbaranes")

def configurar_entorno(log):
    log("Configurando variables de entorno...")
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "TESSDATA_PREFIX", 0, winreg.REG_SZ,
            str(TESSDATA_DIR / "tessdata"))
        winreg.CloseKey(key)
    except Exception as e: log("Aviso entorno: " + str(e))
    log("Entorno configurado")

def crear_acceso_directo(log):
    log("Creando acceso directo...")
    try:
        script  = str(INSTALL_DIR / "crear_acceso_directo.py")
        instdir = str(INSTALL_DIR)
        cmd = 'cmd /c "cd /d ' + instdir + ' && python ' + script + '"'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            log("Acceso directo creado en el escritorio")
        else:
            log("Aviso: " + r.stderr[:80])
    except Exception as e:
        log("Error acceso directo: " + str(e))

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Instalador - Facturas y Albaranes")
        self.root.resizable(False, False)
        w, h = 480, 380
        x = (self.root.winfo_screenwidth()  - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.configure(bg="#1B3A5C")
        self.root.protocol("WM_DELETE_WINDOW", self.cancelar)
        tk.Label(self.root, text="Facturas y Albaranes", bg="#1B3A5C", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(pady=(24,2))
        tk.Label(self.root, text="v1.0  -  Esenex", bg="#1B3A5C", fg="#C9A84C",
                 font=("Segoe UI", 9)).pack()
        tk.Label(self.root, text="Instalando el sistema, por favor espera...",
                 bg="#1B3A5C", fg="#aabbcc", font=("Segoe UI", 9)).pack(pady=(16,4))
        self.prog = ttk.Progressbar(self.root, length=420, mode="determinate", maximum=100)
        self.prog.pack(pady=6)
        self.estado = tk.StringVar(value="Iniciando...")
        tk.Label(self.root, textvariable=self.estado, bg="#1B3A5C", fg="#C9A84C",
                 font=("Segoe UI", 9)).pack()
        fr = tk.Frame(self.root, bg="#0F2236")
        fr.pack(fill="both", expand=True, padx=20, pady=10)
        self.log_txt = tk.Text(fr, height=8, bg="#0F2236", fg="#aabbcc",
                               font=("Consolas", 8), relief="flat", state="disabled")
        self.log_txt.pack(fill="both", expand=True, padx=4, pady=4)
        self.btn = tk.Button(self.root, text="Cancelar", command=self.cancelar,
                             bg="#2A4A6C", fg="white", font=("Segoe UI", 9),
                             relief="flat", padx=20, pady=6)
        self.btn.pack(pady=(0,16))

    def log(self, msg):
        self.log_txt.config(state="normal")
        self.log_txt.insert("end", "  " + msg + "\n")
        self.log_txt.see("end")
        self.log_txt.config(state="disabled")
        self.estado.set(msg)
        self.root.update()

    def avanzar(self, pct):
        self.prog["value"] = pct
        self.root.update()

    def cancelar(self):
        if messagebox.askyesno("Cancelar", "Cancelar la instalacion?"):
            self.root.quit(); sys.exit(0)

    def finalizar(self):
        self.btn.config(text="Cerrar y arrancar", bg="#C9A84C", fg="#1B3A5C",
                        font=("Segoe UI", 9, "bold"), command=self.cerrar_arrancar)
        self.estado.set("Instalacion completada")
        self.prog["value"] = 100

    def cerrar_arrancar(self):
        self.root.destroy()
        instdir = str(INSTALL_DIR)
        subprocess.Popen(
            'cmd /c "cd /d ' + instdir + ' && start pythonw start.py"',
            shell=True
        )

    def run(self):
        threading.Thread(target=self.proceso, daemon=True).start()
        self.root.mainloop()

    def proceso(self):
        try:
            if not es_admin():
                messagebox.showerror("Error", "Necesitas ejecutar como Administrador.")
                self.root.quit(); return
            self.avanzar(5);  instalar_tesseract(self.log)
            self.avanzar(30); instalar_poppler(self.log)
            self.avanzar(55); instalar_programa(self.log)
            self.avanzar(75); configurar_entorno(self.log)
            self.avanzar(88); crear_acceso_directo(self.log)
            self.avanzar(95); self.log("Instalacion completada!")
            self.finalizar()
        except Exception as e:
            messagebox.showerror("Error de instalacion", str(e))
            self.root.quit()

if __name__ == "__main__":
    GUI().run()
"""
    code = code.replace("PLACEHOLDER_B64", zip_b64)
    launcher = TEMP_DIR / 'launcher.py'
    launcher.write_text(code, encoding='utf-8')
    print("      OK")
    return launcher

# ── 4. Empaquetar con PyInstaller ─────────────────────────
def empaquetar(launcher):
    print("[4/5] Empaquetando con PyInstaller...")
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onedir', '--windowed',
        '--name', 'FacturasAlbaranes_Setup',
        '--hidden-import', 'tkinter',
        '--hidden-import', 'win32com.client',
        '--hidden-import', 'winreg',
        '--exclude-module', 'flask',
        '--exclude-module', 'cv2',
        '--exclude-module', 'numpy',
        '--exclude-module', 'PIL',
        '--exclude-module', 'sqlalchemy',
        '--exclude-module', 'pytesseract',
        '--exclude-module', 'openpyxl',
        '--exclude-module', 'pdf2image',
        '--clean',
        str(launcher)
    ]
    r = subprocess.run(cmd, cwd=str(TEMP_DIR))
    if r.returncode != 0:
        print("ERROR al empaquetar"); sys.exit(1)
    print("      OK")

# ── 5. Copiar resultado y limpiar ─────────────────────────
def copiar_y_limpiar():
    print("[5/5] Copiando resultado...")
    src = TEMP_DIR / 'dist' / 'FacturasAlbaranes_Setup'
    DIST_DIR.mkdir(exist_ok=True)
    dst = DIST_DIR / 'FacturasAlbaranes_Setup'
    if dst.exists(): shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst)
        exe = dst / 'FacturasAlbaranes_Setup.exe'
        size_mb = sum(f.stat().st_size for f in dst.rglob('*') if f.is_file()) / 1024 / 1024
        print(f"      Resultado: {dst}")
        print(f"      Tamanio total: {size_mb:.1f} MB")
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    for f in BASE_DIR.glob('*.spec'): f.unlink()
    if (BASE_DIR / 'build').exists(): shutil.rmtree(BASE_DIR / 'build', ignore_errors=True)
    print("      OK")
    return dst if src.exists() else None

# ── Main ──────────────────────────────────────────────────
def main():
    print()
    print("=" * 55)
    print("  Empaquetador Windows - Facturas y Albaranes v1.0")
    print("=" * 55)
    try:
        import PyInstaller
        print(f"PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: pip install pyinstaller"); sys.exit(1)

    limpiar()
    zip_path = crear_zip()
    launcher = crear_launcher(zip_path)
    empaquetar(launcher)
    resultado = copiar_y_limpiar()
    print()
    print("=" * 55)
    print("  Empaquetado completado!")
    print(f"  Carpeta: {resultado}")
    print()
    print("  Distribuye la carpeta FacturasAlbaranes_Setup/")
    print("  Ejecutar FacturasAlbaranes_Setup.exe como Admin")
    print("=" * 55)

if __name__ == '__main__':
    main()
