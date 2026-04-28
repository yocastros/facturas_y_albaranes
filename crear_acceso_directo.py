#!/usr/bin/env python3
"""
Crea un acceso directo en el escritorio para arrancar el sistema
con doble clic, sin ventana CMD.
Ejecutar una sola vez: python crear_acceso_directo.py
"""
import os
import sys
from pathlib import Path


def crear_acceso_directo():
    try:
        import winreg
    except ImportError:
        print("❌ Este script solo funciona en Windows.")
        sys.exit(1)

    # Intentar con pywin32
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        escritorio = Path(shell.SpecialFolders("Desktop"))
        pythonw = Path(sys.executable).parent / 'pythonw.exe'
        start_py = Path(__file__).parent / 'start.py'
        ico_path = Path(__file__).parent / 'frontend' / 'favicon.ico'

        acceso = str(escritorio / 'Facturas y Albaranes.lnk')
        enlace = shell.CreateShortCut(acceso)
        enlace.TargetPath = str(pythonw)
        enlace.Arguments = f'"{start_py}"'
        enlace.WorkingDirectory = str(Path(__file__).parent)
        enlace.Description = 'Sistema de Gestión de Facturas y Albaranes'
        if ico_path.exists():
            enlace.IconLocation = str(ico_path)
        enlace.Save()
        print(f"✅ Acceso directo creado en: {acceso}")
        print("   Ahora puedes hacer doble clic en el escritorio para arrancar el sistema.")
        input("\nPresiona Enter para cerrar...")

    except ImportError:
        # Si no tiene pywin32, crear un .bat como alternativa
        escritorio = Path.home() / 'Desktop'
        pythonw = Path(sys.executable).parent / 'pythonw.exe'
        start_py = Path(__file__).parent / 'start.py'
        bat_path = escritorio / 'Facturas y Albaranes.bat'

        with open(bat_path, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'"{pythonw}" "{start_py}"\n')

        print(f"✅ Acceso directo (.bat) creado en: {bat_path}")
        print("   Doble clic para arrancar el sistema.")
        print("\n   Para un icono más bonito, instala pywin32:")
        print("   pip install pywin32")
        input("\nPresiona Enter para cerrar...")


if __name__ == '__main__':
    crear_acceso_directo()
