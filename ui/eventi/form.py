from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QDateEdit, QTextEdit, QVBoxLayout, QMessageBox,
)
from PyQt6.QtCore import QDate

from models.evento import Evento


class EventoForm(QDialog):
    def __init__(self, parent=None, evento: Optional[Evento] = None):
        super().__init__(parent)
        self._evento = evento
        self.setWindowTitle("Modifica evento" if evento else "Nuovo evento")
        self.setMinimumWidth(420)
        self._build_ui()
        if evento:
            self._populate(evento)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nome = QLineEdit()
        self.data = QDateEdit()
        self.data.setCalendarPopup(True)
        self.data.setDisplayFormat("dd/MM/yyyy")
        self.data.setDate(QDate.currentDate())
        self.luogo = QLineEdit()
        self.note = QTextEdit()
        self.note.setMaximumHeight(80)

        form.addRow("Nome evento *", self.nome)
        form.addRow("Data *", self.data)
        form.addRow("Luogo", self.luogo)
        form.addRow("Note", self.note)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salva")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, evento: Evento) -> None:
        self.nome.setText(evento.nome)
        if evento.data:
            parts = evento.data.split('-')
            if len(parts) == 3:
                self.data.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        self.luogo.setText(evento.luogo or "")
        self.note.setPlainText(evento.note or "")

    def _on_save(self) -> None:
        nome = self.nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Dati non validi", "Il nome dell'evento è obbligatorio.")
            return

        self._evento = self._evento or Evento()
        self._evento.nome = nome
        self._evento.data = self.data.date().toString("yyyy-MM-dd")
        self._evento.luogo = self.luogo.text().strip() or None
        self._evento.note = self.note.toPlainText().strip() or None
        self.accept()

    def get_evento(self) -> Optional[Evento]:
        return self._evento
