"""Generador de la carta responsiva en PDF (WP5).

- `estilos.py`   colores, fuentes y estilos de parrafo (tokens de marca)
- `plantilla.py` estructura del documento a partir de datos ya resueltos
- `responsiva.py` reune los datos de la base, genera el archivo y devuelve su sha256

El PDF se arma **siempre a partir de los datos**. Nunca se guarda HTML
renderizado en el modelo: la maqueta guardaba `loan.responsivaHtml`, que es a la
vez fuga de presentacion al modelo de datos y superficie de XSS al reimportar un
respaldo (§10.9 del plan).
"""
