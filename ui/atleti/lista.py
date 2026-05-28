from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QPushButton, QLabel, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal

from db.connection import get_connection
from db.queries import atleti as q
from models.atleta import Atleta
from ui.atleti.form import AtletaForm

_COLS = ["Cognome", "Nome", "Sesso", "Data nascita", "Società", "Tessera"]
_ATLETA_ID_ROLE = Qt.ItemDataRole.UserRole


class AtletiLista(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Titolo ───────────────────────────────────────────────────────
        title = QLabel("Atleti")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # ── Barra ricerca ────────────────────────────────────────────────
        bar = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca per nome, cognome, società…")
        self.search.textChanged.connect(self.refresh)
        bar.addWidget(self.search, stretch=1)

        self.sesso_filter = QComboBox()
        self.sesso_filter.addItems(["Tutti", "M", "F"])
        self.sesso_filter.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.sesso_filter)

        btn_nuovo = QPushButton("+ Nuovo")
        btn_nuovo.clicked.connect(self._on_nuovo)
        bar.addWidget(btn_nuovo)

        layout.addLayout(bar)

        # ── Tabella ──────────────────────────────────────────────────────
        self.table = QTableWidget(0, len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._on_modifica)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table)

        # ── Barra azioni ─────────────────────────────────────────────────
        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_modifica = QPushButton("Modifica")
        self.btn_modifica.setEnabled(False)
        self.btn_modifica.clicked.connect(self._on_modifica)
        actions.addWidget(self.btn_modifica)

        self.btn_elimina = QPushButton("Elimina")
        self.btn_elimina.setEnabled(False)
        self.btn_elimina.clicked.connect(self._on_elimina)
        actions.addWidget(self.btn_elimina)

        layout.addLayout(actions)

        # ── Contatore ────────────────────────────────────────────────────
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.lbl_count)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        search = self.search.text().strip()
        sesso_txt = self.sesso_filter.currentText()
        sesso = sesso_txt if sesso_txt in ('M', 'F') else ""

        conn = get_connection()
        atleti = q.get_all(conn, search=search, sesso=sesso)

        self.table.setRowCount(0)
        for atleta in atleti:
            row = self.table.rowCount()
            self.table.insertRow(row)

            dob_display = self._format_dob(atleta.data_nascita)

            items = [
                atleta.cognome,
                atleta.nome,
                atleta.sesso,
                dob_display,
                atleta.societa or "",
                atleta.tessera or "",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(_ATLETA_ID_ROLE, atleta.id)
                self.table.setItem(row, col, item)

        n = len(atleti)
        self.lbl_count.setText(f"{n} atleta{'/' + str(n) if n == 1 else 'i'}")
        self._update_buttons()

    def _format_dob(self, iso: str) -> str:
        try:
            y, m, d = iso.split('-')
            return f"{d}/{m}/{y}"
        except Exception:
            return iso

    def _update_buttons(self) -> None:
        has_sel = bool(self.table.selectedItems())
        self.btn_modifica.setEnabled(has_sel)
        self.btn_elimina.setEnabled(has_sel)

    def _selected_atleta_id(self) -> int | None:
        rows = self.table.selectedItems()
        if not rows:
            return None
        return self.table.item(self.table.currentRow(), 0).data(_ATLETA_ID_ROLE)

    def _on_nuovo(self) -> None:
        dlg = AtletaForm(self)
        if dlg.exec() == AtletaForm.DialogCode.Accepted:
            atleta = dlg.get_atleta()
            if atleta:
                q.insert(get_connection(), atleta)
                self.refresh()

    def _on_modifica(self) -> None:
        atleta_id = self._selected_atleta_id()
        if atleta_id is None:
            return
        atleta = q.get_by_id(get_connection(), atleta_id)
        if atleta is None:
            return
        dlg = AtletaForm(self, atleta=atleta)
        if dlg.exec() == AtletaForm.DialogCode.Accepted:
            updated = dlg.get_atleta()
            if updated:
                q.update(get_connection(), updated)
                self.refresh()

    def _on_elimina(self) -> None:
        atleta_id = self._selected_atleta_id()
        if atleta_id is None:
            return

        conn = get_connection()
        if q.has_iscrizioni(conn, atleta_id):
            QMessageBox.warning(
                self,
                "Eliminazione non possibile",
                "L'atleta è iscritto a una o più gare e non può essere eliminato.\n"
                "Rimuovere prima le iscrizioni.",
            )
            return

        atleta = q.get_by_id(conn, atleta_id)
        nome = atleta.nome_completo if atleta else str(atleta_id)
        answer = QMessageBox.question(
            self,
            "Conferma eliminazione",
            f"Eliminare l'atleta «{nome}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            q.delete(conn, atleta_id)
            self.refresh()
