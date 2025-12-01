# operaciones.py
# ==========================================================
# Módulo de operaciones del Gestor de Archivos Unificado
# ==========================================================

import json
import os
import threading
import time
import tkinter as tk
import subprocess
import shutil
import re
import sys
from datetime import datetime, timezone
from tkinter import messagebox
from difflib import SequenceMatcher

from utils import (
    calcular_hash,
    registrar_operacion,
    leer_json,
    formatear_tiempo,
    bloquear_botones,
    desbloquear_botones,
)
# Carpeta de cuarentena dentro de la ruta base
NOMBRE_CARPETA_CUARENTENA = "__Cuarentena_GestorArchivos__"

def obtener_ruta_cuarentena(ruta_base, ruta_archivo):
    """
    Devuelve la ruta dentro de la carpeta de cuarentena para un archivo dado.

    Estructura:
        <ruta_base>/__Cuarentena_GestorArchivos__/REL_PATH

    donde REL_PATH es la ruta del archivo relativa a ruta_base.
    """
    ruta_base_abs = os.path.abspath(ruta_base)
    archivo_abs = os.path.abspath(ruta_archivo)

    try:
        rel = os.path.relpath(archivo_abs, ruta_base_abs)
    except ValueError:
        # Por si no están en el mismo disco (no debería pasar si todo parte de ruta_base)
        rel = os.path.basename(archivo_abs)

    cuarentena_root = os.path.join(ruta_base_abs, NOMBRE_CARPETA_CUARENTENA)
    return os.path.join(cuarentena_root, rel)

# ==========================================================
# FUNCIÓN GENÉRICA PARA RENOMBRAR ARCHIVOS
# ==========================================================


def renombrar_archivos(
    ruta_base,
    ext_origen,
    ext_nueva,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones,
    revertir=False,):
    """Renombra o revierte archivos en un hilo separado."""

    def tarea():
        inicio = time.time()
        total = renombrados = omitidos = errores = 0
        operaciones = []

        try:
            salida.delete(1.0, tk.END)
        except tk.TclError:
            return

        if not os.path.isdir(ruta_base):
            messagebox.showerror("Error", "Ruta no válida o inexistente.")
            if botones:
                desbloquear_botones(botones)
            return

        # Si revertimos, intercambiamos extensiones
        if revertir:
            ext_origen_local, ext_nueva_local = ext_nueva, ext_origen
        else:
            ext_origen_local, ext_nueva_local = ext_origen, ext_nueva

        # Buscar archivos coincidentes
        archivos = []
        for dirpath, _, files in os.walk(ruta_base):
            for f in files:
                if f.endswith(ext_origen_local):
                    archivos.append(os.path.join(dirpath, f))

        total = len(archivos)
        if total == 0:
            messagebox.showinfo(
                "Sin archivos", f"No se encontraron archivos con {ext_origen_local}"
            )
            if botones:
                desbloquear_botones(botones)
            return

        try:
            progreso["maximum"] = total
            progreso["value"] = 0
        except tk.TclError:
            return

        for i, ruta_origen in enumerate(archivos, start=1):
            dirpath = os.path.dirname(ruta_origen)
            nuevo_nombre = (
                os.path.basename(ruta_origen)[: -len(ext_origen_local)] + ext_nueva_local
            )
            ruta_destino = os.path.join(dirpath, nuevo_nombre)
            hash_original = calcular_hash(ruta_origen)

            # Verificación de hash en modo revertir
            if revertir:
                valido = False
                registro = leer_json()
                for op in registro:
                    if (
                        op.get("archivo_nuevo") == ruta_origen
                        and op.get("hash") == hash_original
                    ):
                        valido = True
                        break
                if not valido:
                    try:
                        salida.insert(
                            tk.END,
                            f"⚠️ Saltado (hash no coincide o no fue renombrado): {ruta_origen}\n",
                        )
                    except tk.TclError:
                        return
                    omitidos += 1
                    continue

            # Evitar sobreescrituras
            if os.path.exists(ruta_destino):
                try:
                    salida.insert(tk.END, f"OMITIDO (ya existe): {ruta_destino}\n")
                except tk.TclError:
                    return
                omitidos += 1
                continue

            try:
                os.rename(ruta_origen, ruta_destino)
                salida.insert(
                    tk.END, f"✔ Renombrado: {ruta_origen} → {ruta_destino}\n"
                )
                renombrados += 1
                operaciones.append(
                    {
                        "accion": "revertido" if revertir else "renombrado",
                        "archivo_original": ruta_origen,
                        "archivo_nuevo": ruta_destino,
                        "hash": hash_original,
                    }
                )
            except Exception as e:
                try:
                    salida.insert(tk.END, f"❌ ERROR en {ruta_origen}: {e}\n")
                except tk.TclError:
                    return
                errores += 1

            try:
                progreso["value"] = i
                contador_var.set(f"{i}/{total}")
                tiempo_var.set(formatear_tiempo(time.time() - inicio))
                salida.see(tk.END)
                salida.update()
            except tk.TclError:
                return

        # Guardar registro
        if operaciones:
            registrar_operacion(operaciones)

        fin = time.time()
        try:
            salida.insert(tk.END, f"\n=== RESUMEN ===\n")
            salida.insert(
                tk.END,
                f"Archivos totales: {total}\nRenombrados: {renombrados}\n"
                f"Omitidos: {omitidos}\nErrores: {errores}\n",
            )
            salida.insert(
                tk.END, f"Duración total: {formatear_tiempo(fin - inicio)}\n"
            )
            salida.see(tk.END)
        except tk.TclError:
            pass

        if botones:
            desbloquear_botones(botones)

        messagebox.showinfo(
            "Completado", f"Proceso finalizado ({formatear_tiempo(fin - inicio)})."
        )

    if botones:
        bloquear_botones(botones)
    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()


