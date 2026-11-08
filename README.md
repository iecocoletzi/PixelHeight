# PixelHeight

Herramienta de escritorio en Python para estimar la altura de edificios mediante proporciones en píxeles, utilizando una fotografía y una persona de altura conocida como referencia.

## Requisitos

- Python 3.12 con Tkinter.
- Pillow.
- Una fotografía JPG o PNG con el edificio completo y una persona de altura conocida, aproximadamente en el mismo plano de profundidad que la fachada.

## Instalación y ejecución

Instala Pillow:

    py -3.12 -m pip install "Pillow>=12,<14"

Ejecuta la aplicación:

    py -3.12 rectoria_foto.py

## Uso

Carga la fotografía, introduce la altura de la persona y marca los cuatro puntos: cabeza, pies, parte superior y base del edificio.

Opcionalmente, introduce la altura real del edificio para comparar el resultado y calcular el error.
