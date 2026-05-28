from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.tempo import ms_to_str


class CronoDisplay(QMainWindow):
    """Finestra pubblica: timer grande + lista arrivi. Sola lettura, aggiornata via segnali."""

    def __init__(self, nome_gara: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"UfensCrono Display — {nome_gara}")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Timer
        self.lbl_timer = QLabel("0:00.000")
        font = QFont("Courier New", 72, QFont.Weight.Bold)
        self.lbl_timer.setFont(font)
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet("color: #22d3ee;")
        layout.addWidget(self.lbl_timer)

        # Gara label
        self.lbl_gara = QLabel("")
        self.lbl_gara.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gara.setStyleSheet("color: #94a3b8; font-size: 18px;")
        layout.addWidget(self.lbl_gara)

        # Tabella arrivi
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Pett.", "Atleta", "Tempo"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e293b; color: #f8fafc;
                           gridline-color: #334155; font-size: 16px; }
            QHeaderView::section { background-color: #334155; color: #94a3b8;
                                   padding: 6px; border: none; }
            QTableWidget::item:alternate { background-color: #0f172a; }
        """)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    # ── Slot pubblici (ricevono segnali dall'operatore) ───────────────────

    def on_tick(self, elapsed_ms: int) -> None:
        self.lbl_timer.setText(ms_to_str(elapsed_ms))

    def on_arrivo_confermato(self, pettorale: str, ordine: int, tempo_str: str, nome: str, categoria: str) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, text in enumerate([str(ordine), pettorale, nome, tempo_str]):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col != 2 else Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, col, item)
        self.table.scrollToBottom()

    def on_arrivo_annullato(self, ordine: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and int(item.text()) == ordine:
                self.table.removeRow(row)
                break

    def set_gara_label(self, text: str) -> None:
        self.lbl_gara.setText(text)

    def carica_arrivi(self, arrivi: list) -> None:
        """Popola la tabella con gli arrivi già registrati (caricamento iniziale)."""
        self.table.setRowCount(0)
        for r in arrivi:
            from utils.tempo import ms_to_str
            tempo_str = ms_to_str(r.tempo_ms) if r.tempo_ms is not None else "—"
            self.on_arrivo_confermato(
                r.pettorale or "", r.ordine_arrivo or 0,
                tempo_str, r.nome_atleta, r.categoria_effettiva or ""
            )