# ==========================================================
# FUNCIÓN PARA ELIMINAR ARCHIVOS
# ==========================================================


def eliminar_archivos(
    ruta_base,
    extension,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones,
    rutas_seleccionadas=None,
    usar_cuarentena=True,):
    """
    Elimina archivos con una extensión dada, o solo las rutas indicadas.
    Si rutas_seleccionadas es una lista de rutas, SOLO elimina esas.

    Si usar_cuarentena=True, en lugar de borrar definitivamente,
    mueve los archivos a una carpeta de cuarentena dentro de ruta_base.
    """

    def tarea():
        inicio = time.time()
        total = eliminados = errores = 0
        operaciones = []

        try:
            salida.delete(1.0, tk.END)

            # --- Construir la lista de archivos a borrar ---
            if rutas_seleccionadas:
                # Solo los seleccionados en la interfaz
                archivos = [r for r in rutas_seleccionadas if os.path.exists(r)]
            else:
                # Buscar por carpeta + extensión
                if not os.path.isdir(ruta_base):
                    messagebox.showerror("Error", "Ruta no válida o inexistente.")
                    return

                archivos = []
                for dirpath, dirnames, files in os.walk(ruta_base):
                    # Evitar que entre en la propia carpeta de cuarentena
                    if NOMBRE_CARPETA_CUARENTENA in dirnames:
                        dirnames.remove(NOMBRE_CARPETA_CUARENTENA)

                    for f in files:
                        if f.endswith(extension):
                            archivos.append(os.path.join(dirpath, f))

            total = len(archivos)
            if total == 0:
                if rutas_seleccionadas:
                    messagebox.showinfo(
                        "Sin archivos", "Ninguno de los archivos seleccionados existe ya."
                    )
                else:
                    messagebox.showinfo(
                        "Sin archivos", f"No se encontraron archivos con {extension}"
                    )
                return

            progreso["maximum"] = total
            progreso["value"] = 0

            # --- Confirmación ---
            if rutas_seleccionadas:
                mensaje_conf = f"¿Enviar a cuarentena {total} archivo(s) seleccionado(s)?" if usar_cuarentena \
                               else f"¿Eliminar definitivamente {total} archivo(s) seleccionado(s)?"
            else:
                mensaje_conf = (
                    f"¿Enviar a cuarentena {total} archivos con {extension}?"
                    if usar_cuarentena
                    else f"¿Eliminar definitivamente {total} archivos con {extension}?"
                )

            confirmar = messagebox.askyesno(
                "Confirmar eliminación / cuarentena", mensaje_conf
            )
            if not confirmar:
                return

            # --- Borrado real / cuarentena ---
            for i, ruta in enumerate(archivos, start=1):
                try:
                    hash_archivo = calcular_hash(ruta)

                    if usar_cuarentena:
                        ruta_cuarentena = obtener_ruta_cuarentena(ruta_base, ruta)
                        os.makedirs(os.path.dirname(ruta_cuarentena), exist_ok=True)
                        shutil.move(ruta, ruta_cuarentena)
                        salida.insert(
                            tk.END,
                            f"🧪 A CUARENTENA: {ruta} → {ruta_cuarentena}\n",
                        )
                        accion = "cuarentena"
                    else:
                        os.remove(ruta)
                        salida.insert(tk.END, f"🗑 Eliminado: {ruta}\n")
                        accion = "eliminado"

                    eliminados += 1

                    op = {
                        "accion": accion,
                        "archivo_original": ruta,
                        "hash": hash_archivo,
                    }
                    if usar_cuarentena:
                        op["archivo_cuarentena"] = ruta_cuarentena

                    operaciones.append(op)

                except Exception as e:
                    salida.insert(
                        tk.END, f"❌ ERROR procesando {ruta}: {e}\n"
                    )
                    errores += 1

                try:
                    progreso["value"] = i
                    contador_var.set(f"{i}/{total}")
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.see(tk.END)
                    salida.update()
                except tk.TclError:
                    return

            if operaciones:
                registrar_operacion(operaciones)

            fin = time.time()
            salida.insert(tk.END, f"\n=== RESUMEN ===\n")
            salida.insert(tk.END, f"Archivos objetivo: {total}\n")
            if usar_cuarentena:
                salida.insert(
                    tk.END,
                    f"Enviados a cuarentena: {eliminados}\n"
                )
            else:
                salida.insert(tk.END, f"Eliminados: {eliminados}\n")
            salida.insert(tk.END, f"Errores: {errores}\n")
            salida.insert(
                tk.END, f"Duración total: {formatear_tiempo(fin - inicio)}\n"
            )
            salida.see(tk.END)

            if usar_cuarentena:
                messagebox.showinfo(
                    "Completado",
                    f"Se han enviado {eliminados} archivo(s) a la cuarentena\n"
                    f"en {formatear_tiempo(fin - inicio)}.",
                )
            else:
                messagebox.showinfo(
                    "Completado",
                    f"Se eliminaron {eliminados} archivo(s) en {formatear_tiempo(fin - inicio)}.",
                )
        finally:
            # Pase lo que pase, reactivamos botones
            desbloquear_botones(botones)

    bloquear_botones(botones)
    hilo = threading.Thread(target=tarea)
    hilo.start()

