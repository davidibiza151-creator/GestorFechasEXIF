# utils.py
# =====================================================
# Funciones auxiliares del Gestor de Archivos Unificado
# =====================================================

import tkinter as tk
import json
import os
import hashlib
from datetime import datetime
from tkinter import messagebox

LOG_FILE = "registro_operaciones.json"


# ---------- FUNCIONES DE ARCHIVOS Y HASH ----------

def calcular_hash(ruta_archivo):
    """Calcula el hash SHA-256 de un archivo."""
    try:
        with open(ruta_archivo, "rb") as f:
            hasher = hashlib.sha256()
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


# ---------- FUNCIONES DE REGISTRO JSON ----------

def leer_json():
    """Lee el archivo JSON de registro si existe."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def guardar_json(data):
    """Guarda la lista completa de operaciones en el archivo JSON."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def registrar_operacion(operaciones):
    """
    Añade una o varias operaciones al registro JSON.
    Cada operación es un diccionario con:
    {
        "accion": "renombrado/eliminado/revertido",
        "archivo_original": "...",
        "archivo_nuevo": "...",
        "hash": "...",
        "fecha": "YYYY-MM-DD HH:MM:SS"
    }
    """
    registro = leer_json()
    if isinstance(operaciones, dict):
        operaciones = [operaciones]

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for op in operaciones:
        op["fecha"] = fecha
        registro.append(op)
    guardar_json(registro)


# ---------- FUNCIONES DE INTERFAZ ----------

def formatear_tiempo(segundos: float) -> str:
    """Convierte segundos a formato mm:ss."""
    minutos = int(segundos // 60)
    seg = int(segundos % 60)
    return f"{minutos:02d}:{seg:02d}"

def bloquear_botones(botones):
    """Desactiva temporalmente una lista de botones Tkinter."""
    if not botones:
        return

    for b in botones:
        if b is None:
            continue
        try:
            # Solo si el widget sigue existiendo en Tk
            if b.winfo_exists():
                b.config(state=tk.DISABLED)
        except tk.TclError:
            # El widget ha sido destruido o no es válido: lo ignoramos
            pass

def desbloquear_botones(botones):
    """Vuelve a activar los botones Tkinter."""
    if not botones:
        return

    for b in botones:
        if b is None:
            continue
        try:
            if b.winfo_exists():
                b.config(state=tk.NORMAL)
        except tk.TclError:
            # Si el widget ya no existe, no pasa nada
            pass
