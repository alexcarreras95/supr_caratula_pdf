# Suprimir páginas de PDF

App de escritorio (PyQt5 + PyMuPDF) para abrir un PDF, marcar las páginas a eliminar
(por defecto la carátula) y guardar una copia sin ellas. Tema oscuro neón.

- Arrastrá un PDF a la ventana o usá **Elegir archivo…**
- Clic en una miniatura para marcarla/desmarcarla, o escribí rangos como `1, 3-5`
- **Enter** o **Eliminar y guardar…** genera `nombre_sin_paginas.pdf` (el original no se toca)

## Windows

Descargá `SuprimirPaginasPDF.zip` desde [Releases](../../releases), descomprimilo y abrí
`SuprimirPaginasPDF.exe`. No requiere instalar Python.

## Linux

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh            # o ./run.sh archivo.pdf
```

## Generar el .exe desde Linux

```bash
./build_windows.sh  # requiere Docker; usa Wine + PyInstaller
```
