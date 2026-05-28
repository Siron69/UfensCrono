from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QSpinBox, QTextEdit, QVBoxLayout, QMessageBox,
)

from models.gara import Gara


class GaraForm(QDialog):
    def __init__(self, parent=None, gara: Optional[Gara] = None, evento_id: int = 0):
        super().__init__(parent)
        self._gara = gara
        self._evento_id = evento_id
        self.setWindowTitle("Modifica gara" if gara else "Nuova gara")
        self.setMinimumWidth(380)
        self._build_ui()
        if gara:
            self._populate(gara)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nome = QLineEdit()
        self.tipo = QLineEdit()
        self.tipo.setPlaceholderText("es. corsa, ciclismo, sci")
        self.distanza = QSpinBox()
        self.distanza.setRange(0, 999_999)
        self.distanza.setSuffix(" m")
        self.distanza.setSpecialValueText("—")
        self.note = QTextEdit()
        self.note.setMaximumHeight(60)

        form.addRow("Nome gara *", self.nome)
        form.addRow("Tipo", self.tipo)
        form.addRow("Distanza", self.distanza)
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

    def _populate(self, gara: Gara) -> None:
        self.nome.setText(gara.nome)
        self.tipo.setText(gara.tipo or "")
        self.distanza.setValue(gara.distanza_m or 0)
        self.note.setPlainText(gara.note or "")

    def _on_save(self) -> None:
        nome = self.nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Dati non validi", "Il nome della gara è obbligatorio.")
            return

        self._gara = self._gara or Gara(evento_id=self._evento_id)
        self._gara.nome = nome
        self._gara.tipo = self.tipo.text().strip() or None
        dist = self.distanza.value()
        self._gara.distanza_m = dist if dist > 0 else None
        self._gara.note = self.note.toPlainText().strip() or None
        self.accept()

    def get_gara(self) -> Optional[Gara]:
        return self._gara