# ==========================================================
# PREVISUALIZAR ARCHIVOS POR EXTENSIÓN (SIN BORRAR)
# ==========================================================


def previsualizar_archivos(
    ruta_base, extension, salida, progreso, contador_var, tiempo_var, botones
):
    """Busca y muestra archivos que coinciden con la extensión, sin borrar nada."""

    def tarea():
        inicio = time.time()
        try:
            salida.delete(1.0, tk.END)
        except tk.TclError:
            return

        if not os.path.isdir(ruta_base):
            messagebox.showerror("Error", "Ruta no válida o inexistente.")
            if botones:
                desbloquear_botones(botones)
            return

        archivos = []
        for dirpath, dirnames, files in os.walk(ruta_base):
                # Evitar entrar en la carpeta de cuarentena
            if NOMBRE_CARPETA_CUARENTENA in dirnames:
                dirnames.remove(NOMBRE_CARPETA_CUARENTENA)

            for f in files:
                if f.endswith(extension):
                    archivos.append(os.path.join(dirpath, f))


        total = len(archivos)
        try:
            progreso["maximum"] = total
            progreso["value"] = 0
        except tk.TclError:
            return

        if total == 0:
            messagebox.showinfo(
                "Sin archivos", f"No se encontraron archivos con {extension}"
            )
            return

        for i, ruta in enumerate(archivos, start=1):
            try:
                salida.insert(tk.END, f"Encontrado: {ruta}\n")
                progreso["value"] = i
                contador_var.set(f"{i}/{total}")
                tiempo_var.set(formatear_tiempo(time.time() - inicio))
                salida.see(tk.END)
                salida.update()
            except tk.TclError:
                # La ventana o widgets se han destruido: salimos del hilo
                return

        try:
            salida.insert(tk.END, f"\n=== RESUMEN ===\n")
            salida.insert(
                tk.END, f"Archivos encontrados con {extension}: {total}\n"
            )
            salida.see(tk.END)
        except tk.TclError:
            pass

        messagebox.showinfo(
            "Búsqueda finalizada", f"Se encontraron {total} archivos con {extension}."
        )

        if botones:
            desbloquear_botones(botones)

    if botones:
        bloquear_botones(botones)
    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()


# ==========================================================
# APLICAR FECHAS CON EXIFTOOL (GOOGLE PHOTOS JSON)
# ==========================================================


def aplicar_exiftool_fechas(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones=None,
):
    """
    Ejecuta exiftool para actualizar fechas a partir de los JSON de Google Photos.

    - ruta_base: carpeta base (Takeout / Google Fotos)
    - salida: widget ScrolledText donde se muestra la salida
    - progreso: Progressbar
    - contador_var: StringVar "x/y" (aquí la usamos solo como texto)
    - tiempo_var: StringVar "mm:ss"
    - botones: lista de botones a deshabilitar mientras se ejecuta
    """

    import threading

    def tarea():
        inicio = time.time()

        try:
            # Limpiar salida e inicializar indicadores
            try:
                salida.delete(1.0, tk.END)
            except tk.TclError:
                return

            contador_var.set("0/0")
            tiempo_var.set("00:00")

            if not os.path.isdir(ruta_base):
                messagebox.showerror("Error", "Ruta no válida o inexistente.")
                return

            # --- Localizar exiftool ---
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            exif_local = os.path.join(base_dir, "exiftool.exe")
            if os.path.exists(exif_local):
                exif_bin = exif_local
            else:
                # Recurre al PATH del sistema
                exif_bin = "exiftool"

            if shutil.which(exif_bin) is None and not os.path.exists(exif_local):
                messagebox.showerror(
                    "Error",
                    "No se encontró 'exiftool'.\n\n"
                    "Coloca 'exiftool.exe' junto al ejecutable o añádelo al PATH."
                )
                return

            # Barra en modo indeterminado
            try:
                progreso.config(mode="indeterminate")
                progreso.start(10)
            except tk.TclError:
                pass

            # Comando exiftool
            cmd = [
                exif_bin,
                "-r",
                "-d", "%s",
                "-tagsfromfile", "%d/%F.json",
                "-FileCreateDate<PhotoTakenTimeTimestamp",
                "-FileModifyDate<PhotoTakenTimeTimestamp",
                "-ext", "*",
                "--ext", "json",
                "-overwrite_original",
                "-progress",
                ".",
            ]

            try:
                salida.insert(tk.END, "Ejecutando exiftool...\n\n")
                salida.see(tk.END)
            except tk.TclError:
                return

            proc = subprocess.Popen(
                cmd,
                cwd=ruta_base,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            # Leer salida en streaming
            for linea in proc.stdout:
                try:
                    salida.insert(tk.END, linea)
                    salida.see(tk.END)
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.update()
                except tk.TclError:
                    # Ventana cerrada
                    break

            proc.wait()
            codigo = proc.returncode

            # Restaurar barra de progreso
            try:
                progreso.stop()
                progreso.config(mode="determinate")
                progreso["value"] = 0
            except tk.TclError:
                pass

            if codigo == 0:
                try:
                    salida.insert(tk.END, "\nExifTool terminó correctamente.\n")
                    salida.see(tk.END)
                except tk.TclError:
                    pass

                messagebox.showinfo(
                    "Completado",
                    "ExifTool ha actualizado las fechas usando los JSON."
                )
            else:
                try:
                    salida.insert(
                        tk.END,
                        f"\nExifTool terminó con código {codigo}. Revisa la salida.\n"
                    )
                    salida.see(tk.END)
                except tk.TclError:
                    pass

                messagebox.showerror(
                    "Error",
                    f"ExifTool terminó con código {codigo}. Revisa el registro."
                )

        finally:
            # Pase lo que pase: reactivar botones
            desbloquear_botones(botones or [])
        
    if botones:
        bloquear_botones(botones)
    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()


# ==========================================================
# JSON SIMILARES (PARA FOTOS EDITADAS, ETC.)
# ==========================================================

def extraer_timestamp_de_nombre(ruta):
    """
    Intenta obtener un timestamp (epoch) a partir del nombre del archivo.

    Soporta:
      - números de 10 dígitos (epoch en segundos)
      - números de 13 dígitos (epoch en milisegundos)
      - formatos tipo: 20240115_134522, 20240115-134522, 20240115 134522
      - fechas tipo: 20240115 (hora ficticia 12:00:00)
    """
    base = os.path.basename(ruta)
    nombre, _ = os.path.splitext(base)

    # Rango razonable de fechas (2000-01-01 a 2035-12-31)
    epoch_min = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp())
    epoch_max = int(datetime(2035, 12, 31, tzinfo=timezone.utc).timestamp())

    # 1) Epoch de 10 o 13 dígitos
    for m in re.finditer(r"\d{10,13}", nombre):
        num_str = m.group(0)
        num = int(num_str)
        if len(num_str) == 13:
            num //= 1000  # milisegundos → segundos

        if epoch_min <= num <= epoch_max:
            return num

    # 2) Formatos tipo 20240115_134522 o 20240115-134522 o 20240115134522
    m = re.search(
        r"(20\d{2})([01]\d)([0-3]\d)[ _-]?([0-2]\d)([0-5]\d)([0-5]\d)",
        nombre
    )
    if m:
        y, mo, d, h, mi, s = map(int, m.groups())
        try:
            dt = datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)
            ts = int(dt.timestamp())
            if epoch_min <= ts <= epoch_max:
                return ts
        except ValueError:
            pass

    # 3) Solo fecha YYYYMMDD → hora ficticia 12:00:00
    m = re.search(r"(20\d{2})([01]\d)([0-3]\d)", nombre)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            dt = datetime(y, mo, d, 12, 0, 0, tzinfo=timezone.utc)
            ts = int(dt.timestamp())
            if epoch_min <= ts <= epoch_max:
                return ts
        except ValueError:
            pass

    return None


