from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QSpinBox, QMessageBox, QHeaderView, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from db.connection import get_connection
from db.queries import gare as qg
from db.queries import atleti as qa
from db.queries import eventi as qev
from models.gara import Iscrizione, Categoria
from logic.categorie import calcola_categoria
from ui.atleti.import_wizard import ImportWizard

_ID_ROLE = Qt.ItemDataRole.UserRole


# ── Dialog: aggiungi / modifica iscrizione ──────────────────────────────────

class IscrizioneDialog(QDialog):
    def __init__(
        self,
        parent,
        atleta_nome: str,
        anno_gara: int,
        categorie: list[Categoria],
        pettorale: str = "",
        categoria_calc: Optional[str] = None,
        categoria_override: Optional[str] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Iscrizione atleta")
        self.setMinimumWidth(340)
        self._categorie = categorie
        self._categoria_calc = categoria_calc

        layout = QVBoxLayout(self)
        form = QFormLayout()

        lbl = QLabel(f"<b>{atleta_nome}</b>")
        form.addRow("Atleta:", lbl)

        self.pettorale = QLineEdit(pettorale)
        self.pettorale.setPlaceholderText("es. 001")
        form.addRow("Pettorale *", self.pettorale)

        lbl_calc = QLabel(categoria_calc or "—")
        lbl_calc.setStyleSheet("color: gray;")
        form.addRow("Categoria calcolata:", lbl_calc)

        self.cat_override = QComboBox()
        self.cat_override.addItem("(automatica)", None)
        for cat in categorie:
            self.cat_override.addItem(cat.nome, cat.nome)
        if categoria_override:
            idx = self.cat_override.findData(categoria_override)
            if idx >= 0:
                self.cat_override.setCurrentIndex(idx)

        form.addRow("Override categoria", self.cat_override)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self) -> None:
        if not self.pettorale.text().strip():
            QMessageBox.warning(self, "Dati non validi", "Il pettorale è obbligatorio.")
            return
        self.accept()

    def get_pettorale(self) -> str:
        return self.pettorale.text().strip()

    def get_categoria_override(self) -> Optional[str]:
        return self.cat_override.currentData()


# ── Dialog: aggiungi / modifica categoria ───────────────────────────────────

class CategoriaDialog(QDialog):
    def __init__(self, parent, gara_id: int, cat: Optional[Categoria] = None):
        super().__init__(parent)
        self._gara_id = gara_id
        self._cat = cat
        self.setWindowTitle("Modifica categoria" if cat else "Nuova categoria")
        self.setMinimumWidth(300)
        self._build_ui()
        if cat:
            self._populate(cat)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nome = QLineEdit()
        self.sesso = QComboBox()
        self.sesso.addItems(["MF", "M", "F"])
        self.eta_min = QSpinBox()
        self.eta_min.setRange(0, 120)
        self.eta_min.setSpecialValueText("—")
        self.eta_max = QSpinBox()
        self.eta_max.setRange(0, 120)
        self.eta_max.setSpecialValueText("—")
        self.ordine = QSpinBox()
        self.ordine.setRange(0, 999)

        form.addRow("Nome *", self.nome)
        form.addRow("Sesso", self.sesso)
        form.addRow("Età minima", self.eta_min)
        form.addRow("Età massima", self.eta_max)
        form.addRow("Ordine", self.ordine)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, cat: Categoria) -> None:
        self.nome.setText(cat.nome)
        self.sesso.setCurrentText(cat.sesso)
        self.eta_min.setValue(cat.eta_min or 0)
        self.eta_max.setValue(cat.eta_max or 0)
        self.ordine.setValue(cat.ordine)

    def _on_ok(self) -> None:
        if not self.nome.text().strip():
            QMessageBox.warning(self, "Dati non validi", "Il nome è obbligatorio.")
            return
        self.accept()

    def get_categoria(self) -> Categoria:
        self._cat = self._cat or Categoria(gara_id=self._gara_id)
        self._cat.nome = self.nome.text().strip()
        self._cat.sesso = self.sesso.currentText()
        emin = self.eta_min.value()
        emax = self.eta_max.value()
        self._cat.eta_min = emin if emin > 0 else None
        self._cat.eta_max = emax if emax > 0 else None
        self._cat.ordine = self.ordine.value()
        return self._cat


# ── Pannello principale iscrizioni ───────────────────────────────────────────

