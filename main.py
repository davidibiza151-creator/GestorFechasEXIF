# main.py
# ==========================================================
# Punto de entrada del Gestor de Archivos Unificado v1.1
# ==========================================================

import os
import sys
import tkinter as tk
from ui import GestorArchivosUI
from PIL import Image, ImageTk


def resource_path(relative_path):
    # Soporta ejecución como script y como .exe de PyInstaller
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def main():
    root = tk.Tk()

    icon_path = resource_path("icono.ico")
    icon_image = Image.open(icon_path)
    icon_photo = ImageTk.PhotoImage(icon_image)
    root.iconphoto(True, icon_photo)

    app = GestorArchivosUI(root)
    app.mainloop()


if __name__ == "__main__":
    main()