def crear_json_desde_timestamp(ruta_media, timestamp):
    """
    Crea un JSON estilo Google Photos minimalista usando el timestamp dado.
    Devuelve la ruta del JSON creado.
    """
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "title": os.path.basename(ruta_media),
        "photoTakenTime": {
            "timestamp": str(int(timestamp)),
            "formatted": formatted
        }
    }

    destino = ruta_media + ".json"
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return destino


def normalizar_nombre_archivo(ruta):
    """
    Convierte un nombre de archivo en una versión simplificada para
    comparar similitudes. Elimina palabras típicas de Google Photos
    como 'ha editado', 'effects', espacios, guiones, paréntesis, etc.
    """
    nombre = os.path.basename(ruta).lower()
    # Quitamos la extensión
    nombre, _ = os.path.splitext(nombre)

    # Palabras / patrones que estorban para comparar
    reemplazos = [
        "ha editado",  # Google Photos en español
        "ha_editado",
        "edited",  # por si acaso en inglés
        "effects",
    ]
    for r in reemplazos:
        nombre = nombre.replace(r, "")

    # Quitamos paréntesis con números: (1), (2), etc.
    nombre = re.sub(r"\(\d+\)", "", nombre)

    # Quitamos espacios, guiones y subrayados
    nombre = nombre.replace(" ", "").replace("-", "").replace("_", "")

    return nombre


