import warnings
from math import hypot, isfinite
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageOps, ImageTk

CLAVES = ('cabeza', 'pies', 'azotea', 'base')


class DatosInvalidos(ValueError):
    pass

def validar_puntos(puntos, ancho, alto):
    puntos_validos = {}
    for nombre in CLAVES:
        punto = puntos.get(nombre)
        if punto is None:
            continue
        try:
            x = float(punto['x'])
            y = float(punto['y'])
        except (ValueError, TypeError, KeyError, OverflowError):
            raise DatosInvalidos('Coordenadas invalidas.') from None
        if not isfinite(x) or not isfinite(y):
            raise DatosInvalidos('Coordenadas invalidas.')
        if not (0 <= x <= ancho - 1 and 0 <= y <= alto - 1):
            raise DatosInvalidos('Hay un punto fuera de la fotografia.')
        puntos_validos[nombre] = {'x': x, 'y': y}
    return puntos_validos


def foto(puntos, ancho, alto, persona_m):
    puntos = validar_puntos(puntos, ancho, alto)
    if len(puntos) != 4:
        raise DatosInvalidos('Marca cabeza, pies, azotea y base para calcular.')

    medidas = []
    for arriba, abajo in [('cabeza', 'pies'), ('azotea', 'base')]:
        dx = puntos[abajo]['x'] - puntos[arriba]['x']
        dy = puntos[abajo]['y'] - puntos[arriba]['y']
        if dy <= 0:
            raise DatosInvalidos('Los extremos superiores deben quedar por encima de los inferiores.')
        medidas.append(hypot(dx, dy))

    persona_px, edificio_px = medidas
    if persona_px < 40:
        raise DatosInvalidos('La persona mide menos de 40 pixeles en la foto. Usa una foto con mas detalle.')

    altura = edificio_px / persona_px * persona_m
    formula = f'H = ({edificio_px:.3f} / {persona_px:.3f}) x {persona_m:g} = {altura:.4f} m.'
    return altura, formula


NOMBRES = ('1. Cabeza de la persona', '2. Pies de la persona',
           '3. Parte superior del edificio', '4. Base del edificio')
COLORES = ('#16b6ac', '#16b6ac', '#ff9f43', '#ff9f43')


def a_imagen(x, y, escala, origen_x, origen_y):
    return {'x': (x - origen_x) / escala, 'y': (y - origen_y) / escala}


def a_pantalla(punto, escala, origen_x, origen_y):
    x = punto['x'] * escala + origen_x
    y = punto['y'] * escala + origen_y
    return x, y


def zoom_anclado(x, y, escala_actual, escala_nueva, origen_x, origen_y):
    punto = a_imagen(x, y, escala_actual, origen_x, origen_y)
    nuevo_origen_x = x - punto['x'] * escala_nueva
    nuevo_origen_y = y - punto['y'] * escala_nueva
    return nuevo_origen_x, nuevo_origen_y


def numero(texto):
    try:
        altura = float(texto.strip().replace(',', '.'))
        if not isfinite(altura) or altura <= 0:
            raise ValueError
        return altura
    except (ValueError, OverflowError):
        raise DatosInvalidos('Introduce una altura valida mayor que cero, en metros.') from None


def cargar(ruta):
    if Path(ruta).stat().st_size > 40*1024*1024:
        raise DatosInvalidos('Selecciona una imagen de hasta 40 MB.')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(ruta) as original:
            if original.format not in ('JPEG', 'PNG'):
                raise DatosInvalidos('Usa JPG o PNG; convierte HEIC a JPEG.')
            if original.width*original.height > 60_000_000 or min(original.size) < 2:
                raise DatosInvalidos('Resolucion admitida: de 2 pixeles por lado a 60 megapixeles.')
            rgba = ImageOps.exif_transpose(original).convert('RGBA')
            fondo = Image.new('RGBA', rgba.size, 'white')
            fondo.alpha_composite(rgba)
            return fondo.convert('RGB')


