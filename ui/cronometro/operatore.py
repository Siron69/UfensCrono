import time
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from db.connection import get_connection
from db.queries import gare as qg
from db.queries import eventi as qev
from db.queries import risultati as qr
from logic.timer import CronoThread
from logic.backup import crea_backup
from utils.tempo import ms_to_str
from ui.cronometro.display import CronoDisplay

_ID_ROLE = Qt.ItemDataRole.UserRole   # iscrizione_id


class CronometroPanel(QWidget):
    indietro = pyqtSignal()

    # Segnali verso la display
    arrivoConfermato = pyqtSignal(str, int, str, str, str)  # pettorale, ordine, tempo_str, nome, cat
    arrivoAnnullato  = pyqtSignal(int)                       # ordine

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gara_id: Optional[int] = None
        self._start_ts: float = 0.0
        self._thread: Optional[CronoThread] = None
        self._display: Optional[CronoDisplay] = None
        self._build_ui()

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        # Header
        top = QHBoxLayout()
        btn_back = QPushButton("← Gare")
        btn_back.setFlat(True)
        btn_back.setStyleSheet("color: #2563eb; font-size: 13px;")
        btn_back.clicked.connect(self._on_indietro)
        top.addWidget(btn_back)
        top.addStretch()
        self.btn_apri_display = QPushButton("Apri display pubblica")
        self.btn_apri_display.clicked.connect(self._on_apri_display)
        self.btn_apri_display.setEnabled(False)
        top.addWidget(self.btn_apri_display)
        root.addLayout(top)

        self.lbl_gara = QLabel("Cronometro")
        self.lbl_gara.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(self.lbl_gara)

        # ── Splitter: timer + arrivi ──────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Pannello timer
        timer_panel = QWidget()
        tl = QVBoxLayout(timer_panel)
        tl.setContentsMargins(0, 0, 16, 0)

        self.lbl_timer = QLabel("0:00.000")
        font = QFont("Courier New", 48, QFont.Weight.Bold)
        self.lbl_timer.setFont(font)
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet(
            "color: #1e293b; background: #f1f5f9; border-radius: 8px; padding: 16px;"
        )
        tl.addWidget(self.lbl_timer)

        ctrl = QHBoxLayout()
        self.btn_avvia = QPushButton("▶ Avvia gara")
        self.btn_avvia.setStyleSheet(
            "background-color: #16a34a; color: white; padding: 8px 20px;"
            "font-size: 14px; border-radius: 4px;"
        )
        self.btn_avvia.clicked.connect(self._on_avvia)
        ctrl.addWidget(self.btn_avvia)

        self.btn_concludi = QPushButton("■ Concludi gara")
        self.btn_concludi.setStyleSheet(
            "background-color: #dc2626; color: white; padding: 8px 20px;"
            "font-size: 14px; border-radius: 4px;"
        )
        self.btn_concludi.clicked.connect(self._on_concludi)
        self.btn_concludi.setVisible(False)
        ctrl.addWidget(self.btn_concludi)
        tl.addLayout(ctrl)

        self.lbl_stato = QLabel("")
        self.lbl_stato.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stato.setStyleSheet("color: #64748b; font-size: 12px;")
        tl.addWidget(self.lbl_stato)
        tl.addStretch()

        splitter.addWidget(timer_panel)

        # Pannello arrivi
        arrivi_panel = QWidget()
        al = QVBoxLayout(arrivi_panel)
        al.setContentsMargins(16, 0, 0, 0)

        self.lbl_arrivi_count = QLabel("Arrivati: 0")
        self.lbl_arrivi_count.setStyleSheet("font-weight: bold;")
        al.addWidget(self.lbl_arrivi_count)

        self.tbl_arrivi = QTableWidget(0, 4)
        self.tbl_arrivi.setHorizontalHeaderLabels(["#", "Pett.", "Atleta", "Tempo"])
        self.tbl_arrivi.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_arrivi.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl_arrivi.verticalHeader().setVisible(False)
        self.tbl_arrivi.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        al.addWidget(self.tbl_arrivi)

        splitter.addWidget(arrivi_panel)
        splitter.setSizes([320, 480])
        root.addWidget(splitter)

        # ── Tabella atleti in gara ────────────────────────────────────────
        self.lbl_in_gara = QLabel("In gara:")
        self.lbl_in_gara.setStyleSheet("font-weight: bold; margin-top: 8px;")
        root.addWidget(self.lbl_in_gara)

        self.tbl_in_gara = QTableWidget(0, 3)
        self.tbl_in_gara.setHorizontalHeaderLabels(["Pettorale", "Atleta", ""])
        self.tbl_in_gara.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_in_gara.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl_in_gara.verticalHeader().setVisible(False)
        self.tbl_in_gara.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_in_gara.setMaximumHeight(220)
        root.addWidget(self.tbl_in_gara)

        # ── Barra input rapido ────────────────────────────────────────────
        bib_bar = QHBoxLayout()
        bib_bar.addWidget(QLabel("Pettorale:"))
        self.bib_input = QLineEdit()
        self.bib_input.setPlaceholderText("Digita pettorale e premi Invio…")
        self.bib_input.setFixedWidth(180)
        self.bib_input.returnPressed.connect(self._on_registra_bib)
        bib_bar.addWidget(self.bib_input)
        btn_registra = QPushButton("Registra")
        btn_registra.clicked.connect(self._on_registra_bib)
        bib_bar.addWidget(btn_registra)
        bib_bar.addStretch()
        self.btn_undo = QPushButton("↩ Annulla ultimo")
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_undo.setEnabled(False)
        bib_bar.addWidget(self.btn_undo)
        root.addLayout(bib_bar)

    # ── Caricamento gara ──────────────────────────────────────────────────

    def set_gara(self, gara_id: int) -> None:
        self._stop_thread()
        self._gara_id = gara_id
        conn = get_connection()
        gara = qg.get_by_id(conn, gara_id)
        if not gara:
            return

        ev = qev.get_by_id(conn, gara.evento_id)
        ev_nome = ev.nome if ev else ""
        self.lbl_gara.setText(f"{gara.nome} — {ev_nome}")

        if self._display:
            self._display.set_gara_label(f"{gara.nome} | {ev_nome}")

        if gara.stato == 'bozza':
            self._set_stato_bozza()
        elif gara.stato == 'in_corso':
            self._ripristina_in_corso(gara)
        else:
            self._set_stato_conclusa()

        self._refresh_arrivi()
        self._refresh_in_gara()

    def _set_stato_bozza(self) -> None:
        self.btn_avvia.setVisible(True)
        self.btn_avvia.setEnabled(True)
        self.btn_concludi.setVisible(False)
        self.btn_apri_display.setEnabled(False)
        self.lbl_stato.setText("Stato: Bozza — premi Avvia per iniziare")
        self.bib_input.setEnabled(False)
        self.btn_undo.setEnabled(False)

    def _ripristina_in_corso(self, gara) -> None:
        # Ricostruisce start_ts dal wall clock se la sessione è diversa
        if gara.start_wall:
            try:
                start_wall_dt = datetime.fromisoformat(gara.start_wall)
                elapsed_s = (datetime.now() - start_wall_dt).total_seconds()
                self._start_ts = time.perf_counter() - elapsed_s
            except Exception:
                self._start_ts = time.perf_counter()
        else:
            self._start_ts = time.perf_counter()
        self._avvia_thread()
        self.btn_avvia.setVisible(False)
        self.btn_concludi.setVisible(True)
        self.btn_apri_display.setEnabled(True)
        self.lbl_stato.setText("Stato: In corso")
        self.bib_input.setEnabled(True)
        self.bib_input.setFocus()

    def _set_stato_conclusa(self) -> None:
        self._stop_thread()
        self.btn_avvia.setVisible(False)
        self.btn_concludi.setVisible(False)
        self.btn_apri_display.setEnabled(True)
        self.lbl_stato.setText("Stato: Conclusa")
        self.bib_input.setEnabled(False)
        self.btn_undo.setEnabled(False)

    # ── Thread ────────────────────────────────────────────────────────────

    def _avvia_thread(self) -> None:
        self._thread = CronoThread(self._start_ts)
        self._thread.tick.connect(self._on_tick)
        if self._display:
            self._thread.tick.connect(self._display.on_tick)
        self._thread.start()

    def _stop_thread(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.stop()
        self._thread = None

    # ── Slot tick ─────────────────────────────────────────────────────────

    def _on_tick(self, elapsed_ms: int) -> None:
        self.lbl_timer.setText(ms_to_str(elapsed_ms))

    # ── Avvia / Concludi ──────────────────────────────────────────────────

    def _on_avvia(self) -> None:
        if not self._gara_id:
            return
        conn = get_connection()
        gara = qg.get_by_id(conn, self._gara_id)
        if not gara:
            return

        n = qg.count_iscritti(conn, self._gara_id)
        if n == 0:
            QMessageBox.warning(self, "Nessun atleta", "Iscrivere almeno un atleta prima di avviare la gara.")
            return

        try:
            crea_backup(gara.nome)
        except Exception as e:
            QMessageBox.warning(self, "Backup fallito", f"Impossibile creare il backup:\n{e}\n\nProcedo comunque.")

        # ── Avvio multi-gara: check altre gare bozza nello stesso evento ──
        gare_bozza = [g for g in qg.get_by_evento(conn, gara.evento_id)
                      if g.stato == 'bozza']
        avvia_tutte = False
        if len(gare_bozza) > 1:
            msg = QMessageBox(self)
            msg.setWindowTitle("Avvio gara")
            nomi_bozza = "\n".join(f"  • {g.nome}" for g in gare_bozza)
            msg.setText(
                f"L'evento ha {len(gare_bozza)} gare ancora in bozza:\n{nomi_bozza}"
            )
            msg.setInformativeText("Come vuoi procedere?")
            btn_solo  = msg.addButton(f"Solo «{gara.nome}»",  QMessageBox.ButtonRole.AcceptRole)
            btn_tutte = msg.addButton("Avvia tutte le gare",  QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Annulla",                          QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_tutte:
                avvia_tutte = True
            elif clicked != btn_solo:
                return          # Annulla o X

        self._start_ts = time.perf_counter()
        start_wall = datetime.now().isoformat()
        if avvia_tutte:
            for g in gare_bozza:
                qg.avvia_gara(conn, g.id, self._start_ts, start_wall)
        else:
            qg.avvia_gara(conn, self._gara_id, self._start_ts, start_wall)

        self._avvia_thread()
        self.btn_avvia.setVisible(False)
        self.btn_concludi.setVisible(True)
        self.btn_apri_display.setEnabled(True)
        self.lbl_stato.setText("Stato: In corso")
        self.bib_input.setEnabled(True)
        self.bib_input.setFocus()

    def _on_concludi(self) -> None:
        if QMessageBox.question(
            self, "Concludi gara", "Concludere la gara? Non sarà più possibile registrare nuovi arrivi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self._stop_thread()
        qg.concludi_gara(get_connection(), self._gara_id)
        self._set_stato_conclusa()

    # ── Registrazione arrivo ──────────────────────────────────────────────

    def _registra_arrivo(self, iscrizione_id: int, pettorale: str) -> None:
        """Nucleo atomico: cattura il tempo, scrive nel DB, aggiorna entrambe le finestre."""
        t_arrivo = time.perf_counter()
        delta_ms = round((t_arrivo - self._start_ts) * 1000)

        conn = get_connection()
        ordine = qr.count_arrivi(conn, self._gara_id) + 1

        try:
            qr.insert_arrivo(conn, iscrizione_id, delta_ms, ordine)
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Impossibile registrare l'arrivo:\n{e}")
            return

        tempo_str = ms_to_str(delta_ms)

        # Aggiorna tabella arrivi operatore
        row = self.tbl_arrivi.rowCount()
        self.tbl_arrivi.insertRow(row)
        iscrizioni_map = self._get_iscrizioni_map()
        iscr = iscrizioni_map.get(iscrizione_id)
        nome = f"{iscr.atleta_cognome} {iscr.atleta_nome}" if iscr else pettorale
        categoria = iscr.categoria_effettiva or "" if iscr else ""
        for col, text in enumerate([str(ordine), pettorale, nome, tempo_str]):
            self.tbl_arrivi.setItem(row, col, QTableWidgetItem(text))
        self.tbl_arrivi.scrollToBottom()
        self.lbl_arrivi_count.setText(f"Arrivati: {ordine}")

        # Rimuovi dalla tabella in gara
        self._rimuovi_da_in_gara(iscrizione_id)

        self.btn_undo.setEnabled(True)

        # Notifica display
        self.arrivoConfermato.emit(pettorale, ordine, tempo_str, nome, categoria)
        if self._display:
            self._display.on_arrivo_confermato(pettorale, ordine, tempo_str, nome, categoria)

    def _on_arrivato_click(self, iscrizione_id: int, pettorale: str) -> None:
        if not self._thread or not self._thread.isRunning():
            return
        self._registra_arrivo(iscrizione_id, pettorale)
        self.bib_input.setFocus()

    def _on_registra_bib(self) -> None:
        if not self._thread or not self._thread.isRunning():
            return
        bib = self.bib_input.text().strip()
        if not bib:
            return
        self.bib_input.clear()

        # Cerca l'iscrizione per pettorale
        iscrizioni_map = self._get_iscrizioni_map()
        target = None
        for iscr in iscrizioni_map.values():
            if iscr.pettorale == bib:
                # Controlla che non sia già arrivato
                arrivati = qr.get_iscritti_arrivati_ids(get_connection(), self._gara_id)
                if iscr.id not in arrivati:
                    target = iscr
                    break

        if target is None:
            QMessageBox.warning(self, "Pettorale non trovato",
                                f"Nessun atleta in gara con pettorale «{bib}».")
            self.bib_input.setFocus()
            return

        self._registra_arrivo(target.id, bib)
        self.bib_input.setFocus()

    # ── Undo ─────────────────────────────────────────────────────────────

    def _on_undo(self) -> None:
        conn = get_connection()
        ultimo = qr.get_ultimo_arrivo(conn, self._gara_id)
        if not ultimo:
            self.btn_undo.setEnabled(False)
            return

        if QMessageBox.question(
            self, "Annulla ultimo arrivo",
            f"Annullare l'arrivo di «{ultimo.nome_atleta}» (pett. {ultimo.pettorale})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        qr.delete_by_id(conn, ultimo.id)

        # Rimuovi dall'ultima riga della tabella arrivi
        last_row = self.tbl_arrivi.rowCount() - 1
        if last_row >= 0:
            self.tbl_arrivi.removeRow(last_row)
        n = qr.count_arrivi(conn, self._gara_id)
        self.lbl_arrivi_count.setText(f"Arrivati: {n}")

        # Rimetti l'atleta in gara
        self._refresh_in_gara()
        self.btn_undo.setEnabled(n > 0)

        # Notifica display
        self.arrivoAnnullato.emit(ultimo.ordine_arrivo or 0)
        if self._display:
            self._display.on_arrivo_annullato(ultimo.ordine_arrivo or 0)

    # ── Display ───────────────────────────────────────────────────────────

    def _on_apri_display(self) -> None:
        if self._display is None or not self._display.isVisible():
            gara = qg.get_by_id(get_connection(), self._gara_id)
            nome = gara.nome if gara else "Gara"
            self._display = CronoDisplay(nome)
            if self._thread:
                self._thread.tick.connect(self._display.on_tick)
            self._display.carica_arrivi(qr.get_arrivi(get_connection(), self._gara_id))
        self._display.show()
        self._display.raise_()

    # ── Refresh tabelle ───────────────────────────────────────────────────

    def _refresh_arrivi(self) -> None:
        if not self._gara_id:
            return
        arrivi = qr.get_arrivi(get_connection(), self._gara_id)
        self.tbl_arrivi.setRowCount(0)
        for r in arrivi:
            row = self.tbl_arrivi.rowCount()
            self.tbl_arrivi.insertRow(row)
            tempo_str = ms_to_str(r.tempo_ms) if r.tempo_ms is not None else "—"
            for col, text in enumerate([str(r.ordine_arrivo), r.pettorale or "", r.nome_atleta, tempo_str]):
                self.tbl_arrivi.setItem(row, col, QTableWidgetItem(text))
        self.lbl_arrivi_count.setText(f"Arrivati: {len(arrivi)}")
        self.btn_undo.setEnabled(len(arrivi) > 0 and self._thread and self._thread.isRunning())

    def _refresh_in_gara(self) -> None:
        if not self._gara_id:
            return
        conn = get_connection()
        iscrizioni = qg.get_iscrizioni(conn, self._gara_id)
        arrivati_ids = qr.get_iscritti_arrivati_ids(conn, self._gara_id)

        self.tbl_in_gara.setRowCount(0)
        self._iscrizioni_cache = {i.id: i for i in iscrizioni}

        for iscr in iscrizioni:
            if iscr.id in arrivati_ids:
                continue
            row = self.tbl_in_gara.rowCount()
            self.tbl_in_gara.insertRow(row)

            # Pettorale (bold, grande)
            item_pett = QTableWidgetItem(iscr.pettorale)
            item_pett.setFont(QFont("", 14, QFont.Weight.Bold))
            item_pett.setData(_ID_ROLE, iscr.id)
            self.tbl_in_gara.setItem(row, 0, item_pett)

            self.tbl_in_gara.setItem(row, 1, QTableWidgetItem(iscr.nome_atleta))

            # Pulsante Arrivato
            btn = QPushButton("Arrivato")
            btn.setStyleSheet(
                "background-color: #16a34a; color: white; border-radius: 4px; padding: 4px 12px;"
            )
            iscr_id = iscr.id
            pett = iscr.pettorale
            btn.clicked.connect(lambda checked, i=iscr_id, p=pett: self._on_arrivato_click(i, p))
            self.tbl_in_gara.setCellWidget(row, 2, btn)

        n_rimasti = self.tbl_in_gara.rowCount()
        self.lbl_in_gara.setText(f"In gara: {n_rimasti}")

    def _rimuovi_da_in_gara(self, iscrizione_id: int) -> None:
        for row in range(self.tbl_in_gara.rowCount()):
            item = self.tbl_in_gara.item(row, 0)
            if item and item.data(_ID_ROLE) == iscrizione_id:
                self.tbl_in_gara.removeRow(row)
                break
        n = self.tbl_in_gara.rowCount()
        self.lbl_in_gara.setText(f"In gara: {n}")

    def _get_iscrizioni_map(self) -> dict:
        if not hasattr(self, '_iscrizioni_cache'):
            self._refresh_in_gara()
        return getattr(self, '_iscrizioni_cache', {})

    # ── Indietro ──────────────────────────────────────────────────────────

    def _on_indietro(self) -> None:
        if self._thread and self._thread.isRunning():
            if QMessageBox.question(
                self, "Gara in corso",
                "La gara è in corso. Tornare indietro non fermerà il timer. Continuare?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
        self.indietro.emit()
