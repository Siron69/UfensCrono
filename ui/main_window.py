from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from utils.paths import get_resource_path

from ui.atleti.lista import AtletiLista
from ui.eventi.lista import EventiLista
from ui.gare.lista import GareLista
from ui.gare.iscrizioni import IscrizioniPanel
from ui.cronometro.operatore import CronometroPanel
from ui.classifiche.panel import ClassifichePanel

_NAV_STYLE_ACTIVE = """
    QPushButton {
        background-color: #2563eb; color: white;
        border: none; padding: 10px 16px;
        text-align: left; font-size: 14px; border-radius: 6px;
    }
"""
_NAV_STYLE_NORMAL = """
    QPushButton {
        background-color: transparent; color: #1e293b;
        border: none; padding: 10px 16px;
        text-align: left; font-size: 14px; border-radius: 6px;
    }
    QPushButton:hover { background-color: #e2e8f0; }
    QPushButton:disabled { color: #94a3b8; }
"""

_IDX_ATLETI      = 0
_IDX_EVENTI      = 1
_IDX_GARE        = 2
_IDX_ISCRIZIONI  = 3
_IDX_CRONOMETRO  = 4
_IDX_CLASSIFICHE = 5


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UfensCrono")
        self.setMinimumSize(1100, 700)
        self._nav_buttons: list[tuple] = []
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background-color: #f8fafc; border-right: 1px solid #e2e8f0;")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 20, 12, 20)
        sb.setSpacing(4)

        # ── Logo sidebar ──────────────────────────────────────────────────
        logo_pix = QPixmap(get_resource_path('ui/media/logoUfens.png'))
        if not logo_pix.isNull():
            logo_img = QLabel()
            logo_img.setPixmap(
                logo_pix.scaled(
                    120, 64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            logo_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_img.setStyleSheet("padding-bottom: 4px;")
            sb.addWidget(logo_img)

        logo_text = QLabel("UfensCrono")
        logo_text.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1e293b;"
            "padding: 0 4px 16px 4px;"
        )
        logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb.addWidget(logo_text)

        # ── Stack ────────────────────────────────────────────────────────
        self.stack = QStackedWidget()

        # 0 – Atleti
        self._atleti = AtletiLista()
        self.stack.addWidget(self._atleti)

        # 1 – Eventi
        self._eventi = EventiLista()
        self._eventi.apri_gare.connect(self._on_apri_gare)
        self.stack.addWidget(self._eventi)

        # 2 – Gare
        self._gare = GareLista()
        self._gare.apri_iscrizioni.connect(self._on_apri_iscrizioni)
        self._gare.apri_cronometro.connect(self._on_apri_cronometro)
        self._gare.apri_classifica.connect(self._on_apri_classifica)
        self._gare.indietro.connect(lambda: self._navigate(_IDX_EVENTI))
        self.stack.addWidget(self._gare)

        # 3 – Iscrizioni
        self._iscrizioni = IscrizioniPanel()
        self._iscrizioni.indietro.connect(lambda: self._navigate(_IDX_GARE))
        self.stack.addWidget(self._iscrizioni)

        # 4 – Cronometro
        self._cronometro = CronometroPanel()
        self._cronometro.indietro.connect(self._on_cronometro_indietro)
        self.stack.addWidget(self._cronometro)

        # 5 – Classifiche
        self._classifiche = ClassifichePanel()
        self._classifiche.indietro.connect(lambda: self._navigate(_IDX_GARE))
        self.stack.addWidget(self._classifiche)

        nav_items = [
            ("Atleti",      _IDX_ATLETI,      True),
            ("Eventi",      _IDX_EVENTI,      True),
            ("Gare",        _IDX_GARE,        True),
            ("Cronometro",  _IDX_CRONOMETRO,  True),
            ("Classifiche", _IDX_CLASSIFICHE, True),
        ]
        for label, idx, ready in nav_items:
            btn = QPushButton(label)
            btn.setEnabled(ready)
            if ready:
                btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            btn.setStyleSheet(_NAV_STYLE_NORMAL)
            sb.addWidget(btn)
            self._nav_buttons.append((btn, idx))

        sb.addStretch()
        root.addWidget(sidebar)
        root.addWidget(self.stack, stretch=1)

        self._navigate(_IDX_ATLETI)

    def _placeholder(self, name: str) -> QWidget:
        w = QWidget()
        lbl = QLabel(f"<i>{name} — in sviluppo</i>")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #94a3b8; font-size: 16px;")
        lay = QVBoxLayout(w)
        lay.addWidget(lbl)
        return w

    def _navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for btn, idx in self._nav_buttons:
            if idx == index:
                btn.setStyleSheet(_NAV_STYLE_ACTIVE)
            elif btn.isEnabled():
                btn.setStyleSheet(_NAV_STYLE_NORMAL)

    def _on_apri_gare(self, evento_id: int) -> None:
        self._gare.set_evento(evento_id)
        self._navigate(_IDX_GARE)

    def _on_apri_iscrizioni(self, gara_id: int) -> None:
        self._iscrizioni.set_gara(gara_id)
        self._navigate(_IDX_ISCRIZIONI)

    def _on_apri_cronometro(self, gara_id: int) -> None:
        self._cronometro.set_gara(gara_id)
        self._navigate(_IDX_CRONOMETRO)

    def _on_apri_classifica(self, gara_id: int) -> None:
        self._classifiche.set_gara(gara_id)
        self._navigate(_IDX_CLASSIFICHE)

    def _on_cronometro_indietro(self) -> None:
        self._navigate(_IDX_GARE)
        self._gare.refresh()
