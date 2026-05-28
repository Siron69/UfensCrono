from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox,
    QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from db.connection import get_connection
from db.queries import gare as qg
from db.queries import eventi as qev
from db.queries import risultati as qr
from logic.classifica import RigaClassifica, from_row, calcola_classifica
from logic.export_xlsx import esporta_xlsx
from logic.export_pdf import esporta_pdf
from utils.tempo import ms_to_str, str_to_ms

_ID_ROLE = Qt.ItemDataRole.UserRole
_STATO_LABELS = {"ok": "OK", "dsq": "DSQ", "dnf": "DNF", "dns": "DNS", "": "—"}
_STATO_KEYS = ["ok", "dsq", "dnf", "dns"]
_GRAY = QColor("#94a3b8")


class EditRisultatoDialog(QDialog):
    def __init__(self, riga: RigaClassifica, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Modifica — {riga.nome_atleta}")
        self.setMinimumWidth(380)
        self._riga = riga
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addRow("Atleta:", QLabel(f"{self._riga.nome_atleta} (pett. {self._riga.pettorale})"))
        layout.addRow("Tempo originale:", QLabel(
            ms_to_str(self._riga.tempo_ms) if self._riga.tempo_ms is not None else "—"
        ))

        self.combo_stato = QComboBox()
        for key in _STATO_KEYS:
            self.combo_stato.addItem(_STATO_LABELS[key], key)
        current = self._riga.stato if self._riga.stato in _STATO_KEYS else "ok"
        self.combo_stato.setCurrentIndex(_STATO_KEYS.index(current))
        layout.addRow("Stato:", self.combo_stato)

        self.edit_override = QLineEdit()
        self.edit_override.setPlaceholderText("es. 1:23.456  (vuoto = usa originale)")
        self.edit_override.setText(self._riga.tempo_override or "")
        layout.addRow("Tempo corretto:", self.edit_override)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_save(self) -> None:
        override = self.edit_override.text().strip()
        if override and str_to_ms(override) is None:
            QMessageBox.warning(self, "Formato non valido",
                                "Usa il formato M:SS.mmm  oppure  H:MM:SS.mmm")
            return
        self.accept()

    def get_stato(self) -> str:
        return self.combo_stato.currentData()

    def get_tempo_override(self) -> Optional[str]:
        v = self.edit_override.text().strip()
        return v if v else None


class ClassifichePanel(QWidget):
    indietro = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gara_id: Optional[int] = None
        self._nome_gara: str = ""
        self._nome_evento: str = ""
        self._righe: list[RigaClassifica] = []
        self._build_ui()

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        btn_back = QPushButton("← Gare")
        btn_back.setFlat(True)
        btn_back.setStyleSheet("color: #2563eb; font-size: 13px;")
        btn_back.clicked.connect(self.indietro.emit)
        top.addWidget(btn_back)
        top.addStretch()
        btn_refresh = QPushButton("Aggiorna")
        btn_refresh.clicked.connect(self._load)
        top.addWidget(btn_refresh)
        self.btn_xlsx = QPushButton("Esporta Excel")
        self.btn_xlsx.clicked.connect(self._on_esporta_xlsx)
        self.btn_xlsx.setEnabled(False)
        top.addWidget(self.btn_xlsx)
        self.btn_pdf = QPushButton("Esporta PDF")
        self.btn_pdf.clicked.connect(self._on_esporta_pdf)
        self.btn_pdf.setEnabled(False)
        top.addWidget(self.btn_pdf)
        layout.addLayout(top)

        self.lbl_gara = QLabel("Classifica")
        self.lbl_gara.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_gara)

        self.tabs = QTabWidget()

        self.tbl_assoluta = self._make_table(
            ["Pos.", "Pett.", "Atleta", "Cat.", "Sesso", "Tempo", "Stato"]
        )
        self.tabs.addTab(self.tbl_assoluta, "Assoluta")

        self.tbl_categorie = self._make_table(
            ["Pos.Cat.", "Pett.", "Atleta", "Categoria", "Sesso", "Tempo", "Stato"]
        )
        self.tabs.addTab(self.tbl_categorie, "Per Categoria")

        self.tbl_uomini = self._make_table(
            ["Pos.", "Pett.", "Atleta", "Cat.", "Tempo", "Stato"]
        )
        self.tabs.addTab(self.tbl_uomini, "Uomini")

        self.tbl_donne = self._make_table(
            ["Pos.", "Pett.", "Atleta", "Cat.", "Tempo", "Stato"]
        )
        self.tabs.addTab(self.tbl_donne, "Donne")

        layout.addWidget(self.tabs)

        lbl_hint = QLabel("Doppio clic su una riga per modificare stato o tempo")
        lbl_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl_hint)

    def _make_table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        t.doubleClicked.connect(lambda _idx, tbl=t: self._on_edit(tbl))
        return t

    # ── Data loading ──────────────────────────────────────────────────────

    def set_gara(self, gara_id: int) -> None:
        self._gara_id = gara_id
        self._load()

    def _load(self) -> None:
        if not self._gara_id:
            return
        conn = get_connection()
        gara = qg.get_by_id(conn, self._gara_id)
        if not gara:
            return
        ev = qev.get_by_id(conn, gara.evento_id)
        ev_nome = ev.nome if ev else ""
        self.lbl_gara.setText(f"Classifica — {gara.nome} | {ev_nome}")

        self._nome_gara = gara.nome
        self._nome_evento = ev_nome
        rows = qr.get_classifica_raw(conn, self._gara_id)
        self._righe = calcola_classifica([from_row(r) for r in rows])
        has_data = bool(self._righe)
        self.btn_xlsx.setEnabled(has_data)
        self.btn_pdf.setEnabled(has_data)
        self._fill_all()

    # ── Fill tables ───────────────────────────────────────────────────────

    def _fill_all(self) -> None:
        assoluta = sorted(
            self._righe,
            key=lambda r: (0 if r.pos_assoluta else 1, r.pos_assoluta or 9999),
        )
        self._fill_table(self.tbl_assoluta, assoluta, [
            lambda r: str(r.pos_assoluta) if r.pos_assoluta else "—",
            lambda r: r.pettorale,
            lambda r: r.nome_atleta,
            lambda r: r.categoria,
            lambda r: r.sesso,
            lambda r: r.tempo_display,
            lambda r: _STATO_LABELS.get(r.stato, r.stato or "—"),
        ])

        per_cat = sorted(
            self._righe,
            key=lambda r: (
                r.categoria,
                0 if r.pos_categoria else 1,
                r.pos_categoria or 9999,
            ),
        )
        self._fill_table(self.tbl_categorie, per_cat, [
            lambda r: str(r.pos_categoria) if r.pos_categoria else "—",
            lambda r: r.pettorale,
            lambda r: r.nome_atleta,
            lambda r: r.categoria,
            lambda r: r.sesso,
            lambda r: r.tempo_display,
            lambda r: _STATO_LABELS.get(r.stato, r.stato or "—"),
        ])

        uomini = sorted(
            [r for r in self._righe if r.sesso.upper() in ("M", "MASCHIO")],
            key=lambda r: (0 if r.pos_sesso else 1, r.pos_sesso or 9999),
        )
        self._fill_table(self.tbl_uomini, uomini, [
            lambda r: str(r.pos_sesso) if r.pos_sesso else "—",
            lambda r: r.pettorale,
            lambda r: r.nome_atleta,
            lambda r: r.categoria,
            lambda r: r.tempo_display,
            lambda r: _STATO_LABELS.get(r.stato, r.stato or "—"),
        ])

        donne = sorted(
            [r for r in self._righe if r.sesso.upper() in ("F", "FEMMINA")],
            key=lambda r: (0 if r.pos_sesso else 1, r.pos_sesso or 9999),
        )
        self._fill_table(self.tbl_donne, donne, [
            lambda r: str(r.pos_sesso) if r.pos_sesso else "—",
            lambda r: r.pettorale,
            lambda r: r.nome_atleta,
            lambda r: r.categoria,
            lambda r: r.tempo_display,
            lambda r: _STATO_LABELS.get(r.stato, r.stato or "—"),
        ])

    def _fill_table(
        self,
        table: QTableWidget,
        righe: list[RigaClassifica],
        getters: list,
    ) -> None:
        table.setRowCount(0)
        for riga in righe:
            row = table.rowCount()
            table.insertRow(row)
            for col, getter in enumerate(getters):
                text = getter(riga)
                item = QTableWidgetItem(text)
                align = Qt.AlignmentFlag.AlignCenter if col != 2 else (
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                item.setTextAlignment(align)
                if col == 0:
                    item.setData(_ID_ROLE, (riga.iscrizione_id, riga.risultato_id))
                if riga.stato in ("dsq", "dnf", "dns"):
                    item.setForeground(_GRAY)
                table.setItem(row, col, item)

    # ── Export ───────────────────────────────────────────────────────────

    def _on_esporta_xlsx(self) -> None:
        if not self._righe:
            return
        safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in self._nome_gara)
        default_name = f"classifica_{safe}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva classifica Excel", default_name,
            "Excel (*.xlsx);;Tutti i file (*)"
        )
        if not path:
            return
        try:
            dest = esporta_xlsx(self._righe, self._nome_gara, self._nome_evento, dest_path=path)
            QMessageBox.information(self, "Export completato", f"File salvato in:\n{dest}")
        except Exception as e:
            QMessageBox.critical(self, "Errore export", str(e))

    def _on_esporta_pdf(self) -> None:
        if not self._righe:
            return
        safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in self._nome_gara)
        default_name = f"classifica_{safe}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva classifica PDF", default_name,
            "PDF (*.pdf);;Tutti i file (*)"
        )
        if not path:
            return
        try:
            dest = esporta_pdf(self._righe, self._nome_gara, self._nome_evento, dest_path=path)
            QMessageBox.information(self, "Export completato", f"File salvato in:\n{dest}")
        except Exception as e:
            QMessageBox.critical(self, "Errore export", str(e))

    # ── Edit ──────────────────────────────────────────────────────────────

    def _on_edit(self, table: QTableWidget) -> None:
        row = table.currentRow()
        if row < 0:
            return
        item = table.item(row, 0)
        if not item:
            return
        data = item.data(_ID_ROLE)
        if data is None:
            return
        iscrizione_id, risultato_id = data

        riga = next((r for r in self._righe if r.iscrizione_id == iscrizione_id), None)
        if not riga:
            return

        dlg = EditRisultatoDialog(riga, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        nuovo_stato = dlg.get_stato()
        nuovo_override = dlg.get_tempo_override()

        conn = get_connection()
        if risultato_id:
            qr.update_stato(conn, risultato_id, nuovo_stato)
            qr.update_tempo_override(conn, risultato_id, nuovo_override)
        else:
            rid = qr.upsert_stato(conn, iscrizione_id, nuovo_stato)
            if nuovo_override:
                qr.update_tempo_override(conn, rid, nuovo_override)

        self._load()
