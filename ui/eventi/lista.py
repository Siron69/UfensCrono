from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal

from db.connection import get_connection
from db.queries import eventi as q
from models.evento import Evento
from ui.eventi.form import EventoForm

_COLS = ["Nome evento", "Data", "Luogo"]
_ID_ROLE = Qt.ItemDataRole.UserRole


class EventiLista(QWidget):
    apri_gare = pyqtSignal(int)   # evento_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Eventi")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        bar = QHBoxLayout()
        btn_nuovo = QPushButton("+ Nuovo evento")
        btn_nuovo.clicked.connect(self._on_nuovo)
        bar.addWidget(btn_nuovo)
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
        self.table.doubleClicked.connect(lambda: self._on_apri_gare())
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_gare = QPushButton("Apri gare →")
        self.btn_gare.setEnabled(False)
        self.btn_gare.clicked.connect(self._on_apri_gare)
        actions.addWidget(self.btn_gare)

        self.btn_modifica = QPushButton("Modifica")
        self.btn_modifica.setEnabled(False)
        self.btn_modifica.clicked.connect(self._on_modifica)
        actions.addWidget(self.btn_modifica)

        self.btn_elimina = QPushButton("Elimina")
        self.btn_elimina.setEnabled(False)
        self.btn_elimina.clicked.connect(self._on_elimina)
        actions.addWidget(self.btn_elimina)

        layout.addLayout(actions)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        conn = get_connection()
        eventi = q.get_all(conn)

        self.table.setRowCount(0)
        for ev in eventi:
            row = self.table.rowCount()
            self.table.insertRow(row)
            items = [ev.nome, self._fmt_date(ev.data), ev.luogo or ""]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(_ID_ROLE, ev.id)
                self.table.setItem(row, col, item)

        self._update_buttons()

    def _fmt_date(self, iso: str) -> str:
        try:
            y, m, d = iso.split('-')
            return f"{d}/{m}/{y}"
        except Exception:
            return iso

    def _update_buttons(self) -> None:
        has = bool(self.table.selectedItems())
        self.btn_gare.setEnabled(has)
        self.btn_modifica.setEnabled(has)
        self.btn_elimina.setEnabled(has)

    def _selected_id(self) -> int | None:
        if not self.table.selectedItems():
            return None
        return self.table.item(self.table.currentRow(), 0).data(_ID_ROLE)

    def _on_nuovo(self) -> None:
        dlg = EventoForm(self)
        if dlg.exec() == EventoForm.DialogCode.Accepted:
            ev = dlg.get_evento()
            if ev:
                q.insert(get_connection(), ev)
                self.refresh()

    def _on_modifica(self) -> None:
        eid = self._selected_id()
        if eid is None:
            return
        ev = q.get_by_id(get_connection(), eid)
        if not ev:
            return
        dlg = EventoForm(self, evento=ev)
        if dlg.exec() == EventoForm.DialogCode.Accepted:
            updated = dlg.get_evento()
            if updated:
                q.update(get_connection(), updated)
                self.refresh()

    def _on_elimina(self) -> None:
        eid = self._selected_id()
        if eid is None:
            return
        conn = get_connection()
        if q.has_gare(conn, eid):
            QMessageBox.warning(
                self, "Eliminazione non possibile",
                "L'evento contiene gare e non può essere eliminato.\n"
                "Eliminare prima le gare.",
            )
            return
        ev = q.get_by_id(conn, eid)
        nome = ev.nome if ev else str(eid)
        if QMessageBox.question(
            self, "Conferma eliminazione", f"Eliminare l'evento «{nome}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            q.delete(conn, eid)
            self.refresh()

    def _on_apri_gare(self) -> None:
        eid = self._selected_id()
        if eid is not None:
            self.apri_gare.emit(eid)