def generar_json_desde_similares(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones=None,
    simulacion=True,
):
    """
    Busca archivos de imagen/vídeo SIN JSON y:

      1º intenta crear un JSON a partir de la FECHA del NOMBRE del archivo
         (timestamp, YYYYMMDD_HHMMSS, etc.)

      2º si no lo consigue, intenta buscar un JSON con nombre similar
         en la misma carpeta y lo copia.

    - simulacion=True  → solo muestra qué haría, sin crear nada.
    - simulacion=False → crea realmente los .json.
    """

    MEDIA_EXTS = {
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic",
        ".mp4", ".mov", ".m4v", ".avi", ".mts", ".mkv"
    }
    UMBRAL_SIMILITUD = 0.70  # similitud mínima para considerar "similar"

    def tarea():
        inicio = time.time()

        try:
            # Bloqueamos botones si se han pasado
            bloquear_botones(botones)

            try:
                salida.delete(1.0, tk.END)
            except tk.TclError:
                return

            contador_var.set("0/0")
            tiempo_var.set("00:00")

            if not os.path.isdir(ruta_base):
                messagebox.showerror("Error", "Ruta no válida o inexistente.")
                return

            salida.insert(
                tk.END,
                "Buscando archivos sin JSON y posibles fuentes (nombre o similares)...\n\n"
            )
            salida.see(tk.END)

            archivos_sin_json = []
            json_en_carpeta = {}

            # 1) Recorremos todo el árbol y separamos media + json
            for dirpath, _, files in os.walk(ruta_base):
                ruta_dir = os.path.abspath(dirpath)
                lista_media = []
                lista_json = []

                for f in files:
                    full = os.path.join(ruta_dir, f)
                    lower = f.lower()

                    if lower.endswith(".json"):
                        lista_json.append(full)
                    else:
                        _, ext = os.path.splitext(lower)
                        if ext in MEDIA_EXTS:
                            lista_media.append(full)

                if not lista_media:
                    continue

                json_en_carpeta[ruta_dir] = lista_json

                for media in lista_media:
                    esperado = media + ".json"
                    if not os.path.exists(esperado):
                        archivos_sin_json.append(media)

            total = len(archivos_sin_json)
            if total == 0:
                salida.insert(
                    tk.END, "No hay archivos de imagen/vídeo sin JSON.\n"
                )
                salida.see(tk.END)
                return

            try:
                progreso["maximum"] = total
                progreso["value"] = 0
            except tk.TclError:
                pass

            # Contadores
            creados_total = 0
            creados_desde_nombre = 0
            con_nombre_valido = 0
            con_similar = 0
            sin_coincidencia = 0

            for i, media in enumerate(archivos_sin_json, start=1):
                ruta_dir = os.path.dirname(media)
                lista_json = json_en_carpeta.get(ruta_dir, [])

                json_destino = media + ".json"
                creado_este = False

                # -------------------------
                # 1) Intentar sacar fecha del nombre
                # -------------------------
                ts = extraer_timestamp_de_nombre(media)
                if ts is not None:
                    con_nombre_valido += 1
                    salida.insert(
                        tk.END,
                        f"[NOMBRE] {media}\n"
                        f"  → timestamp extraído: {ts}\n"
                    )
                    salida.see(tk.END)

                    if not simulacion:
                        if not os.path.exists(json_destino):
                            try:
                                crear_json_desde_timestamp(media, ts)
                                creados_desde_nombre += 1
                                creados_total += 1
                                creado_este = True
                                salida.insert(
                                    tk.END,
                                    f"  JSON creado desde nombre: {json_destino}\n\n"
                                )
                            except Exception as e:
                                salida.insert(
                                    tk.END,
                                    f"  ERROR al crear JSON desde nombre: {e}\n\n"
                                )
                        else:
                            salida.insert(
                                tk.END,
                                "  (Ya existe JSON, no se crea otro)\n\n"
                            )
                    else:
                        salida.insert(
                            tk.END,
                            "  (SIMULACIÓN: se crearía JSON desde nombre)\n\n"
                        )

                # -------------------------
                # 2) Si no hay fecha válida en nombre, buscar JSON similar
                # -------------------------
                if not creado_este and ts is None:
                    mejor_json = None
                    mejor_ratio = 0.0

                    norm_media = normalizar_nombre_archivo(media)

                    for jpath in lista_json:
                        base_json = jpath[:-5] if jpath.lower().endswith(".json") else jpath
                        norm_json = normalizar_nombre_archivo(base_json)

                        if not norm_media or not norm_json:
                            continue

                        ratio = SequenceMatcher(None, norm_media, norm_json).ratio()
                        if ratio > mejor_ratio:
                            mejor_ratio = ratio
                            mejor_json = jpath

                    if mejor_json and mejor_ratio >= UMBRAL_SIMILITUD:
                        con_similar += 1
                        salida.insert(
                            tk.END,
                            f"[SIMILAR] {media}\n"
                            f"  a partir de: {mejor_json} "
                            f"(coincidencia {mejor_ratio:.2f})\n"
                        )
                        salida.see(tk.END)

                        if not simulacion:
                            if not os.path.exists(json_destino):
                                try:
                                    shutil.copy2(mejor_json, json_destino)
                                    creados_total += 1
                                    salida.insert(
                                        tk.END,
                                        f"  JSON copiado a: {json_destino}\n\n"
                                    )
                                except Exception as e:
                                    salida.insert(
                                        tk.END,
                                        f"  ERROR al copiar JSON: {e}\n\n"
                                    )
                            else:
                                salida.insert(
                                    tk.END,
                                    "  (Ya existe JSON, no se copia)\n\n"
                                )
                        else:
                            salida.insert(
                                tk.END,
                                "  (SIMULACIÓN: se copiaría JSON similar)\n\n"
                            )
                    else:
                        sin_coincidencia += 1
                        salida.insert(
                            tk.END,
                            f"[SIN COINCIDENCIA] {media}\n"
                        )
                        salida.see(tk.END)

                # Actualizar progreso
                try:
                    progreso["value"] = i
                    contador_var.set(f"{i}/{total}")
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.update()
                except tk.TclError:
                    return

            # -------------------------
            # Resumen
            # -------------------------
            salida.insert(tk.END, "\n=== RESUMEN ===\n")
            salida.insert(
                tk.END,
                f"Archivos sin JSON: {total}\n"
                f"Con fecha válida en nombre: {con_nombre_valido}\n"
                f"Con JSON similar: {con_similar}\n"
                f"Sin coincidencia: {sin_coincidencia}\n"
                f"JSON creados realmente: {creados_total}\n"
                f"  - Desde nombre: {creados_desde_nombre}\n"
                f"  - Desde similares: {creados_total - creados_desde_nombre}\n"
            )
            salida.see(tk.END)

            if simulacion:
                messagebox.showinfo(
                    "Previsualización terminada",
                    "Revisa el listado para comprobar las coincidencias."
                )
            else:
                messagebox.showinfo(
                    "Proceso terminado",
                    f"Se han creado {creados_total} JSON nuevos."
                )

        finally:
            desbloquear_botones(botones)

    threading.Thread(target=tarea, daemon=True).start()



