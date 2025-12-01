# ui.py
# ==========================================================
# Interfaz moderna del Gestor de Archivos Unificado (Dark)
# ==========================================================

import os
import time
import inspect
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# Intentamos importar el módulo de operaciones
try:
    import operaciones as ops
except ImportError:
    ops = None

# Ruta del registro de operaciones (por si lo define utils.py)
try:
    from utils import RUTA_REGISTRO_OPERACIONES
except Exception:
    RUTA_REGISTRO_OPERACIONES = "registro_operaciones.json"


def _safe_call(func_name: str, **posibles_kwargs):
    """
    Llama a una función de operaciones.py si existe, filtrando los kwargs
    para que solo se pasen los parámetros aceptados por su firma.
    """
    if ops is None:
        messagebox.showerror(
            "Error",
            "No se pudo importar 'operaciones.py'. "
            "Asegúrate de que el archivo existe junto a main.py.",
        )
        return

    func = getattr(ops, func_name, None)
    if func is None:
        messagebox.showerror(
            "Función no encontrada",
            f"No existe la función '{func_name}' en operaciones.py.\n\n"
            "Revisa el nombre de la función o coméntamelo para ajustarlo.",
        )
        return

    sig = inspect.signature(func)
    kwargs = {k: v for k, v in posibles_kwargs.items() if k in sig.parameters}

    try:
        return func(**kwargs)
    except Exception as e:
        messagebox.showerror(
            "Error en operación",
            f"Se produjo un error al ejecutar '{func_name}':\n\n{e}",
        )


class GestorArchivosUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.master.title("Gestor de Archivos Unificado v1.1 - Dark Edition")
        self.master.geometry("1200x700")
        self.master.configure(bg="#1E1E1E")
        self.master.resizable(True, True)
        self.pack(fill="both", expand=True)

        # Variables globales
        self.ruta_var = tk.StringVar()
        self.ext1_var = tk.StringVar(value=".supplemental-metadata.json")
        self.ext2_var = tk.StringVar(value=".json")
        self.ext_borrar_var = tk.StringVar(value=".zip")
        self.contador_var = tk.StringVar(value="0/0")
        self.tiempo_var = tk.StringVar(value="00:00")
        self.filtro_var = tk.StringVar()
        self.cuarentena_var = tk.BooleanVar(value=True)  # NUEVO: usar cuarentena por defecto


        # Referencias a widgets que se crean en cada página
        self.salida = None
        self.progreso = None

        # Referencias a botones (para bloquear/desbloquear)
        self.btn_ren_buscar = None
        self.btn_ren_renombrar = None
        self.btn_ren_revertir = None

        self.btn_del_buscar = None
        self.btn_del_eliminar = None

        self.btn_exif_aplicar = None
        self.btn_exif_prev = None
        self.btn_exif_crear = None
        self.btn_exif_informe = None

        # NUEVO: botones de la página Cuarentena
        self.btn_cuar_listar = None
        self.btn_cuar_rest_sel = None
        self.btn_cuar_rest_todo = None
        self.btn_cuar_purgar_sel = None      # NUEVO
        self.btn_cuar_purgar_todo = None     # NUEVO

        # Crear interfaz
        self._crear_estilo()
        self._crear_panel_lateral()
        self._crear_contenedor()

        # Página inicial: Fechas ExifTool
        self._cargar_pagina("exiftool")

    def _formatear_tiempo(self, segundos: float) -> str:
        """Devuelve mm:ss a partir de segundos."""
        seg = int(segundos)
        m, s = divmod(seg, 60)
        return f"{m:02d}:{s:02d}"

    # ------------------------------------------------------------------
    # Helpers de interfaz
    # ------------------------------------------------------------------

    def _seleccionar_carpeta(self):
        """Abre un diálogo para elegir carpeta y la guarda en self.ruta_var."""
        carpeta = filedialog.askdirectory(
            title="Seleccionar carpeta base",
            initialdir=self.ruta_var.get() or os.getcwd(),
        )
        if carpeta:
            self.ruta_var.set(carpeta)

    def _crear_estilo(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#1E1E1E")
        style.configure("Side.TFrame", background="#252526")
        style.configure(
            "Header.TLabel",
            background="#1E1E1E",
            foreground="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "TLabel",
            background="#1E1E1E",
            foreground="#FFFFFF",
            font=("Segoe UI", 9),
        )

        # Lateral
        style.configure(
            "SideTitle.TLabel",
            background="#252526",
            foreground="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "SideButton.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#0E639C",
            foreground="#FFFFFF",
        )
        style.map("SideButton.TButton", background=[("active", "#1177BB")])

        # Botones de acción
        style.configure(
            "Green.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#107C10",
            foreground="#FFFFFF",
        )
        style.map("Green.TButton", background=[("active", "#149414")])

        style.configure(
            "Orange.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#D98C00",
            foreground="#FFFFFF",
        )
        style.map("Orange.TButton", background=[("active", "#E5A000")])

        style.configure(
            "Red.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#C1272D",
            foreground="#FFFFFF",
        )
        style.map("Red.TButton", background=[("active", "#E03A3F")])

        style.configure(
            "Blue.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#0E639C",
            foreground="#FFFFFF",
        )
        style.map("Blue.TButton", background=[("active", "#1177BB")])

        style.configure(
            "TProgressbar",
            troughcolor="#3E3E42",
            bordercolor="#3E3E42",
            background="#0E639C",
        )

    def _crear_panel_lateral(self):
        """Crea el menú lateral con los botones de navegación."""
        panel = ttk.Frame(self, style="Side.TFrame", width=180)
        panel.pack(side="left", fill="y")

        ttk.Label(panel, text="GESTOR", style="SideTitle.TLabel").pack(pady=10)

        # 1º - Fechas ExifTool
        self.btn_exiftool = ttk.Button(
            panel,
            text="Fechas ExifTool",
            style="SideButton.TButton",
            command=lambda: self._cargar_pagina("exiftool"),
        )
        self.btn_exiftool.pack(fill="x", padx=10, pady=5)

        # 2º - Renombrar / Revertir
        self.btn_renombrar = ttk.Button(
            panel,
            text="Renombrar / Revertir",
            style="SideButton.TButton",
            command=lambda: self._cargar_pagina("renombrar"),
        )
        self.btn_renombrar.pack(fill="x", padx=10, pady=5)

        # 3º - Eliminar archivos
        self.btn_eliminar = ttk.Button(
            panel,
            text="Eliminar archivos",
            style="SideButton.TButton",
            command=lambda: self._cargar_pagina("eliminar"),
        )
        self.btn_eliminar.pack(fill="x", padx=10, pady=5)

        # 4º - Cuarentena
        self.btn_cuarentena = ttk.Button(
            panel,
            text="Cuarentena",
            style="SideButton.TButton",
            command=lambda: self._cargar_pagina("cuarentena"),
        )
        self.btn_cuarentena.pack(fill="x", padx=10, pady=5)

        # 5º - Historial
        self.btn_historial = ttk.Button(
            panel,
            text="Historial",
            style="SideButton.TButton",
            command=lambda: self._cargar_pagina("historial"),
        )
        self.btn_historial.pack(fill="x", padx=10, pady=5)


    def _crear_contenedor(self):
        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(side="right", fill="both", expand=True)

    def _limpiar_contenedor(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()
        self.salida = None
        self.progreso = None
        self.contador_var.set("0/0")
        self.tiempo_var.set("00:00")

    def _cargar_pagina(self, sel_pagina: str):
        self._limpiar_contenedor()

        if sel_pagina == "renombrar":
            self._pagina_renombrar()
        elif sel_pagina == "eliminar":
            self._pagina_eliminar()
        elif sel_pagina == "historial":
            self._pagina_historial()
        elif sel_pagina == "exiftool":
            self._pagina_exiftool()
        elif sel_pagina == "cuarentena":   # NUEVO
            self._pagina_cuarentena()

    # ------------------------------------------------------------------
    # PÁGINA 1: RENOMBRAR / REVERTIR
    # ------------------------------------------------------------------

    def _pagina_renombrar(self):
        ttk.Label(
            self.contenedor,
            text="Renombrar / Revertir archivos",
            style="Header.TLabel",
        ).pack(pady=10)

        frame1 = ttk.Frame(self.contenedor)
        frame1.pack(pady=5)

        ttk.Label(frame1, text="Carpeta base:").pack(side="left", padx=5)
        ttk.Entry(frame1, textvariable=self.ruta_var, width=60).pack(
            side="left", padx=5
        )
        ttk.Button(
            frame1,
            text="Examinar...",
            command=self._seleccionar_carpeta,
        ).pack(side="left", padx=5)

        frame2 = ttk.Frame(self.contenedor)
        frame2.pack(pady=5)

        ttk.Label(frame2, text="Buscar:").pack(side="left", padx=5)
        ttk.Entry(frame2, textvariable=self.ext1_var, width=25).pack(
            side="left", padx=5
        )

        ttk.Label(frame2, text="Reemplazar por:").pack(side="left", padx=5)
        ttk.Entry(frame2, textvariable=self.ext2_var, width=25).pack(
            side="left", padx=5
        )

        frame3 = ttk.Frame(self.contenedor)
        frame3.pack(pady=10)

        # Botón BUSCAR
        btn_buscar = ttk.Button(
            frame3,
            text="Buscar",
            style="Blue.TButton",
            command=self._accion_buscar_renombrar,
        )
        btn_buscar.pack(side="left", padx=10)

        btn_renombrar = ttk.Button(
            frame3,
            text="Renombrar",
            style="Green.TButton",
            command=self._accion_renombrar,
        )
        btn_renombrar.pack(side="left", padx=10)

        btn_revertir = ttk.Button(
            frame3,
            text="Revertir",
            style="Orange.TButton",
            command=self._accion_revertir,
        )
        btn_revertir.pack(side="left", padx=10)

        # Guardamos referencias de botones
        self.btn_ren_buscar = btn_buscar
        self.btn_ren_renombrar = btn_renombrar
        self.btn_ren_revertir = btn_revertir

        # Barra de progreso + contador + tiempo
        frame_prog = ttk.Frame(self.contenedor)
        frame_prog.pack(fill="x", padx=10, pady=(5, 0))

        self.progreso = ttk.Progressbar(
            frame_prog, mode="determinate", maximum=100
        )
        self.progreso.pack(side="left", fill="x", expand=True)

        ttk.Label(frame_prog, textvariable=self.contador_var).pack(
            side="left", padx=10
        )
        ttk.Label(frame_prog, textvariable=self.tiempo_var).pack(
            side="left", padx=5
        )

        # Área de salida
        self.salida = scrolledtext.ScrolledText(
            self.contenedor,
            bg="#1E1E1E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
        )
        self.salida.pack(fill="both", expand=True, padx=10, pady=5)

    def _accion_buscar_renombrar(self):
        """
        Solo busca y lista archivos que coincidan con el texto de 'Buscar'.
        NO renombra nada.
        """
        ruta = self.ruta_var.get().strip()
        patron = self.ext1_var.get().strip()

        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        if not patron:
            messagebox.showwarning(
                "Patrón requerido",
                "Escribe algo en 'Buscar' (por ejemplo '.supplemental-metadata.json')."
            )
            return

        if self.salida:
            self.salida.delete(1.0, tk.END)
            self.salida.insert(
                tk.END,
                f"Buscando archivos que contengan '{patron}' en:\n{ruta}\n\n"
            )
            self.salida.see(tk.END)

        inicio = time.time()
        total_archivos = 0
        total_coincidencias = 0

        # Barra en modo determinado
        try:
            self.progreso.config(mode="determinate", value=0, maximum=1)
        except Exception:
            pass

        # Primero contamos archivos para fijar el máximo
        for _, _, ficheros in os.walk(ruta):
            total_archivos += len(ficheros)

        if total_archivos == 0:
            self.contador_var.set("0/0")
            self.tiempo_var.set(self._formatear_tiempo(time.time() - inicio))
            return

        try:
            self.progreso.config(maximum=total_archivos, value=0)
        except Exception:
            pass

        procesados = 0
        for raiz, _, ficheros in os.walk(ruta):
            for nombre in ficheros:
                procesados += 1
                if patron in nombre:
                    total_coincidencias += 1
                    if self.salida:
                        self.salida.insert(
                            tk.END, os.path.join(raiz, nombre) + "\n"
                        )
                        # Hacer scroll mientras escribe
                        self.salida.see(tk.END)

                # Actualizar barra y tiempo cada cierto nº de archivos
                if procesados % 200 == 0 or procesados == total_archivos:
                    try:
                        self.progreso["value"] = procesados
                    except Exception:
                        pass
                    self.tiempo_var.set(
                        self._formatear_tiempo(time.time() - inicio)
                    )
                    # Refrescar UI
                    self.update_idletasks()

        # Restaurar valores finales
        self.contador_var.set(f"{total_coincidencias}/{total_archivos}")
        self.tiempo_var.set(self._formatear_tiempo(time.time() - inicio))

        if self.salida:
            self.salida.insert(
                tk.END,
                "\n--- RESUMEN ---\n"
                f"Archivos analizados: {total_archivos}\n"
                f"Coincidencias: {total_coincidencias}\n"
            )
            # Asegurar que se ve el final del listado
            self.salida.see(tk.END)


    def _accion_renombrar(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        _safe_call(
            "renombrar_archivos",
            ruta_base=ruta,
            ext_origen=self.ext1_var.get(),
            ext_nueva=self.ext2_var.get(),
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_ren_buscar,
                self.btn_ren_renombrar,
                self.btn_ren_revertir,
            ],
        )

    def _accion_revertir(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        _safe_call(
            "renombrar_archivos",
            ruta_base=ruta,
            ext_origen=self.ext1_var.get(),
            ext_nueva=self.ext2_var.get(),
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            revertir=True,
            botones=[
                self.btn_ren_buscar,
                self.btn_ren_renombrar,
                self.btn_ren_revertir,
            ],
        )

    # ------------------------------------------------------------------
    # PÁGINA 2: ELIMINAR ARCHIVOS
    # ------------------------------------------------------------------

    def _pagina_eliminar(self):
        ttk.Label(
            self.contenedor,
            text="Eliminar archivos por extensión",
            style="Header.TLabel",
        ).pack(pady=10)

        frame1 = ttk.Frame(self.contenedor)
        frame1.pack(pady=5)

        ttk.Label(frame1, text="Carpeta base:").pack(side="left", padx=5)
        ttk.Entry(frame1, textvariable=self.ruta_var, width=60).pack(
            side="left", padx=5
        )
        ttk.Button(
            frame1,
            text="Examinar...",
            command=self._seleccionar_carpeta,
        ).pack(side="left", padx=5)

        frame2 = ttk.Frame(self.contenedor)
        frame2.pack(pady=5)

        ttk.Label(frame2, text="Extensión a eliminar:").pack(
            side="left", padx=5
        )
        ttk.Entry(frame2, textvariable=self.ext_borrar_var, width=20).pack(
            side="left", padx=5
        )

        # NUEVO: casilla de cuarentena
        chk_cuar = ttk.Checkbutton(
            frame2,
            text="Enviar a cuarentena (recomendado)",
            variable=self.cuarentena_var
        )
        chk_cuar.pack(side="left", padx=10)

        frame3 = ttk.Frame(self.contenedor)
        frame3.pack(pady=10)

        btn_buscar = ttk.Button(
            frame3,
            text="Buscar",
            style="Blue.TButton",
            command=self._accion_buscar_eliminar,
        )
        btn_buscar.pack(side="left", padx=10)

        btn_eliminar = ttk.Button(
            frame3,
            text="Eliminar",
            style="Red.TButton",
            command=self._accion_eliminar,
        )
        btn_eliminar.pack(side="left", padx=10)

        self.btn_del_buscar = btn_buscar
        self.btn_del_eliminar = btn_eliminar

        # Progreso
        frame_prog = ttk.Frame(self.contenedor)
        frame_prog.pack(fill="x", padx=10, pady=(5, 0))

        self.progreso = ttk.Progressbar(
            frame_prog, mode="determinate", maximum=100
        )
        self.progreso.pack(side="left", fill="x", expand=True)

        ttk.Label(frame_prog, textvariable=self.contador_var).pack(
            side="left", padx=10
        )
        ttk.Label(frame_prog, textvariable=self.tiempo_var).pack(
            side="left", padx=5
        )

        # Área de salida
        self.salida = scrolledtext.ScrolledText(
            self.contenedor,
            bg="#1E1E1E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
        )
        self.salida.pack(fill="both", expand=True, padx=10, pady=5)

    def _accion_buscar_eliminar(self):
        ruta = self.ruta_var.get().strip()
        ext = self.ext_borrar_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return
        if not ext:
            messagebox.showwarning(
                "Extensión requerida",
                "Escribe una extensión (por ej. .zip).",
            )
            return

        _safe_call(
            "previsualizar_archivos",
            ruta_base=ruta,
            extension=ext,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[self.btn_del_buscar, self.btn_del_eliminar],
        )

    def _accion_eliminar(self):
        ruta = self.ruta_var.get().strip()
        ext = self.ext_borrar_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return
        if not ext:
            messagebox.showwarning(
                "Extensión requerida",
                "Escribe una extensión (por ej. .zip).",
            )
            return

        # Detectar si el usuario ha seleccionado rutas en el log
        rutas_seleccionadas = []
        if self.salida is not None:
            try:
                texto_sel = self.salida.get("sel.first", "sel.last")
            except tk.TclError:
                texto_sel = ""

            for linea in texto_sel.splitlines():
                linea = linea.strip()
                if linea:
                    rutas_seleccionadas.append(linea)

        if rutas_seleccionadas:
            # Solo archivos seleccionados
            _safe_call(
                "eliminar_archivos",
                ruta_base=ruta,
                extension=ext,
                salida=self.salida,
                progreso=self.progreso,
                contador_var=self.contador_var,
                tiempo_var=self.tiempo_var,
                botones=[self.btn_del_buscar, self.btn_del_eliminar],
                rutas_seleccionadas=rutas_seleccionadas,
                usar_cuarentena=self.cuarentena_var.get(),  # NUEVO
            )
        else:
            # Todos los archivos con esa extensión
            _safe_call(
                "eliminar_archivos",
                ruta_base=ruta,
                extension=ext,
                salida=self.salida,
                progreso=self.progreso,
                contador_var=self.contador_var,
                tiempo_var=self.tiempo_var,
                botones=[self.btn_del_buscar, self.btn_del_eliminar],
                usar_cuarentena=self.cuarentena_var.get(),  # NUEVO
            )

    # ------------------------------------------------------------------
    # PÁGINA 3: HISTORIAL
    # ------------------------------------------------------------------

    def _pagina_historial(self):
        ttk.Label(
            self.contenedor,
            text="Historial de operaciones",
            style="Header.TLabel",
        ).pack(pady=10)

        frame_filtro = ttk.Frame(self.contenedor)
        frame_filtro.pack(pady=5, fill="x")

        ttk.Label(frame_filtro, text="Filtro (contiene):").pack(
            side="left", padx=5
        )
        ttk.Entry(frame_filtro, textvariable=self.filtro_var, width=30).pack(
            side="left", padx=5
        )
        ttk.Button(
            frame_filtro,
            text="Actualizar",
            command=self._cargar_historial,
        ).pack(side="left", padx=5)

        self.salida = scrolledtext.ScrolledText(
            self.contenedor,
            bg="#1E1E1E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
        )
        self.salida.pack(fill="both", expand=True, padx=10, pady=5)

        self._cargar_historial()

    def _cargar_historial(self):
        if self.salida is None:
            return

        self.salida.delete(1.0, tk.END)

        if not os.path.exists(RUTA_REGISTRO_OPERACIONES):
            self.salida.insert(
                tk.END,
                "No se encontró el archivo de historial:\n"
                f"{RUTA_REGISTRO_OPERACIONES}\n",
            )
            return

        try:
            with open(RUTA_REGISTRO_OPERACIONES, "r", encoding="utf-8") as f:
                contenido = f.read()
        except Exception as e:
            self.salida.insert(
                tk.END,
                f"Error al leer el historial:\n{e}\n",
            )
            return

        filtro = self.filtro_var.get().strip().lower()
        if not filtro:
            self.salida.insert(tk.END, contenido)
        else:
            for linea in contenido.splitlines():
                if filtro in linea.lower():
                    self.salida.insert(tk.END, linea + "\n")

    # ------------------------------------------------------------------
    # PÁGINA 4: FECHAS EXIFTOOL
    # ------------------------------------------------------------------

    def _pagina_exiftool(self):
        ttk.Label(
            self.contenedor,
            text="Actualizar fechas con ExifTool (Google Photos JSON)",
            style="Header.TLabel",
        ).pack(pady=10)

        frame1 = ttk.Frame(self.contenedor)
        frame1.pack(pady=5)

        ttk.Label(
            frame1,
            text="Carpeta base (Takeout / Google Fotos):",
        ).pack(side="left", padx=5)
        ttk.Entry(frame1, textvariable=self.ruta_var, width=60).pack(
            side="left", padx=5
        )
        ttk.Button(
            frame1,
            text="Examinar...",
            command=self._seleccionar_carpeta,
        ).pack(side="left", padx=5)

        frame_botones = ttk.Frame(self.contenedor)
        frame_botones.pack(pady=10)

        self.btn_exif = ttk.Button(
            frame_botones,
            text="Aplicar fechas desde JSON (ExifTool)",
            style="Blue.TButton",
            command=self._accion_exiftool
        )
        self.btn_exif.pack(side="left", padx=5)

        self.btn_prev = ttk.Button(
            frame_botones,
            text="Previsualizar JSON desde similares",
            style="Blue.TButton",
            command=self._accion_previsualizar_json_similares
        )
        self.btn_prev.pack(side="left", padx=5)

        self.btn_crear = ttk.Button(
            frame_botones,
            text="Crear JSON (nombre + similares)",
            style="Blue.TButton",
            command=self._accion_crear_json_similares
        )
        self.btn_crear.pack(side="left", padx=5)

        self.btn_informe = ttk.Button(
            frame_botones,
            text="Informe archivos sin JSON",
            style="Blue.TButton",
            command=self._accion_informe_sin_json
        )
        self.btn_informe.pack(side="left", padx=5)


        self.btn_exif_aplicar = self.btn_exif
        self.btn_exif_prev = self.btn_prev
        self.btn_exif_crear = self.btn_crear
        self.btn_exif_informe = self.btn_informe

        frame_prog = ttk.Frame(self.contenedor)
        frame_prog.pack(fill="x", padx=10, pady=(5, 0))

        self.progreso = ttk.Progressbar(
            frame_prog, mode="determinate", maximum=100
        )
        self.progreso.pack(side="left", fill="x", expand=True)

        ttk.Label(frame_prog, textvariable=self.contador_var).pack(
            side="left", padx=10
        )
        ttk.Label(frame_prog, textvariable=self.tiempo_var).pack(
            side="left", padx=5
        )

        self.salida = scrolledtext.ScrolledText(
            self.contenedor,
            bg="#1E1E1E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
        )
        self.salida.pack(fill="both", expand=True, padx=10, pady=5)

    def _accion_exiftool(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida",
                "Selecciona la carpeta base de Takeout / Google Fotos."
            )
            return

        # Botones de esta página que queremos bloquear mientras corre exiftool
        botones = [
            # estos nombres son las variables que creas en _pagina_exiftool
            # asegúrate de que están guardadas como self.btn_... allí
            self.btn_exif,
            self.btn_prev,
            self.btn_crear,
            self.btn_informe,
        ]

        _safe_call(
            "aplicar_exiftool_fechas",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=botones,
        )

    def _accion_previsualizar_json_similares(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida",
                "Selecciona la carpeta base de Takeout / Google Fotos.",
            )
            return

        _safe_call(
            "generar_json_desde_similares",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            simulacion=True,
            botones=[
                self.btn_exif_aplicar,
                self.btn_exif_prev,
                self.btn_exif_crear,
                self.btn_exif_informe,
            ],
        )

    def _accion_crear_json_similares(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida",
                "Selecciona la carpeta base de Takeout / Google Fotos.",
            )
            return

        if not messagebox.askyesno(
            "Confirmar",
            "Se crearán archivos JSON nuevos a partir de otros similares.\n"
            "¿Continuar?",
        ):
            return

        _safe_call(
            "generar_json_desde_similares",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            simulacion=False,
            botones=[
                self.btn_exif_aplicar,
                self.btn_exif_prev,
                self.btn_exif_crear,
                self.btn_exif_informe,
            ],
        )

    def _accion_informe_sin_json(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida",
                "Selecciona la carpeta base de Takeout / Google Fotos.",
            )
            return

        _safe_call(
            "informe_archivos_sin_json",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_exif_aplicar,
                self.btn_exif_prev,
                self.btn_exif_crear,
                self.btn_exif_informe,
            ],
        )

    # ------------------------------------------------------------------
    # PÁGINA 5: CUARENTENA
    # ------------------------------------------------------------------

    def _pagina_cuarentena(self):
        ttk.Label(
            self.contenedor,
            text="Cuarentena de archivos (mover, restaurar y purgar)",
            style="Header.TLabel",
        ).pack(pady=10)

        frame1 = ttk.Frame(self.contenedor)
        frame1.pack(pady=5)

        ttk.Label(frame1, text="Carpeta base:").pack(side="left", padx=5)
        ttk.Entry(frame1, textvariable=self.ruta_var, width=60).pack(
            side="left", padx=5
        )
        ttk.Button(
            frame1,
            text="Examinar...",
            command=self._seleccionar_carpeta,
        ).pack(side="left", padx=5)

        frame_botones = ttk.Frame(self.contenedor)
        frame_botones.pack(pady=10)

        btn_listar = ttk.Button(
            frame_botones,
            text="Listar cuarentena",
            style="Blue.TButton",
            command=self._accion_listar_cuarentena,
        )
        btn_listar.pack(side="left", padx=5)

        btn_rest_sel = ttk.Button(
            frame_botones,
            text="Restaurar seleccionados",
            style="Green.TButton",
            command=self._accion_restaurar_cuarentena_sel,
        )
        btn_rest_sel.pack(side="left", padx=5)

        btn_rest_todo = ttk.Button(
            frame_botones,
            text="Restaurar TODO",
            style="Orange.TButton",
            command=self._accion_restaurar_cuarentena_todo,
        )
        btn_rest_todo.pack(side="left", padx=5)

        # NUEVOS: purga definitiva
        btn_purg_sel = ttk.Button(
            frame_botones,
            text="Purgar seleccionados",
            style="Red.TButton",
            command=self._accion_purgar_cuarentena_sel,
        )
        btn_purg_sel.pack(side="left", padx=5)

        btn_purg_todo = ttk.Button(
            frame_botones,
            text="Purgar TODO",
            style="Red.TButton",
            command=self._accion_purgar_cuarentena_todo,
        )
        btn_purg_todo.pack(side="left", padx=5)

        self.btn_cuar_listar = btn_listar
        self.btn_cuar_rest_sel = btn_rest_sel
        self.btn_cuar_rest_todo = btn_rest_todo
        self.btn_cuar_purgar_sel = btn_purg_sel
        self.btn_cuar_purgar_todo = btn_purg_todo

        frame_prog = ttk.Frame(self.contenedor)
        frame_prog.pack(fill="x", padx=10, pady=(5, 0))

        self.progreso = ttk.Progressbar(
            frame_prog, mode="determinate", maximum=100
        )
        self.progreso.pack(side="left", fill="x", expand=True)

        ttk.Label(frame_prog, textvariable=self.contador_var).pack(
            side="left", padx=10
        )
        ttk.Label(frame_prog, textvariable=self.tiempo_var).pack(
            side="left", padx=5
        )

        self.salida = scrolledtext.ScrolledText(
            self.contenedor,
            bg="#1E1E1E",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
        )
        self.salida.pack(fill="both", expand=True, padx=10, pady=5)

    def _accion_listar_cuarentena(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        _safe_call(
            "listar_cuarentena",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_cuar_listar,
                self.btn_cuar_rest_sel,
                self.btn_cuar_rest_todo,
            ],
        )

    def _accion_restaurar_cuarentena_sel(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        rutas_seleccionadas = []
        if self.salida is not None:
            try:
                texto_sel = self.salida.get("sel.first", "sel.last")
            except tk.TclError:
                texto_sel = ""

            for linea in texto_sel.splitlines():
                linea = linea.strip()
                if linea:
                    rutas_seleccionadas.append(linea)

        if not rutas_seleccionadas:
            messagebox.showinfo(
                "Sin selección",
                "Selecciona en el listado las rutas de cuarentena que quieras restaurar."
            )
            return

        _safe_call(
            "restaurar_cuarentena",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_cuar_listar,
                self.btn_cuar_rest_sel,
                self.btn_cuar_rest_todo,
            ],
            rutas_seleccionadas=rutas_seleccionadas,
        )

    def _accion_restaurar_cuarentena_todo(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        _safe_call(
            "restaurar_cuarentena",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_cuar_listar,
                self.btn_cuar_rest_sel,
                self.btn_cuar_rest_todo,
            ],
            # rutas_seleccionadas=None → restaurar todo lo que haya
        )

    def _accion_purgar_cuarentena_sel(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        rutas_seleccionadas = []
        if self.salida is not None:
            try:
                texto_sel = self.salida.get("sel.first", "sel.last")
            except tk.TclError:
                texto_sel = ""

            for linea in texto_sel.splitlines():
                linea = linea.strip()
                if linea:
                    rutas_seleccionadas.append(linea)

        if not rutas_seleccionadas:
            messagebox.showinfo(
                "Sin selección",
                "Selecciona en el listado las rutas de cuarentena que quieras purgar."
            )
            return

        _safe_call(
            "purgar_cuarentena",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_cuar_listar,
                self.btn_cuar_rest_sel,
                self.btn_cuar_rest_todo,
                self.btn_cuar_purgar_sel,
                self.btn_cuar_purgar_todo,
            ],
            rutas_seleccionadas=rutas_seleccionadas,
        )

    def _accion_purgar_cuarentena_todo(self):
        ruta = self.ruta_var.get().strip()
        if not ruta:
            messagebox.showwarning(
                "Ruta requerida", "Selecciona una carpeta base."
            )
            return

        _safe_call(
            "purgar_cuarentena",
            ruta_base=ruta,
            salida=self.salida,
            progreso=self.progreso,
            contador_var=self.contador_var,
            tiempo_var=self.tiempo_var,
            botones=[
                self.btn_cuar_listar,
                self.btn_cuar_rest_sel,
                self.btn_cuar_rest_todo,
                self.btn_cuar_purgar_sel,
                self.btn_cuar_purgar_todo,
            ],
            # rutas_seleccionadas=None -> purga todo lo que haya
        )
