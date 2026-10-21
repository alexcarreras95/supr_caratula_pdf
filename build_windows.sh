#!/usr/bin/env bash
# Genera el .exe de Windows desde Linux usando Docker + Wine (imagen tobix/pywine).
# Resultado: windows/SuprimirPaginasPDF/SuprimirPaginasPDF.exe
# PyMuPDF fijado en 1.25.5: las versiones nuevas usan crealf, que Wine 9.17 no implementa.
set -e
cd "$(dirname "$0")"
rm -rf windows
docker run --rm -v "$PWD":/src:ro -v "$PWD/windows":/out tobix/pywine:3.12 bash -c "
set -e
cp /src/app.py /tmp/app.py && cd /tmp
wine python -m pip install -q --no-warn-script-location PyQt5 pymupdf==1.25.5 pyinstaller==6.10.0
wine pyinstaller --noconfirm --clean --windowed --onedir --noupx --name SuprimirPaginasPDF \
    --distpath /out --workpath /tmp/build app.py
chown -R $(id -u):$(id -g) /out
" 2>&1 | grep -v fixme
echo "Listo: $(pwd)/windows/SuprimirPaginasPDF/SuprimirPaginasPDF.exe"
