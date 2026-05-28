from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame,
)
from PyQt6.QtCore import Qt

from ui.atleti.lista import AtletiLista

_NAV_ITEMS = [
    ("Atleti", 0),
    ("Eventi", None),
    ("Gare", None),
    ("Cronometro", None),
    ("Classifiche", None),
]

_NAV_STYLE_ACTIVE = """
    QPushButton {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 10px 16px;
        text-align: left;
        font-size: 14px;
        border-radius: 6px;
    }
"""
_NAV_STYLE_NORMAL = """
    QPushButton {
        background-color: transparent;
        color: #1e293b;
        border: none;
        padding: 10px 16px;
        text-align: left;
        font-size: 14px;
        border-radius: 6px;
    }
    QPushButton:hover {
        background-color: #e2e8f0;
    }
    QPushButton:disabled {
        color: #94a3b8;
    }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UfensCrono")
        self.setMinimumSize(960, 640)
        self._nav_buttons: list[QPushButton] = []
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
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 20, 12, 20)
        sb_layout.setSpacing(4)

        logo = QLabel("UfensCrono")
        logo.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; padding: 0 4px 16px 4px;")
        sb_layout.addWidget(logo)

        # ── Stack ────────────────────────────────────────────────────────
        self.stack = QStackedWidget()

        self._atleti_panel = AtletiLista()
        self.stack.addWidget(self._atleti_panel)   # index 0

        for label, index in _NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(False)
            if index is not None:
                btn.clicked.connect(lambda checked, i=index: self._navigate(i))
                btn.setStyleSheet(_NAV_STYLE_NORMAL)
            else:
                btn.setEnabled(False)
                btn.setStyleSheet(_NAV_STYLE_NORMAL)
                placeholder = QLabel(f"<i>{label} — in sviluppo</i>")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("color: #94a3b8; font-size: 14px;")
                self.stack.addWidget(placeholder)

            sb_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sb_layout.addStretch()

        root.addWidget(sidebar)
        root.addWidget(self.stack, stretch=1)

        self._navigate(0)

    def _navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, (_, idx) in enumerate(_NAV_ITEMS):
            if idx == index:
                self._nav_buttons[i].setStyleSheet(_NAV_STYLE_ACTIVE)
            elif idx is not None:
                self._nav_buttons[i].setStyleSheet(_NAV_STYLE_NORMAL)
