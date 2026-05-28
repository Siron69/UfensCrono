import re
from typing import Optional
from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QComboBox, QDateEdit,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget, QMessageBox,
)
from PyQt6.QtCore import QDate, Qt

from models.atleta import Atleta


class AtletaForm(QDialog):
    def __init__(self, parent=None, atleta: Optional[Atleta] = None):
        super().__init__(parent)
        self._atleta = atleta
        self.setWindowTitle("Modifica atleta" if atleta else "Nuovo atleta")
        self.setMinimumWidth(520)
        self._build_ui()
        if atleta:
            self._populate(atleta)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        scroll.setWidget(container)
        root.addWidget(scroll)

        # ── Dati anagrafici obbligatori ──────────────────────────────────
        grp_ana = QGroupBox("Dati anagrafici")
        f_ana = QFormLayout(grp_ana)

        self.nome = QLineEdit()
        self.cognome = QLineEdit()
        self.sesso = QComboBox()
        self.sesso.addItems(["M", "F"])
        self.data_nascita = QDateEdit()
        self.data_nascita.setCalendarPopup(True)
        self.data_nascita.setDisplayFormat("dd/MM/yyyy")
        self.data_nascita.setDate(QDate(2000, 1, 1))
        self.luogo_nascita = QLineEdit()
        self.nazionalita = QLineEdit()
        self.nazionalita.setText("ITA")

        f_ana.addRow("Nome *", self.nome)
        f_ana.addRow("Cognome *", self.cognome)
        f_ana.addRow("Sesso *", self.sesso)
        f_ana.addRow("Data di nascita *", self.data_nascita)
        f_ana.addRow("Luogo di nascita", self.luogo_nascita)
        f_ana.addRow("Nazionalità", self.nazionalita)
        layout.addWidget(grp_ana)

        # ── Dati societari ───────────────────────────────────────────────
        grp_soc = QGroupBox("Dati societari")
        f_soc = QFormLayout(grp_soc)

        self.codice_fiscale = QLineEdit()
        self.codice_fiscale.setMaxLength(16)
        self.societa = QLineEdit()
        self.codice_societa = QLineEdit()
        self.ente = QLineEdit()
        self.tessera = QLineEdit()
        self.tessera2 = QLineEdit()
        self.categoria = QLineEdit()

        f_soc.addRow("Codice fiscale", self.codice_fiscale)
        f_soc.addRow("Società", self.societa)
        f_soc.addRow("Codice società", self.codice_societa)
        f_soc.addRow("Ente", self.ente)
        f_soc.addRow("Tessera", self.tessera)
        f_soc.addRow("Tessera 2", self.tessera2)
        f_soc.addRow("Categoria", self.categoria)
        layout.addWidget(grp_soc)

        # ── Certificato medico ───────────────────────────────────────────
        grp_cert = QGroupBox("Certificato medico")
        f_cert = QFormLayout(grp_cert)

        self.scad_certificato = QLineEdit()
        self.scad_certificato.setPlaceholderText("GG/MM/AAAA (opzionale)")
        self.stato_cert = QLineEdit()

        f_cert.addRow("Scadenza certificato", self.scad_certificato)
        f_cert.addRow("Stato certificato", self.stato_cert)
        layout.addWidget(grp_cert)

        # ── Contatti ─────────────────────────────────────────────────────
        grp_cont = QGroupBox("Contatti")
        f_cont = QFormLayout(grp_cont)

        self.telefono = QLineEdit()
        self.cellulare = QLineEdit()
        self.email = QLineEdit()

        f_cont.addRow("Telefono", self.telefono)
        f_cont.addRow("Cellulare", self.cellulare)
        f_cont.addRow("E-mail", self.email)
        layout.addWidget(grp_cont)

        # ── Note ─────────────────────────────────────────────────────────
        grp_note = QGroupBox("Note")
        f_note = QVBoxLayout(grp_note)
        self.note = QTextEdit()
        self.note.setMaximumHeight(80)
        f_note.addWidget(self.note)
        layout.addWidget(grp_note)

        # ── Pulsanti ─────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salva")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate(self, atleta: Atleta) -> None:
        self.nome.setText(atleta.nome)
        self.cognome.setText(atleta.cognome)
        self.sesso.setCurrentText(atleta.sesso)
        if atleta.data_nascita:
            parts = atleta.data_nascita.split('-')
            if len(parts) == 3:
                self.data_nascita.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        self.luogo_nascita.setText(atleta.luogo_nascita or "")
        self.nazionalita.setText(atleta.nazionalita or "ITA")
        self.codice_fiscale.setText(atleta.codice_fiscale or "")
        self.societa.setText(atleta.societa or "")
        self.codice_societa.setText(atleta.codice_societa or "")
        self.ente.setText(atleta.ente or "")
        self.tessera.setText(atleta.tessera or "")
        self.tessera2.setText(atleta.tessera2 or "")
        self.categoria.setText(atleta.categoria or "")
        self.scad_certificato.setText(
            self._iso_to_display(atleta.scad_certificato) if atleta.scad_certificato else ""
        )
        self.stato_cert.setText(atleta.stato_cert or "")
        self.telefono.setText(atleta.telefono or "")
        self.cellulare.setText(atleta.cellulare or "")
        self.email.setText(atleta.email or "")
        self.note.setPlainText(atleta.note or "")

    def _iso_to_display(self, iso: str) -> str:
        try:
            y, m, d = iso.split('-')
            return f"{d}/{m}/{y}"
        except Exception:
            return iso

    def _display_to_iso(self, display: str) -> Optional[str]:
        display = display.strip()
        if not display:
            return None
        m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', display)
        if m:
            d, mo, y = m.groups()
            return f"{y}-{int(mo):02}-{int(d):02}"
        m2 = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', display)
        if m2:
            return display
        return None

    def _on_save(self) -> None:
        errors = []

        nome = self.nome.text().strip()
        cognome = self.cognome.text().strip()
        if not nome:
            errors.append("Il nome è obbligatorio.")
        if not cognome:
            errors.append("Il cognome è obbligatorio.")

        dob = self.data_nascita.date()
        if dob >= QDate.currentDate():
            errors.append("La data di nascita non può essere oggi o nel futuro.")

        cf = self.codice_fiscale.text().strip()
        if cf and len(cf) != 16:
            errors.append("Il codice fiscale deve essere di 16 caratteri.")

        email = self.email.text().strip()
        if email and '@' not in email:
            errors.append("Formato e-mail non valido.")

        scad_raw = self.scad_certificato.text().strip()
        scad_iso = None
        if scad_raw:
            scad_iso = self._display_to_iso(scad_raw)
            if scad_iso is None:
                errors.append("Formato scadenza certificato non valido (usare GG/MM/AAAA).")

        if errors:
            QMessageBox.warning(self, "Dati non validi", "\n".join(errors))
            return

        self._atleta = self._atleta or Atleta()
        self._atleta.nome = nome
        self._atleta.cognome = cognome
        self._atleta.sesso = self.sesso.currentText()
        self._atleta.data_nascita = dob.toString("yyyy-MM-dd")
        self._atleta.luogo_nascita = self.luogo_nascita.text().strip() or None
        self._atleta.nazionalita = self.nazionalita.text().strip() or "ITA"
        self._atleta.codice_fiscale = cf or None
        self._atleta.societa = self.societa.text().strip() or None
        self._atleta.codice_societa = self.codice_societa.text().strip() or None
        self._atleta.ente = self.ente.text().strip() or None
        self._atleta.tessera = self.tessera.text().strip() or None
        self._atleta.tessera2 = self.tessera2.text().strip() or None
        self._atleta.categoria = self.categoria.text().strip() or None
        self._atleta.scad_certificato = scad_iso
        self._atleta.stato_cert = self.stato_cert.text().strip() or None
        self._atleta.telefono = self.telefono.text().strip() or None
        self._atleta.cellulare = self.cellulare.text().strip() or None
        self._atleta.email = email or None
        self._atleta.note = self.note.toPlainText().strip() or None

        self.accept()

    def get_atleta(self) -> Optional[Atleta]:
        return self._atleta
