"""Suprimir carátula PDF: abre un PDF, marca las páginas a eliminar y guarda una copia."""

import os
import sys

# Usar el selector de archivos nativo del escritorio (GNOME/KDE) vía xdg-desktop-portal
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")

import pymupdf
from PyQt5.QtCore import QEvent, QPoint, QRect, QSettings, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QKeySequence, QPalette, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QShortcut,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

THUMB_SIZE = 160

# Paleta neón cyberpunk
BG = "#0d0b1a"
SURFACE = "#16122b"
BORDER = "#3a2d6b"
TEXT = "#e6e1ff"
MUTED = "#8a80b8"
PURPLE = "#b026ff"
CYAN = "#00f0ff"
PINK = "#ff2e88"

STYLE = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-size: 13px; }}
QStatusBar {{ background: {SURFACE}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QLabel {{ background: transparent; }}
QPushButton {{
    background: {SURFACE}; color: {CYAN};
    border: 1px solid {CYAN}; border-radius: 6px; padding: 6px 14px;
}}
QPushButton:hover {{ background: #1f2a45; }}
QPushButton:pressed {{ background: {CYAN}; color: {BG}; }}
QPushButton:disabled {{ color: {MUTED}; border-color: {BORDER}; }}
QPushButton#saveBtn {{
    background: {PINK}; color: white; font-weight: bold; border: none;
}}
QPushButton#saveBtn:hover {{ background: #ff5aa3; }}
QPushButton#saveBtn:pressed {{ background: #d61f6f; }}
QPushButton#browseBtn {{
    background: {PURPLE}; color: white; font-weight: bold; border: none;
    padding: 10px 28px; font-size: 14px;
}}
QPushButton#browseBtn:hover {{ background: #c255ff; }}
QLineEdit {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 5px 8px; selection-background-color: {PURPLE};
}}
QLineEdit:focus {{ border-color: {CYAN}; }}
QListWidget {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {PURPLE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QToolTip {{ background: {SURFACE}; color: {CYAN}; border: 1px solid {CYAN}; }}
QMessageBox QPushButton {{ min-width: 70px; }}
#dropZone {{ border: 2px dashed {PURPLE}; border-radius: 16px; background: {SURFACE}; }}
#dropZone[active="true"] {{ border-color: {CYAN}; background: #1a2140; }}
#dropTitle {{ font-size: 22px; font-weight: 600; color: {CYAN}; }}
#dropHint {{ color: {MUTED}; }}
"""


def neon_glow(widget, color, radius=22):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setColor(QColor(color))
    effect.setBlurRadius(radius)
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)


def apply_theme(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, color in (
        (QPalette.Window, BG), (QPalette.Base, SURFACE), (QPalette.AlternateBase, BG),
        (QPalette.WindowText, TEXT), (QPalette.Text, TEXT), (QPalette.ButtonText, TEXT),
        (QPalette.Button, SURFACE), (QPalette.Highlight, PURPLE), (QPalette.HighlightedText, "white"),
        (QPalette.ToolTipBase, SURFACE), (QPalette.ToolTipText, CYAN), (QPalette.Mid, BORDER),
    ):
        pal.setColor(role, QColor(color))
    app.setPalette(pal)
    app.setStyleSheet(STYLE)


def parse_ranges(text, total):
    """Convierte '1, 3-5' en un conjunto de índices base 0. Lanza ValueError si es inválido."""
    pages = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            start, end = (int(x) for x in part.split("-", 1))
        else:
            start = end = int(part)
        if start < 1 or end > total or start > end:
            raise ValueError(f"Rango fuera de límites: {part} (el PDF tiene {total} páginas)")
        pages.update(range(start - 1, end))
    return pages


def format_ranges(indices):
    """Convierte índices base 0 en texto tipo '1, 3-5'."""
    nums = sorted(i + 1 for i in indices)
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ", ".join(parts)


def pdf_from_drop(event):
    """Devuelve la ruta del primer PDF arrastrado, o None."""
    for url in event.mimeData().urls():
        if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
            return url.toLocalFile()
    return None


class DropZone(QFrame):
    """Pantalla inicial: zona para soltar un PDF o elegirlo con el selector."""

    browse = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")

        icon = QLabel()
        icon.setPixmap(QIcon.fromTheme(
            "application-pdf", self.style().standardIcon(QStyle.SP_FileIcon)).pixmap(96, 96))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("Arrastrá un PDF aquí")
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignCenter)

        hint = QLabel("o")
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignCenter)

        btn = QPushButton(QIcon.fromTheme("document-open"), "Elegir archivo…")
        btn.setObjectName("browseBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.browse)
        neon_glow(btn, PURPLE)

        self.recent_label = QLabel()
        self.recent_label.setObjectName("dropHint")
        self.recent_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(btn, 0, Qt.AlignCenter)
        layout.addSpacing(12)
        layout.addWidget(self.recent_label)
        layout.addStretch()

    def set_active(self, active):
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class PageDelegate(QStyledItemDelegate):
    """Dibuja cada página con su casilla en la esquina; un clic la marca/desmarca."""

    PAD = 10
    LABEL_H = 24
    DELETE_COLOR = QColor(PINK)

    def sizeHint(self, option, index):
        return QSize(THUMB_SIZE + 2 * self.PAD, THUMB_SIZE + 2 * self.PAD + self.LABEL_H)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(painter.Antialiasing)
        rect = option.rect
        pm = index.data(Qt.UserRole)
        checked = index.data(Qt.CheckStateRole) == Qt.Checked
        hover = option.state & QStyle.State_MouseOver

        # Página centrada en el cuadro de miniatura
        x = rect.x() + (rect.width() - pm.width()) // 2
        y = rect.y() + self.PAD + (THUMB_SIZE - pm.height()) // 2
        page = QRect(x, y, pm.width(), pm.height())

        accent = QColor(PINK if checked else CYAN if hover else PURPLE)

        # Halo neón alrededor de la página
        if checked or hover:
            for i, alpha in enumerate((70, 40, 18)):
                glow = QColor(accent)
                glow.setAlpha(alpha)
                painter.setPen(QPen(glow, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(page.adjusted(-2 - 2 * i, -2 - 2 * i, 2 + 2 * i, 2 + 2 * i), 3, 3)
        painter.drawPixmap(page, pm)
        if checked:
            painter.fillRect(page, QColor(255, 46, 136, 70))
        painter.setPen(QPen(accent, 2 if (checked or hover) else 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(page)

        # Casilla en la esquina superior izquierda de la página
        box = QRect(page.left() + 6, page.top() + 6, 20, 20)
        painter.setPen(QPen(QColor(PINK if checked else PURPLE), 2))
        painter.setBrush(QColor(PINK if checked else BG))
        painter.drawRoundedRect(box, 4, 4)
        if checked:
            painter.setPen(QPen(Qt.white, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPolyline(box.topLeft() + QPoint(5, 10), box.topLeft() + QPoint(9, 14),
                                 box.topLeft() + QPoint(15, 6))

        # Etiqueta debajo
        label = QRect(rect.x(), rect.y() + self.PAD + THUMB_SIZE + 4, rect.width(), self.LABEL_H)
        font = QFont(option.font)
        if checked:
            font.setBold(True)
            painter.setPen(self.DELETE_COLOR)
        else:
            painter.setPen(option.palette.text().color())
        painter.setFont(font)
        text = index.data(Qt.DisplayRole) + (" · eliminar" if checked else "")
        painter.drawText(label, Qt.AlignCenter, text)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            checked = index.data(Qt.CheckStateRole) == Qt.Checked
            model.setData(index, Qt.Unchecked if checked else Qt.Checked, Qt.CheckStateRole)
            return True
        return event.type() == QEvent.MouseButtonDblClick


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Suprimir páginas de PDF")
        self.resize(900, 650)
        self.doc = None
        self.path = None
        self.settings = QSettings("supr_caratula_pdf", "app")
        self.setAcceptDrops(True)

        self.drop_zone = DropZone()
        self.drop_zone.browse.connect(self.open_pdf)
        last_dir = self.last_dir()
        if last_dir != os.path.expanduser("~"):
            self.drop_zone.recent_label.setText(
                "Última carpeta: " + last_dir.replace(os.path.expanduser("~"), "~", 1))

        self.open_btn = QPushButton(QIcon.fromTheme("document-open"), "Abrir otro PDF…")
        self.open_btn.clicked.connect(self.open_pdf)
        self.file_label = QLabel("Ningún archivo abierto")

        top = QHBoxLayout()
        top.addWidget(self.open_btn)
        top.addWidget(self.file_label, 1)

        self.pages = QListWidget()
        self.pages.setViewMode(QListWidget.IconMode)
        self.pages.setItemDelegate(PageDelegate(self.pages))
        self.pages.setSelectionMode(QListWidget.NoSelection)
        self.pages.setMouseTracking(True)
        self.pages.setUniformItemSizes(True)
        self.pages.setResizeMode(QListWidget.Adjust)
        self.pages.setMovement(QListWidget.Static)
        self.pages.setSpacing(8)
        self.pages.itemChanged.connect(self.sync_text_from_checks)

        self.ranges_edit = QLineEdit()
        self.ranges_edit.setPlaceholderText("Páginas a eliminar, ej: 1, 3-5")
        self.ranges_edit.editingFinished.connect(self.sync_checks_from_text)

        self.first_btn = QPushButton("Marcar solo la 1ª página")
        self.first_btn.clicked.connect(lambda: self.set_marked({0}))
        self.clear_btn = QPushButton("Desmarcar todo")
        self.clear_btn.clicked.connect(lambda: self.set_marked(set()))
        self.save_btn = QPushButton(QIcon.fromTheme("edit-delete"), "Eliminar y guardar…  ⏎")
        self.save_btn.setToolTip("Atajo: Enter")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setObjectName("saveBtn")
        neon_glow(self.save_btn, PINK)
        self.save_btn.clicked.connect(self.save_pdf)
        # Enter (normal y del teclado numérico) dispara el guardado, también desde el campo de rangos
        for key in (Qt.Key_Return, Qt.Key_Enter):
            QShortcut(QKeySequence(key), self, activated=self.save_shortcut)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Eliminar:"))
        bottom.addWidget(self.ranges_edit, 1)
        bottom.addWidget(self.first_btn)
        bottom.addWidget(self.clear_btn)
        bottom.addWidget(self.save_btn)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.pages, 1)
        layout.addLayout(bottom)
        editor = QWidget()
        editor.setLayout(layout)

        start = QWidget()
        start_layout = QVBoxLayout(start)
        start_layout.setContentsMargins(24, 24, 24, 24)
        start_layout.addWidget(self.drop_zone)

        self.stack = QStackedWidget()
        self.stack.addWidget(start)
        self.stack.addWidget(editor)
        self.setCentralWidget(self.stack)

        self.statusBar().showMessage("Abrí un PDF para empezar.")

    def last_dir(self):
        d = self.settings.value("last_dir", "")
        return d if d and os.path.isdir(d) else os.path.expanduser("~")

    def dragEnterEvent(self, event):
        if pdf_from_drop(event):
            event.acceptProposedAction()
            self.drop_zone.set_active(True)

    def dragLeaveEvent(self, event):
        self.drop_zone.set_active(False)

    def dropEvent(self, event):
        self.drop_zone.set_active(False)
        path = pdf_from_drop(event)
        if path:
            self.open_pdf(path)

    def open_pdf(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir PDF", self.last_dir(), "Documentos PDF (*.pdf)")
            if not path:
                return
        try:
            doc = pymupdf.open(path)
            if doc.needs_pass:
                raise ValueError("El PDF está protegido con contraseña.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el PDF:\n{e}")
            return

        if self.doc:
            self.doc.close()
        self.doc, self.path = doc, path
        self.settings.setValue("last_dir", os.path.dirname(path))
        self.file_label.setText(f"<b>{os.path.basename(path)}</b> — {doc.page_count} páginas")
        self.stack.setCurrentIndex(1)
        self.load_thumbnails()
        self.set_marked({0})  # caso típico: quitar la carátula

    def load_thumbnails(self):
        self.pages.blockSignals(True)
        self.pages.clear()
        for i, page in enumerate(self.doc):
            zoom = THUMB_SIZE / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
            item = QListWidgetItem(f"Pág. {i + 1}")
            item.setData(Qt.UserRole, QPixmap.fromImage(img))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.pages.addItem(item)
            if i % 10 == 0:
                QApplication.processEvents()
        self.pages.blockSignals(False)

    def marked(self):
        return {i for i in range(self.pages.count()) if self.pages.item(i).checkState() == Qt.Checked}

    def set_marked(self, indices):
        self.pages.blockSignals(True)
        for i in range(self.pages.count()):
            self.pages.item(i).setCheckState(Qt.Checked if i in indices else Qt.Unchecked)
        self.pages.blockSignals(False)
        self.sync_text_from_checks()

    def save_shortcut(self):
        if self.doc and self.stack.currentIndex() == 1:
            self.save_pdf()

    def sync_text_from_checks(self, *_):
        marked = self.marked()
        self.ranges_edit.setText(format_ranges(marked))
        self.statusBar().showMessage(f"{len(marked)} página(s) marcadas para eliminar")

    def sync_checks_from_text(self):
        if not self.doc:
            return False
        try:
            self.set_marked(parse_ranges(self.ranges_edit.text(), self.doc.page_count))
            return True
        except ValueError as e:
            QMessageBox.warning(self, "Rango inválido", str(e) if "límites" in str(e) else
                                "Usá números y rangos separados por coma, ej: 1, 3-5")
            return False

    def save_pdf(self):
        if not self.sync_checks_from_text():
            return
        marked = self.marked()
        if not marked:
            QMessageBox.information(self, "Nada que eliminar", "No hay páginas marcadas.")
            return
        if len(marked) == self.doc.page_count:
            QMessageBox.warning(self, "Error", "No se pueden eliminar todas las páginas.")
            return

        base, _ = os.path.splitext(self.path)
        out, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", f"{base}_sin_paginas.pdf", "Documentos PDF (*.pdf)")
        if not out:
            return
        if not out.lower().endswith(".pdf"):
            out += ".pdf"

        try:
            # Se reabre el archivo para no tocar el original ni las miniaturas
            new_doc = pymupdf.open(self.path)
            new_doc.delete_pages(sorted(marked))
            new_doc.save(out, garbage=3, deflate=True)
            new_doc.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return

        QMessageBox.information(
            self, "Listo",
            f"Se eliminaron {len(marked)} página(s).\nGuardado en:\n{out}")


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.show()
    if len(sys.argv) > 1:
        win.open_pdf(sys.argv[1])
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
