from math import hypot
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageOps, ImageTk

CLAVES = ('cabeza', 'pies', 'azotea', 'base')


NOMBRES = ('1. Cabeza de la persona', '2. Pies de la persona',
           '3. Parte superior del edificio', '4. Base del edificio')
COLORES = ('#16b6ac', '#16b6ac', '#ff9f43', '#ff9f43')


class Aplicacion:
    def __init__(self, root):
        self.root = root
        root.title('PixelHeight - Medicion fotografica')
        root.geometry('1180x780')
        root.minsize(850, 650)
        self.imagen = None
        self.puntos = {}
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
        ttk.Button(lateral, text='Limpiar puntos', command=self.limpiar).pack(fill='x', pady=2)
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
        ruta = filedialog.askopenfilename(
            title='Elegir fotografia',
            filetypes=[('Fotografias', '*.jpg *.jpeg *.png'), ('Todos los archivos', '*.*')]
        )
        if not ruta:
            return

        with Image.open(ruta) as original:
            imagen = ImageOps.exif_transpose(original).convert('RGBA')
            fondo = Image.new('RGBA', imagen.size, 'white')
            fondo.alpha_composite(imagen)
            self.imagen = fondo.convert('RGB')

        self.nombre = Path(ruta).name
        self.puntos = {}
        self.arrastre = None
        self.pan = None
        self.objetivo.set(0)
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

    def zoom(self, factor, x, y):
        if self.imagen is None:
            return

        punto = self.coordenada(x, y)
        self.escala *= factor
        self.origen_x = x - punto['x'] * self.escala
        self.origen_y = y - punto['y'] * self.escala
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
        ancho = self.canvas.winfo_width()
        alto = self.canvas.winfo_height()
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
        x = punto['x'] * self.escala + self.origen_x
        y = punto['y'] * self.escala + self.origen_y
        return x, y

    def coordenada(self, x, y):
        return {'x': (x - self.origen_x) / self.escala,
                'y': (y - self.origen_y) / self.escala}

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
                self.arrastre = nombre
                self.objetivo.set(CLAVES.index(nombre))
                return

        punto = self.coordenada(evento.x, evento.y)
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
            self.puntos[self.arrastre] = self.coordenada(evento.x, evento.y)
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
            dx, dy = movimientos[evento.keysym]
            paso = 0.1 if evento.state & 1 else 1
            punto = self.puntos[nombre]
            punto['x'] += dx * paso
            punto['y'] += dy * paso
            self.actualizar()
            return 'break'

    def borrar(self):
        nombre = CLAVES[self.objetivo.get()]
        if nombre in self.puntos:
            del self.puntos[nombre]
            self.actualizar()

    def limpiar(self):
        self.puntos = {}
        self.objetivo.set(0)
        self.actualizar()

    def actualizar(self):
        self.calcular()
        self.dibujar()

    def calcular(self):
        self.resumen.set('Altura estimada: -')
        texto = ''
        if len(self.puntos) == 4 and self.persona.get().strip():
            cabeza = self.puntos['cabeza']
            pies = self.puntos['pies']
            azotea = self.puntos['azotea']
            base = self.puntos['base']
            persona_px = hypot(pies['x'] - cabeza['x'], pies['y'] - cabeza['y'])
            edificio_px = hypot(base['x'] - azotea['x'], base['y'] - azotea['y'])
            altura_persona = float(self.persona.get().replace(',', '.'))
            altura = edificio_px / persona_px * altura_persona
            texto = f'H = ({edificio_px:.3f} / {persona_px:.3f}) x {altura_persona:g} = {altura:.4f} m.'

            if self.real.get().strip():
                altura_real = float(self.real.get().replace(',', '.'))
                error_absoluto = abs(altura - altura_real)
                error_porcentual = 100 * error_absoluto / altura_real
                texto += (
                    f'\nEdificio real: {altura_real:g} m | '
                    f'Error absoluto: {error_absoluto:.2f} m | '
                    f'Error porcentual: {error_porcentual:.2f}%'
                )
            self.resumen.set(f'Altura estimada: {altura:.2f} m  ({altura * 100:.0f} cm)')

        self.salida.configure(state='normal')
        self.salida.delete('1.0', 'end')
        self.salida.insert('1.0', texto)
        self.salida.configure(state='disabled')


if __name__ == '__main__':
    raiz = tk.Tk()
    app = Aplicacion(raiz)
    raiz.mainloop()