def previsualizar_json_desde_similares(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones=None,
):
    """
    Simplemente llama a generar_json_desde_similares en modo simulación,
    reutilizando toda la lógica y el sistema de hilos.
    """
    generar_json_desde_similares(
        ruta_base=ruta_base,
        salida=salida,
        progreso=progreso,
        contador_var=contador_var,
        tiempo_var=tiempo_var,
        botones=botones,
        simulacion=True,
    )


# ==========================================================
# INFORME DE ARCHIVOS SIN JSON
# ==========================================================


def informe_archivos_sin_json(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones=None,):
    """
    Genera un informe con TODOS los archivos de imagen/vídeo que no
    tienen su archivo JSON lateral (<archivo.ext>.json).

    Crea un fichero de texto en la carpeta base:
        informe_sin_json_YYYYMMDD_HHMMSS.txt
    """

    MEDIA_EXTS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".heic",
        ".mp4",
        ".mov",
        ".m4v",
        ".avi",
        ".mts",
        ".mkv",
    }

    def tarea():
        inicio = time.time()

        try:
            try:
                salida.delete(1.0, tk.END)
            except tk.TclError:
                return

            contador_var.set("0/0")
            tiempo_var.set("00:00")

            if not os.path.isdir(ruta_base):
                messagebox.showerror("Error", "Ruta no válida o inexistente.")
                return

            salida.insert(
                tk.END, "Generando informe de archivos sin JSON...\n\n"
            )
            salida.see(tk.END)

            media_files = []
            sin_json = []

            # Escaneo recursivo
            for dirpath, _, files in os.walk(ruta_base):
                for f in files:
                    full = os.path.join(dirpath, f)
                    lower = f.lower()
                    if lower.endswith(".json"):
                        continue
                    _, ext = os.path.splitext(lower)
                    if ext in MEDIA_EXTS:
                        media_files.append(full)

            total = len(media_files)
            if total == 0:
                salida.insert(
                    tk.END,
                    "No se han encontrado archivos de imagen/vídeo.\n",
                )
                salida.see(tk.END)
                return

            try:
                progreso["maximum"] = total
                progreso["value"] = 0
            except tk.TclError:
                pass

            for i, media in enumerate(media_files, start=1):
                json_esperado = media + ".json"
                if not os.path.exists(json_esperado):
                    sin_json.append(media)
                    try:
                        salida.insert(tk.END, f"Sin JSON: {media}\n")
                        salida.see(tk.END)
                    except tk.TclError:
                        return

                try:
                    progreso["value"] = i
                    contador_var.set(f"{i}/{total}")
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.update()
                except tk.TclError:
                    return

            # Resumen e informe a fichero
            salida.insert(tk.END, "\n=== RESUMEN ===\n")
            salida.insert(
                tk.END,
                (
                    f"Archivos de imagen/vídeo: {total}\n"
                    f"Archivos sin JSON: {len(sin_json)}\n\n"
                ),
            )
            salida.see(tk.END)

            if sin_json:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                nombre_informe = f"informe_sin_json_{timestamp}.txt"
                ruta_informe = os.path.join(ruta_base, nombre_informe)
                try:
                    with open(ruta_informe, "w", encoding="utf-8") as f:
                        f.write(
                            "INFORME DE ARCHIVOS SIN JSON\n"
                            f"Carpeta base: {ruta_base}\n"
                            f"Total archivos de imagen/vídeo: {total}\n"
                            f"Archivos sin JSON: {len(sin_json)}\n\n"
                        )
                        for media in sin_json:
                            f.write(media + "\n")

                    salida.insert(
                        tk.END, f"Informe guardado en:\n{ruta_informe}\n"
                    )
                    salida.see(tk.END)

                    messagebox.showinfo(
                        "Informe generado",
                        f"Se ha creado el informe:\n{ruta_informe}",
                    )
                except Exception as e:
                    messagebox.showerror(
                        "Error al guardar informe",
                        f"No se pudo guardar el informe:\n{e}",
                    )
            else:
                messagebox.showinfo(
                    "Informe generado",
                    "Todos los archivos de imagen/vídeo tienen JSON.",
                )

        finally:
            if botones:
                desbloquear_botones(botones)

    if botones:
        bloquear_botones(botones)
    threading.Thread(target=tarea, daemon=True).start()

# ==========================================================
# MANEJO DE LA PESTAÑA CUARENTENA
# ==========================================================