class IscrizioniPanel(QWidget):
    indietro = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gara_id: int | None = None
        self._evento_id: int | None = None
        self._anno_gara: int = 2025
        self._is_bozza: bool = True
        self._build_ui()

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
        layout.addLayout(top)

        self.lbl_gara = QLabel("Iscrizioni")
        self.lbl_gara.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_gara)

        # ── Splitter atleti disponibili / iscritti ────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Pannello sinistro: disponibili
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)
        ll.addWidget(QLabel("Atleti disponibili"))

        self.search_disp = QLineEdit()
        self.search_disp.setPlaceholderText("Cerca…")
        self.search_disp.textChanged.connect(self._refresh_disponibili)
        ll.addWidget(self.search_disp)

        self.tbl_disp = QTableWidget(0, 3)
        self.tbl_disp.setHorizontalHeaderLabels(["Cognome / Nome", "S.", "Anno"])
        self.tbl_disp.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_disp.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_disp.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_disp.verticalHeader().setVisible(False)
        self.tbl_disp.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_disp.doubleClicked.connect(self._on_iscrivi)
        self.tbl_disp.itemSelectionChanged.connect(self._update_buttons)
        ll.addWidget(self.tbl_disp)

        left_btns = QHBoxLayout()
        self.btn_iscrivi = QPushButton("Iscrivi →")
        self.btn_iscrivi.setEnabled(False)
        self.btn_iscrivi.clicked.connect(self._on_iscrivi)
        left_btns.addWidget(self.btn_iscrivi)

        self.btn_import_xlsx = QPushButton("Importa XLSX…")
        self.btn_import_xlsx.clicked.connect(self._on_import_xlsx)
        left_btns.addWidget(self.btn_import_xlsx)
        left_btns.addStretch()
        ll.addLayout(left_btns)

        splitter.addWidget(left)

        # Pannello destro: iscritti
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.addWidget(QLabel("Atleti iscritti"))

        self.tbl_iscr = QTableWidget(0, 3)
        self.tbl_iscr.setHorizontalHeaderLabels(["Pett.", "Cognome / Nome", "Categoria"])
        self.tbl_iscr.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_iscr.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_iscr.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_iscr.verticalHeader().setVisible(False)
        self.tbl_iscr.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_iscr.doubleClicked.connect(self._on_modifica_iscr)
        self.tbl_iscr.itemSelectionChanged.connect(self._update_buttons)
        rl.addWidget(self.tbl_iscr)

        right_btns = QHBoxLayout()
        self.btn_modifica_iscr = QPushButton("Modifica")
        self.btn_modifica_iscr.setEnabled(False)
        self.btn_modifica_iscr.clicked.connect(self._on_modifica_iscr)
        right_btns.addWidget(self.btn_modifica_iscr)

        self.btn_rimuovi = QPushButton("← Rimuovi")
        self.btn_rimuovi.setEnabled(False)
        self.btn_rimuovi.clicked.connect(self._on_rimuovi)
        right_btns.addWidget(self.btn_rimuovi)
        right_btns.addStretch()
        rl.addLayout(right_btns)

        splitter.addWidget(right)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter, stretch=1)

        # ── Categorie ─────────────────────────────────────────────────────
        grp = QGroupBox("Categorie della gara")
        cl = QVBoxLayout(grp)

        self.tbl_cat = QTableWidget(0, 4)
        self.tbl_cat.setHorizontalHeaderLabels(["Nome", "Sesso", "Età min", "Età max"])
        self.tbl_cat.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_cat.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_cat.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_cat.verticalHeader().setVisible(False)
        self.tbl_cat.setMaximumHeight(130)
        self.tbl_cat.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_cat.itemSelectionChanged.connect(self._update_buttons)
        cl.addWidget(self.tbl_cat)

        cat_btns = QHBoxLayout()
        self.btn_add_cat = QPushButton("+ Categoria")
        self.btn_add_cat.clicked.connect(self._on_add_cat)
        cat_btns.addWidget(self.btn_add_cat)

        self.btn_mod_cat = QPushButton("Modifica")
        self.btn_mod_cat.setEnabled(False)
        self.btn_mod_cat.clicked.connect(self._on_mod_cat)
        cat_btns.addWidget(self.btn_mod_cat)

        self.btn_del_cat = QPushButton("Elimina")
        self.btn_del_cat.setEnabled(False)
        self.btn_del_cat.clicked.connect(self._on_del_cat)
        cat_btns.addWidget(self.btn_del_cat)
        cat_btns.addStretch()
        cl.addLayout(cat_btns)

        layout.addWidget(grp)

    # ── Caricamento ───────────────────────────────────────────────────────

    def set_gara(self, gara_id: int) -> None:
        self._gara_id = gara_id
        conn = get_connection()
        gara = qg.get_by_id(conn, gara_id)
        if gara:
            self._is_bozza = gara.stato == "bozza"
            self._evento_id = gara.evento_id
            ev = qev.get_by_id(conn, gara.evento_id)
            anno = 2025
            if ev and ev.data:
                try:
                    anno = int(ev.data.split('-')[0])
                except Exception:
                    pass
            self._anno_gara = anno
            stato_lbl = {"bozza": "Bozza", "in_corso": "In corso", "conclusa": "Conclusa"}.get(
                gara.stato, gara.stato
            )
            self.lbl_gara.setText(f"Iscrizioni — {gara.nome} [{stato_lbl}]")
        self.refresh()

    def refresh(self) -> None:
        self._refresh_categorie()
        self._refresh_disponibili()
        self._refresh_iscritti()
        self._update_buttons()

    def _refresh_categorie(self) -> None:
        if self._gara_id is None:
            return
        cats = qg.get_categorie(get_connection(), self._gara_id)
        self.tbl_cat.setRowCount(0)
        for cat in cats:
            row = self.tbl_cat.rowCount()
            self.tbl_cat.insertRow(row)
            items = [
                cat.nome,
                cat.sesso,
                str(cat.eta_min) if cat.eta_min is not None else "—",
                str(cat.eta_max) if cat.eta_max is not None else "—",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(_ID_ROLE, cat.id)
                self.tbl_cat.setItem(row, col, item)

    def _refresh_disponibili(self) -> None:
        if self._gara_id is None:
            return
        conn = get_connection()
        iscritti_ids = qg.atleti_iscritti_ids(conn, self._gara_id)
        search = self.search_disp.text().strip()
        tutti = qa.get_all(conn, search=search)

        self.tbl_disp.setRowCount(0)
        for atleta in tutti:
            if atleta.id in iscritti_ids:
                continue
            row = self.tbl_disp.rowCount()
            self.tbl_disp.insertRow(row)
            anno = atleta.data_nascita.split('-')[0] if atleta.data_nascita else "—"
            items = [f"{atleta.cognome} {atleta.nome}", atleta.sesso, anno]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(_ID_ROLE, atleta.id)
                self.tbl_disp.setItem(row, col, item)

    def _refresh_iscritti(self) -> None:
        if self._gara_id is None:
            return
        iscrizioni = qg.get_iscrizioni(get_connection(), self._gara_id)
        self.tbl_iscr.setRowCount(0)
        for iscr in iscrizioni:
            row = self.tbl_iscr.rowCount()
            self.tbl_iscr.insertRow(row)
            cat_display = iscr.categoria_effettiva or "—"
            if iscr.categoria_override:
                cat_display += " ✎"
            items = [iscr.pettorale, iscr.nome_atleta, cat_display]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(_ID_ROLE, iscr.id)
                self.tbl_iscr.setItem(row, col, item)

    def _update_buttons(self) -> None:
        has_disp = bool(self.tbl_disp.selectedItems())
        has_iscr = bool(self.tbl_iscr.selectedItems())
        has_cat = bool(self.tbl_cat.selectedItems())

        self.btn_iscrivi.setEnabled(has_disp and self._is_bozza)
        self.btn_modifica_iscr.setEnabled(has_iscr)
        self.btn_rimuovi.setEnabled(has_iscr and self._is_bozza)
        self.btn_mod_cat.setEnabled(has_cat)
        self.btn_del_cat.setEnabled(has_cat)

    # ── Azioni iscrizioni ─────────────────────────────────────────────────

    def _on_iscrivi(self) -> None:
        if not self.tbl_disp.selectedItems():
            return
        atleta_id = self.tbl_disp.item(self.tbl_disp.currentRow(), 0).data(_ID_ROLE)
        atleta = qa.get_by_id(get_connection(), atleta_id)
        if not atleta:
            return

        conn = get_connection()
        categorie = qg.get_categorie(conn, self._gara_id)
        cat_calc = calcola_categoria(
            categorie, atleta.data_nascita or "", atleta.sesso, self._anno_gara
        )
        # Suggerisci il prossimo pettorale libero a livello di evento
        pettorale = qg.next_pettorale_evento(conn, self._evento_id) if self._evento_id else qg.next_pettorale(conn, self._gara_id)

        dlg = IscrizioneDialog(
            self, atleta.nome_completo, self._anno_gara,
            categorie, pettorale=pettorale, categoria_calc=cat_calc,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Validazione unicità pettorale cross-gara
        nuovo_pett = dlg.get_pettorale()
        if self._evento_id:
            conflitto = qg.get_pettorale_conflitto(conn, self._evento_id, nuovo_pett, exclude_gara_id=self._gara_id)
            if conflitto:
                QMessageBox.warning(
                    self, "Pettorale già in uso",
                    f"Il pettorale «{nuovo_pett}» è già usato nella gara «{conflitto}» "
                    f"dello stesso evento.\n\nScegli un numero diverso.",
                )
                return

        try:
            qg.add_iscrizione(
                conn, self._gara_id, atleta_id,
                nuovo_pett,
                categoria_calc=cat_calc,
                categoria_override=dlg.get_categoria_override(),
            )
        except Exception as e:
            QMessageBox.warning(self, "Errore", str(e))
            return

        self._refresh_disponibili()
        self._refresh_iscritti()
        self._update_buttons()

    def _on_modifica_iscr(self) -> None:
        if not self.tbl_iscr.selectedItems():
            return
        iscr_id = self.tbl_iscr.item(self.tbl_iscr.currentRow(), 0).data(_ID_ROLE)
        conn = get_connection()
        iscr = qg.get_iscrizione_by_id(conn, iscr_id)
        if not iscr:
            return
        categorie = qg.get_categorie(conn, self._gara_id)

        dlg = IscrizioneDialog(
            self, iscr.nome_atleta, self._anno_gara, categorie,
            pettorale=iscr.pettorale,
            categoria_calc=iscr.categoria_calc,
            categoria_override=iscr.categoria_override,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        nuovo_pett = dlg.get_pettorale()
        # Validazione unicità pettorale cross-gara (solo se il pettorale è cambiato)
        if nuovo_pett != iscr.pettorale and self._evento_id:
            conflitto = qg.get_pettorale_conflitto(conn, self._evento_id, nuovo_pett, exclude_gara_id=self._gara_id)
            if conflitto:
                QMessageBox.warning(
                    self, "Pettorale già in uso",
                    f"Il pettorale «{nuovo_pett}» è già usato nella gara «{conflitto}» "
                    f"dello stesso evento.\n\nScegli un numero diverso.",
                )
                return

        iscr.pettorale = nuovo_pett
        iscr.categoria_override = dlg.get_categoria_override()
        try:
            qg.update_iscrizione(conn, iscr)
        except Exception as e:
            QMessageBox.warning(self, "Errore", str(e))
            return
        self._refresh_iscritti()

    def _on_rimuovi(self) -> None:
        if not self.tbl_iscr.selectedItems():
            return
        iscr_id = self.tbl_iscr.item(self.tbl_iscr.currentRow(), 0).data(_ID_ROLE)
        conn = get_connection()
        iscr = qg.get_iscrizione_by_id(conn, iscr_id)
        nome = iscr.nome_atleta if iscr else str(iscr_id)
        if QMessageBox.question(
            self, "Conferma", f"Rimuovere l'iscrizione di «{nome}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            qg.remove_iscrizione(conn, iscr_id)
            self._refresh_disponibili()
            self._refresh_iscritti()
            self._update_buttons()

    # ── Azioni categorie ──────────────────────────────────────────────────

    def _on_add_cat(self) -> None:
        dlg = CategoriaDialog(self, self._gara_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            qg.insert_categoria(get_connection(), dlg.get_categoria())
            self._refresh_categorie()

    def _on_mod_cat(self) -> None:
        if not self.tbl_cat.selectedItems():
            return
        cat_id = self.tbl_cat.item(self.tbl_cat.currentRow(), 0).data(_ID_ROLE)
        cats = qg.get_categorie(get_connection(), self._gara_id)
        cat = next((c for c in cats if c.id == cat_id), None)
        if not cat:
            return
        dlg = CategoriaDialog(self, self._gara_id, cat)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            qg.update_categoria(get_connection(), dlg.get_categoria())
            self._refresh_categorie()

    def _on_del_cat(self) -> None:
        if not self.tbl_cat.selectedItems():
            return
        cat_id = self.tbl_cat.item(self.tbl_cat.currentRow(), 0).data(_ID_ROLE)
        if QMessageBox.question(
            self, "Conferma", "Eliminare questa categoria?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            qg.delete_categoria(get_connection(), cat_id)
            self._refresh_categorie()

    def _on_import_xlsx(self) -> None:
        dlg = ImportWizard(self, gara_id=self._gara_id)
        dlg.exec()
        self.refresh()
