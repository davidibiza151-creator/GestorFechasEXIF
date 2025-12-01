# historial.py
# ==========================================================
# Módulo para gestionar y visualizar el historial de acciones
# ==========================================================

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from utils import leer_json


# ==========================================================
# CARGAR Y MOSTRAR HISTORIAL
# ==========================================================

def mostrar_historial(caja_texto, filtro_var=None):
    """Carga y muestra el contenido del historial con formato."""
    caja_texto.delete(1.0, tk.END)
    registros = leer_json()

    if not registros:
        caja_texto.insert(tk.END, "No hay operaciones registradas todavía.\n")
        return

    filtro = filtro_var.get().strip().lower() if filtro_var else ""

    for op in registros:
        accion = op.get("accion", "")
        original = op.get("archivo_original", "")
        nuevo = op.get("archivo_nuevo", "")
        fecha = op.get("fecha", "")
        hashv = op.get("hash", "")

        # Filtro por texto
        texto_completo = f"{accion} {original} {nuevo} {fecha} {hashv}".lower()
        if filtro and filtro not in texto_completo:
            continue

        # Color según tipo de acción
        if accion == "renombrado":
            color = "lightgreen"
        elif accion == "revertido":
            color = "orange"
        elif accion == "eliminado":
            color = "salmon"
        else:
            color = "white"

        linea = f"[{fecha}] {accion.upper()} | {original}"
        if nuevo:
            linea += f" → {nuevo}"
        linea += f" | HASH: {hashv}\n"

        caja_texto.insert(tk.END, linea, accion)
        caja_texto.tag_config(accion, foreground=color)

    caja_texto.see(tk.END)


# ==========================================================
# EXPORTAR HISTORIAL A TXT
# ==========================================================

def exportar_historial(caja_texto):
    """Exporta el historial visible a un archivo .txt."""
    contenido = caja_texto.get(1.0, tk.END).strip()
    if not contenido:
        messagebox.showinfo("Sin contenido", "No hay nada que exportar.")
        return

    ruta = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Archivo de texto", "*.txt")],
        title="Guardar historial como..."
    )
    if not ruta:
        return

    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        messagebox.showinfo("Exportado", f"Historial guardado correctamente en:\n{ruta}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")