def listar_cuarentena(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones,):
    """
    Lista todos los archivos que hay dentro de la carpeta de cuarentena
    asociada a ruta_base.
    """
    def tarea():
        inicio = time.time()

        try:
            try:
                salida.delete(1.0, tk.END)
            except tk.TclError:
                return

            contador_var.set("0/0")
            tiempo_var.set("00:00")

            if not os.path.isdir(ruta_base):
                messagebox.showerror("Error", "Ruta base no válida o inexistente.")
                return

            ruta_base_abs = os.path.abspath(ruta_base)
            carpeta_cuar = os.path.join(ruta_base_abs, NOMBRE_CARPETA_CUARENTENA)

            if not os.path.isdir(carpeta_cuar):
                salida.insert(
                    tk.END,
                    "No se ha encontrado la carpeta de cuarentena para esta ruta.\n"
                )
                salida.see(tk.END)
                messagebox.showinfo(
                    "Cuarentena vacía",
                    "No se ha encontrado ninguna carpeta de cuarentena en esta ruta."
                )
                return

            salida.insert(
                tk.END,
                f"Listando archivos en cuarentena:\n{carpeta_cuar}\n\n"
            )
            salida.see(tk.END)

            archivos = []
            for dirpath, _, files in os.walk(carpeta_cuar):
                for f in files:
                    archivos.append(os.path.join(dirpath, f))

            total = len(archivos)
            if total == 0:
                salida.insert(tk.END, "La cuarentena está vacía.\n")
                salida.see(tk.END)
                messagebox.showinfo(
                    "Cuarentena vacía",
                    "No hay archivos en cuarentena para esta ruta."
                )
                return

            try:
                progreso["maximum"] = total
                progreso["value"] = 0
            except tk.TclError:
                pass

            for i, ruta_arch in enumerate(archivos, start=1):
                try:
                    # MUY IMPORTANTE: mostramos solo la ruta, sin texto delante,
                    # para poder seleccionarla y usarla como ruta exacta.
                    salida.insert(tk.END, ruta_arch + "\n")
                    salida.see(tk.END)

                    progreso["value"] = i
                    contador_var.set(f"{i}/{total}")
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.update()
                except tk.TclError:
                    return

            salida.insert(tk.END, "\n=== RESUMEN ===\n")
            salida.insert(tk.END, f"Archivos en cuarentena: {total}\n")
            salida.see(tk.END)

        finally:
            desbloquear_botones(botones)

    bloquear_botones(botones)
    threading.Thread(target=tarea, daemon=True).start()

def restaurar_cuarentena(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones,
    rutas_seleccionadas=None,
):
    """
    Restaura archivos desde la carpeta de cuarentena a su ubicación original.

    - Si rutas_seleccionadas es una lista, intentará restaurar SOLO esos archivos.
    - Si rutas_seleccionadas es None o vacía, intentará restaurar TODO lo que haya
      en la cuarentena de esa ruta_base.
    """
    def tarea():
        inicio = time.time()
        restaurados = 0
        errores = 0

        try:
            try:
                salida.delete(1.0, tk.END)
            except tk.TclError:
                return

            contador_var.set("0/0")
            tiempo_var.set("00:00")

            if not os.path.isdir(ruta_base):
                messagebox.showerror("Error", "Ruta base no válida o inexistente.")
                return

            ruta_base_abs = os.path.abspath(ruta_base)
            carpeta_cuar = os.path.join(ruta_base_abs, NOMBRE_CARPETA_CUARENTENA)

            if not os.path.isdir(carpeta_cuar):
                salida.insert(
                    tk.END,
                    "No se ha encontrado la carpeta de cuarentena para esta ruta.\n"
                )
                salida.see(tk.END)
                messagebox.showinfo(
                    "Cuarentena vacía",
                    "No hay carpeta de cuarentena en esta ruta."
                )
                return

            # Construimos la lista de archivos a restaurar
            if rutas_seleccionadas:
                archivos = [r for r in rutas_seleccionadas if os.path.exists(r)]
            else:
                archivos = []
                for dirpath, _, files in os.walk(carpeta_cuar):
                    for f in files:
                        archivos.append(os.path.join(dirpath, f))

            total = len(archivos)
            if total == 0:
                salida.insert(
                    tk.END,
                    "No hay archivos que restaurar desde la cuarentena.\n"
                )
                salida.see(tk.END)
                return

            confirmar = messagebox.askyesno(
                "Confirmar restauración",
                f"¿Restaurar {total} archivo(s) desde la cuarentena?"
            )
            if not confirmar:
                return

            try:
                progreso["maximum"] = total
                progreso["value"] = 0
            except tk.TclError:
                pass

            # Leemos registro para intentar recuperar la ruta original
            registro = leer_json()
            if registro is None:
                registro = []

            for i, ruta_cuar in enumerate(archivos, start=1):
                try:
                    # Buscar en el registro la última operación de cuarentena
                    ruta_original = None
                    hash_reg = None

                    for op in reversed(registro):
                        if (
                            op.get("accion") == "cuarentena"
                            and op.get("archivo_cuarentena") == ruta_cuar
                        ):
                            ruta_original = op.get("archivo_original")
                            hash_reg = op.get("hash")
                            break

                    if ruta_original is None:
                        # Si no hay información en el registro, reconstruimos
                        # la ruta original a partir de la relativa.
                        rel = os.path.relpath(ruta_cuar, carpeta_cuar)
                        ruta_original = os.path.join(ruta_base_abs, rel)

                    hash_actual = calcular_hash(ruta_cuar)

                    # Si tenemos hash en el registro, podemos verificar
                    if hash_reg and hash_reg != hash_actual:
                        salida.insert(
                            tk.END,
                            f"⚠️ Hash distinto al registrado, restaurando igualmente: {ruta_cuar}\n"
                        )
                        salida.see(tk.END)

                    # Creamos carpeta destino si no existe
                    os.makedirs(os.path.dirname(ruta_original), exist_ok=True)

                    shutil.move(ruta_cuar, ruta_original)

                    salida.insert(
                        tk.END,
                        f"🔁 Restaurado: {ruta_cuar} → {ruta_original}\n"
                    )
                    salida.see(tk.END)
                    restaurados += 1

                    # Registramos la restauración
                    registrar_operacion([{
                        "accion": "restaurado",
                        "archivo_original": ruta_original,
                        "archivo_cuarentena": ruta_cuar,
                        "hash": hash_actual,
                    }])

                except Exception as e:
                    salida.insert(
                        tk.END,
                        f"❌ ERROR restaurando {ruta_cuar}: {e}\n"
                    )
                    salida.see(tk.END)
                    errores += 1

                try:
                    progreso["value"] = i
                    contador_var.set(f"{i}/{total}")
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.update()
                except tk.TclError:
                    return

            salida.insert(tk.END, "\n=== RESUMEN RESTAURACIÓN ===\n")
            salida.insert(tk.END, f"Total a restaurar: {total}\n")
            salida.insert(tk.END, f"Restaurados: {restaurados}\n")
            salida.insert(tk.END, f"Errores: {errores}\n")
            salida.see(tk.END)

            messagebox.showinfo(
                "Restauración completada",
                f"Se han restaurado {restaurados} archivo(s)."
            )

        finally:
            desbloquear_botones(botones)

    bloquear_botones(botones)
    threading.Thread(target=tarea, daemon=True).start()

