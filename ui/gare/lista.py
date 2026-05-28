from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal

from db.connection import get_connection
from db.queries import eventi as qev
from db.queries import gare as qg
from models.gara import Gara
from ui.gare.form import GaraForm

_COLS = ["Nome gara", "Tipo", "Distanza", "Stato", "Iscritti"]
_ID_ROLE = Qt.ItemDataRole.UserRole

_STATO_LABEL = {
    "bozza": "Bozza",
    "in_corso": "In corso",
    "conclusa": "Conclusa",
}


class GareLista(QWidget):
    apri_iscrizioni = pyqtSignal(int)   # gara_id
    indietro = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._evento_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        top = QHBoxLayout()
        btn_back = QPushButton("← Eventi")
        btn_back.setFlat(True)
        btn_back.setStyleSheet("color: #2563eb; font-size: 13px;")
        btn_back.clicked.connect(self.indietro.emit)
        top.addWidget(btn_back)
        top.addStretch()
        layout.addLayout(top)

        self.lbl_evento = QLabel("Gare")
        self.lbl_evento.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_evento)

        bar = QHBoxLayout()
        self.btn_nuova = QPushButton("+ Nuova gara")
        self.btn_nuova.clicked.connect(self._on_nuova)
        bar.addWidget(self.btn_nuova)
        bar.addStretch()
        layout.addLayout(bar)

        self.table = QTableWidget(0, len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(lambda: self._on_iscrizioni())
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_iscrizioni = QPushButton("Iscrizioni →")
        self.btn_iscrizioni.setEnabled(False)
        self.btn_iscrizioni.clicked.connect(self._on_iscrizioni)
        actions.addWidget(self.btn_iscrizioni)

        self.btn_modifica = QPushButton("Modifica")
        self.btn_modifica.setEnabled(False)
        self.btn_modifica.clicked.connect(self._on_modifica)
        actions.addWidget(self.btn_modifica)

        self.btn_elimina = QPushButton("Elimina")
        self.btn_elimina.setEnabled(False)
        self.btn_elimina.clicked.connect(self._on_elimina)
        actions.addWidget(self.btn_elimina)

        layout.addLayout(actions)

    def set_evento(self, evento_id: int) -> None:
        self._evento_id = evento_id
        conn = get_connection()
        ev = qev.get_by_id(conn, evento_id)
        if ev:
            self.lbl_evento.setText(f"Gare — {ev.nome}")
        self.refresh()

    def refresh(self) -> None:
        if self._evento_id is None:
            return
        conn = get_connection()
        gare = qg.get_by_evento(conn, self._evento_id)

        self.table.setRowCount(0)
        for gara in gare:
            row = self.table.rowCount()
            self.table.insertRow(row)
            dist = f"{gara.distanza_m} m" if gara.distanza_m else "—"
            n = qg.count_iscritti(conn, gara.id)
            items = [
                gara.nome,
                gara.tipo or "—",
                dist,
                _STATO_LABEL.get(gara.stato, gara.stato),
                str(n),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(_ID_ROLE, gara.id)
                self.table.setItem(row, col, item)

        self._update_buttons()

    def _update_buttons(self) -> None:
        has = bool(self.table.selectedItems())
        self.btn_iscrizioni.setEnabled(has)
        self.btn_modifica.setEnabled(has and self._selected_stato() == "bozza")
        self.btn_elimina.setEnabled(has and self._selected_stato() == "bozza")

    def _selected_id(self) -> int | None:
        if not self.table.selectedItems():
            return None
        return self.table.item(self.table.currentRow(), 0).data(_ID_ROLE)

    def _selected_stato(self) -> str:
        if not self.table.selectedItems():
            return ""
        item = self.table.item(self.table.currentRow(), 3)
        reverse = {v: k for k, v in _STATO_LABEL.items()}
        return reverse.get(item.text() if item else "", "")

    def _on_nuova(self) -> None:
        if self._evento_id is None:
            return
        dlg = GaraForm(self, evento_id=self._evento_id)
        if dlg.exec() == GaraForm.DialogCode.Accepted:
            gara = dlg.get_gara()
            if gara:
                qg.insert(get_connection(), gara)
                self.refresh()

    def _on_modifica(self) -> None:
        gid = self._selected_id()
        if gid is None:
            return
        gara = qg.get_by_id(get_connection(), gid)
        if not gara:
            return
        dlg = GaraForm(self, gara=gara)
        if dlg.exec() == GaraForm.DialogCode.Accepted:
            updated = dlg.get_gara()
            if updated:
                qg.update(get_connection(), updated)
                self.refresh()

    def _on_elimina(self) -> None:
        gid = self._selected_id()
        if gid is None:
            return
        gara = qg.get_by_id(get_connection(), gid)
        nome = gara.nome if gara else str(gid)
        if QMessageBox.question(
            self, "Conferma eliminazione", f"Eliminare la gara «{nome}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            qg.delete(get_connection(), gid)
            self.refresh()

    def _on_iscrizioni(self) -> None:
        gid = self._selected_id()
        if gid is not None:
            self.apri_iscrizioni.emit(gid)