class Aplicacion:
    def __init__(self, root):
        self.root = root
        root.title('PixelHeight - Medicion fotografica')
        root.geometry('1180x780')
        root.minsize(850, 650)
        self.imagen = None
        self.puntos = {}
        self.historial = []
        self.escala = 1.0
        self.origen_x = 0.0
        self.origen_y = 0.0
        self.arrastre = None
        self.pan = None
        self.persona = tk.StringVar(value='1.73')
        self.real = tk.StringVar(value='45')
        self.objetivo = tk.IntVar(value=0)
        self.estado = tk.StringVar(value='Elige una foto para comenzar.')
        self.resumen = tk.StringVar(value='Altura estimada: -')
        barra = ttk.Frame(root, padding=8)
        barra.pack(fill='x')
        ttk.Button(barra, text='Elegir fotografia', command=self.abrir).pack(side='left')
        datos = ttk.Frame(root, padding=(8, 0, 8, 8))
        datos.pack(fill='x')
        ttk.Label(datos, text='Persona (m):').pack(side='left')
        ttk.Entry(datos, textvariable=self.persona, width=9).pack(side='left', padx=(5, 18))
        ttk.Label(datos, text='Altura real del edificio (m):').pack(side='left')
        ttk.Entry(datos, textvariable=self.real, width=10).pack(side='left', padx=5)
        principal = ttk.Frame(root)
        principal.pack(fill='both', expand=True)
        lateral = ttk.Frame(principal, padding=8, width=270)
        lateral.pack(side='left', fill='y')
        ttk.Label(lateral, text='Selecciona el punto y haz clic:').pack(anchor='w')
        for i, nombre in enumerate(NOMBRES):
            ttk.Radiobutton(lateral, text=nombre, variable=self.objetivo, value=i).pack(anchor='w', pady=4)
        ttk.Separator(lateral).pack(fill='x', pady=8)
        for texto, comando in [('Ajustar foto', self.ajustar),
                               ('Acercar +', lambda: self.zoom(1.25)),
                               ('Alejar -', lambda: self.zoom(0.8)),
                               ('Borrar punto seleccionado', self.borrar),
                               ('Deshacer', self.deshacer), ('Limpiar puntos', self.limpiar)]:
            ttk.Button(lateral, text=texto, command=comando).pack(fill='x', pady=2)
        self.canvas = tk.Canvas(principal, bg='#22262b', highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        ttk.Label(root, textvariable=self.resumen, font=('TkDefaultFont', 14, 'bold'), padding=8).pack(anchor='w')
        self.salida = ScrolledText(root, height=7, wrap='word', font=('TkDefaultFont', 10))
        self.salida.pack(fill='x', padx=8)
        self.salida.configure(state='disabled')
        ttk.Label(root, textvariable=self.estado, padding=8).pack(anchor='w')
        self.canvas.bind('<Configure>', lambda e: self.dibujar())
        self.canvas.bind('<Button-1>', self.pulsar)
        self.canvas.bind('<B1-Motion>', self.mover_punto)
        self.canvas.bind('<ButtonRelease-1>', lambda e: setattr(self, 'arrastre', None))
        self.canvas.bind('<Button-3>', self.iniciar_pan)
        self.canvas.bind('<B3-Motion>', self.mover_pan)
        self.canvas.bind('<ButtonRelease-3>', lambda e: setattr(self, 'pan', None))
        self.canvas.bind('<MouseWheel>', self.rueda)
        self.canvas.bind('<Button-4>', lambda e: self.zoom(1.2, e.x, e.y))
        self.canvas.bind('<Button-5>', lambda e: self.zoom(1/1.2, e.x, e.y))
        self.canvas.bind('<KeyPress>', self.tecla)
        for campo in (self.persona, self.real):
            campo.trace_add('write', lambda *_: self.calcular())

    def abrir(self):
        ruta = filedialog.askopenfilename(title='Elegir fotografia', filetypes=[('Fotografias', '*.jpg *.jpeg *.png'), ('Todos los archivos', '*.*')])
        if not ruta:
            return
        try:
            imagen = cargar(ruta)
        except (ValueError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            messagebox.showerror('No se pudo abrir la fotografia', str(exc))
            return
        self.establecer_imagen(imagen, Path(ruta).name)

    def establecer_imagen(self, imagen, nombre):
        self.imagen = imagen
        self.puntos = {}
        self.historial = []
        self.arrastre = None
        self.pan = None
        self.objetivo.set(0)
        self.nombre = nombre
        self.ajustar()
        self.calcular()

    def ajustar(self):
        if self.imagen is None:
            return
        self.root.update_idletasks()
        ancho = self.canvas.winfo_width()
        alto = self.canvas.winfo_height()
        self.escala = min((ancho - 20) / self.imagen.width,
                          (alto - 20) / self.imagen.height)
        self.origen_x = (ancho - self.imagen.width * self.escala) / 2
        self.origen_y = (alto - self.imagen.height * self.escala) / 2
        self.dibujar()

    def zoom(self, factor, x=None, y=None):
        if self.imagen is None:
            return
        if x is None:
            x = self.canvas.winfo_width() / 2
        if y is None:
            y = self.canvas.winfo_height() / 2

        escala_nueva = max(0.01, min(32.0, self.escala * factor))
        self.origen_x, self.origen_y = zoom_anclado(
            x, y, self.escala, escala_nueva, self.origen_x, self.origen_y
        )
        self.escala = escala_nueva
        self.dibujar()

    def rueda(self, evento):
        if evento.delta > 0:
            self.zoom(1.2, evento.x, evento.y)
        elif evento.delta < 0:
            self.zoom(1 / 1.2, evento.x, evento.y)
        return 'break'

    def dibujar(self):
        self.canvas.delete('all')
        if self.imagen is None:
            return
        ancho = max(1, self.canvas.winfo_width())
        alto = max(1, self.canvas.winfo_height())
        escala_inversa = 1 / self.escala
        transformacion = (
            escala_inversa, 0, -self.origen_x * escala_inversa,
            0, escala_inversa, -self.origen_y * escala_inversa
        )
        vista = self.imagen.transform(
            (ancho, alto), Image.Transform.AFFINE, transformacion,
            Image.Resampling.BILINEAR, fillcolor='#22262b'
        )
        self.tk_imagen = ImageTk.PhotoImage(vista, master=self.root)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_imagen)
        for a, b, color in [('cabeza', 'pies', COLORES[0]), ('azotea', 'base', COLORES[2])]:
            if a in self.puntos and b in self.puntos:
                self.canvas.create_line(*self.pantalla(self.puntos[a]), *self.pantalla(self.puntos[b]), fill=color, width=2)
        for i, k in enumerate(CLAVES):
            if k in self.puntos:
                x, y = self.pantalla(self.puntos[k])
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=COLORES[i], outline='white', width=2)
                self.canvas.create_text(x+10, y-10, text=str(i+1), fill='white', anchor='sw', font=('TkDefaultFont', 12, 'bold'))
        self.estado.set(f'{self.nombre} | {self.imagen.width} x {self.imagen.height} px | Zoom {self.escala*100:.0f}% | {len(self.puntos)}/4 puntos')

    def pantalla(self, punto):
        return a_pantalla(punto, self.escala, self.origen_x, self.origen_y)

    def coordenada(self, x, y, limitar=False):
        punto = a_imagen(x, y, self.escala, self.origen_x, self.origen_y)
        if limitar:
            punto['x'] = max(0, min(self.imagen.width - 1, punto['x']))
            punto['y'] = max(0, min(self.imagen.height - 1, punto['y']))
        return punto

    def recordar(self):
        copia = {nombre: punto.copy() for nombre, punto in self.puntos.items()}
        self.historial.append(copia)
        self.historial = self.historial[-80:]

    def pulsar(self, evento):
        self.canvas.focus_set()
        if self.imagen is None:
            return

        cercanos = []
        for nombre, punto in self.puntos.items():
            x, y = self.pantalla(punto)
            distancia = hypot(evento.x - x, evento.y - y)
            cercanos.append((distancia, nombre))

        if cercanos:
            distancia, nombre = min(cercanos)
            if distancia <= 10:
                self.recordar()
                self.arrastre = nombre
                self.objetivo.set(CLAVES.index(nombre))
                return

        punto = self.coordenada(evento.x, evento.y)
        if not (0 <= punto['x'] <= self.imagen.width - 1 and
                0 <= punto['y'] <= self.imagen.height - 1):
            return

        self.recordar()
        indice = self.objetivo.get()
        nombre = CLAVES[indice]
        self.puntos[nombre] = punto
        self.arrastre = nombre

        for paso in range(1, 5):
            siguiente = (indice + paso) % 4
            if CLAVES[siguiente] not in self.puntos:
                self.objetivo.set(siguiente)
                break
        self.actualizar()

    def mover_punto(self, evento):
        if self.arrastre:
            self.puntos[self.arrastre] = self.coordenada(evento.x, evento.y, limitar=True)
            self.actualizar()

    def iniciar_pan(self, evento):
        self.pan = (evento.x, evento.y, self.origen_x, self.origen_y)

    def mover_pan(self, evento):
        if self.pan:
            inicio_x, inicio_y, origen_x, origen_y = self.pan
            self.origen_x = origen_x + evento.x - inicio_x
            self.origen_y = origen_y + evento.y - inicio_y
            self.dibujar()

    def tecla(self, evento):
        if evento.keysym == 'Delete':
            self.borrar()
            return 'break'

        movimientos = {
            'Left': (-1, 0),
            'Right': (1, 0),
            'Up': (0, -1),
            'Down': (0, 1)
        }
        nombre = CLAVES[self.objetivo.get()]
        if evento.keysym in movimientos and nombre in self.puntos:
            self.recordar()
            dx, dy = movimientos[evento.keysym]
            paso = 0.1 if evento.state & 1 else 1
            punto = self.puntos[nombre]
            punto['x'] = max(0, min(self.imagen.width - 1, punto['x'] + dx * paso))
            punto['y'] = max(0, min(self.imagen.height - 1, punto['y'] + dy * paso))
            self.actualizar()
            return 'break'

    def borrar(self):
        nombre = CLAVES[self.objetivo.get()]
        if nombre in self.puntos:
            self.recordar()
            del self.puntos[nombre]
            self.actualizar()

    def limpiar(self):
        self.recordar()
        self.puntos = {}
        self.objetivo.set(0)
        self.actualizar()

    def deshacer(self):
        if self.historial:
            self.puntos = self.historial.pop()
            self.actualizar()

    def actualizar(self):
        self.calcular()
        self.dibujar()

    def calcular(self):
        self.resumen.set('Altura estimada: -')
        try:
            if self.imagen is None:
                raise DatosInvalidos('Elige una fotografia JPG o PNG.')
            altura_persona = numero(self.persona.get())
            altura_real = None
            if self.real.get().strip():
                altura_real = numero(self.real.get())

            altura, formula = foto(self.puntos, *self.imagen.size, altura_persona)
            lineas = [formula]
            if altura_real is not None:
                error_absoluto = abs(altura - altura_real)
                error_porcentual = 100 * error_absoluto / altura_real
                lineas.append(
                    f'Edificio real: {altura_real:g} m | '
                    f'Error absoluto: {error_absoluto:.2f} m | '
                    f'Error porcentual: {error_porcentual:.2f}%'
                )
            texto = '\n'.join(lineas)
            self.resumen.set(f'Altura estimada: {altura:.2f} m  ({altura * 100:.0f} cm)')
        except DatosInvalidos as exc:
            texto = str(exc)
        self.salida.configure(state='normal')
        self.salida.delete('1.0', 'end')
        self.salida.insert('1.0', texto)
        self.salida.configure(state='disabled')


if __name__ == '__main__':
    raiz = tk.Tk()
    app = Aplicacion(raiz)
    raiz.mainloop()