def purgar_cuarentena(
    ruta_base,
    salida,
    progreso,
    contador_var,
    tiempo_var,
    botones,
    rutas_seleccionadas=None,
):
    """
    Borra DEFINITIVAMENTE archivos que están en la carpeta de cuarentena.

    - Si rutas_seleccionadas es una lista, purga SOLO esos archivos.
    - Si rutas_seleccionadas es None o vacía, purga TODO lo que haya
      en la cuarentena para esa ruta_base.
    """
    def tarea():
        inicio = time.time()
        purgados = 0
        errores = 0

        try:
            try:
                salida.delete(1.0, tk.END)
            except tk.TclError:
                return

            contador_var.set("0/0")
            tiempo_var.set("00:00")

            if not os.path.isdir(ruta_base):
                messagebox.showerror("Error", "Ruta base no válida o inexistente.")
                return

            ruta_base_abs = os.path.abspath(ruta_base)
            carpeta_cuar = os.path.join(ruta_base_abs, NOMBRE_CARPETA_CUARENTENA)

            if not os.path.isdir(carpeta_cuar):
                salida.insert(
                    tk.END,
                    "No se ha encontrado la carpeta de cuarentena para esta ruta.\n"
                )
                salida.see(tk.END)
                messagebox.showinfo(
                    "Cuarentena vacía",
                    "No hay carpeta de cuarentena en esta ruta."
                )
                return

            # Construimos la lista de archivos a purgar
            if rutas_seleccionadas:
                archivos = [r for r in rutas_seleccionadas if os.path.exists(r)]
            else:
                archivos = []
                for dirpath, _, files in os.walk(carpeta_cuar):
                    for f in files:
                        archivos.append(os.path.join(dirpath, f))

            total = len(archivos)
            if total == 0:
                salida.insert(
                    tk.END,
                    "No hay archivos que purgar en la cuarentena.\n"
                )
                salida.see(tk.END)
                return

            confirmar = messagebox.askyesno(
                "Confirmar purga definitiva",
                f"Se van a ELIMINAR DEFINITIVAMENTE {total} archivo(s) "
                f"de la cuarentena.\nEsta acción no se puede deshacer.\n\n"
                f"¿Continuar?"
            )
            if not confirmar:
                return

            try:
                progreso["maximum"] = total
                progreso["value"] = 0
            except tk.TclError:
                pass

            for i, ruta_cuar in enumerate(archivos, start=1):
                try:
                    hash_archivo = calcular_hash(ruta_cuar)

                    os.remove(ruta_cuar)

                    salida.insert(
                        tk.END,
                        f"🔥 PURGADO definitivamente: {ruta_cuar}\n"
                    )
                    salida.see(tk.END)
                    purgados += 1

                    # Registramos la purga
                    registrar_operacion([{
                        "accion": "purgado",
                        "archivo_cuarentena": ruta_cuar,
                        "hash": hash_archivo,
                    }])

                except Exception as e:
                    salida.insert(
                        tk.END,
                        f"❌ ERROR purgando {ruta_cuar}: {e}\n"
                    )
                    salida.see(tk.END)
                    errores += 1

                try:
                    progreso["value"] = i
                    contador_var.set(f"{i}/{total}")
                    tiempo_var.set(formatear_tiempo(time.time() - inicio))
                    salida.update()
                except tk.TclError:
                    return

            salida.insert(tk.END, "\n=== RESUMEN PURGA ===\n")
            salida.insert(tk.END, f"Total a purgar: {total}\n")
            salida.insert(tk.END, f"Purgados: {purgados}\n")
            salida.insert(tk.END, f"Errores: {errores}\n")
            salida.see(tk.END)

            messagebox.showinfo(
                "Purga completada",
                f"Se han eliminado definitivamente {purgados} archivo(s)."
            )

        finally:
            desbloquear_botones(botones)

    bloquear_botones(botones)
    threading.Thread(target=tarea, daemon=True).start()
