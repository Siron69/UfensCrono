import time
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QMessageBox, QHeaderView, QMenu,
    QDialog, QFormLayout, QDialogButtonBox, QTimeEdit, QRadioButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTime
from PyQt6.QtGui import QFont


# ── Dialog: scelta orario di partenza ────────────────────────────────────────

class StartGaraDialog(QDialog):
    """Chiede all'operatore se partire adesso o con un orario personalizzato."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Avvio gara — orario di partenza")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Scegli l'orario di partenza:"))

        self._rb_adesso = QRadioButton("Adesso")
        self._rb_adesso.setChecked(True)
        self._rb_custom = QRadioButton("Orario personalizzato:")

        grp = QButtonGroup(self)
        grp.addButton(self._rb_adesso)
        grp.addButton(self._rb_custom)

        layout.addWidget(self._rb_adesso)

        row = QHBoxLayout()
        row.addWidget(self._rb_custom)
        self._time_edit = QTimeEdit(QTime.currentTime())
        self._time_edit.setDisplayFormat("HH:mm:ss")
        self._time_edit.setEnabled(False)
        row.addWidget(self._time_edit)
        layout.addLayout(row)

        self._rb_custom.toggled.connect(self._time_edit.setEnabled)

        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self._lbl_info)
        self._time_edit.timeChanged.connect(self._aggiorna_info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _aggiorna_info(self) -> None:
        if not self._rb_custom.isChecked():
            self._lbl_info.setText("")
            return
        elapsed = self._elapsed_seconds()
        if elapsed is None:
            return
        if elapsed < 0:
            self._lbl_info.setText(
                f"⚠ Orario nel futuro (+{-elapsed:.0f}s) — verrà accettato solo se ≤5 min"
            )
        else:
            h, rem = divmod(int(elapsed), 3600)
            m, s  = divmod(rem, 60)
            self._lbl_info.setText(f"Il timer partirà da  {h}:{m:02}:{s:02}  (tempo già trascorso)")

    def _elapsed_seconds(self) -> Optional[float]:
        """Secondi trascorsi dall'orario selezionato a adesso. Negativo = futuro."""
        if self._rb_adesso.isChecked():
            return 0.0
        qt = self._time_edit.time()
        now = datetime.now()
        start_today = now.replace(
            hour=qt.hour(), minute=qt.minute(), second=qt.second(), microsecond=0
        )
        diff = (now - start_today).total_seconds()
        # Se l'orario è nella prossima ora (< -23h) consideriamolo come ieri
        if diff < -23 * 3600:
            diff += 24 * 3600
        return diff

    def _on_ok(self) -> None:
        if self._rb_custom.isChecked():
            elapsed = self._elapsed_seconds()
            if elapsed is not None and elapsed < -300:   # > 5 min nel futuro
                QMessageBox.warning(
                    self, "Orario non valido",
                    "L'orario di partenza non può essere più di 5 minuti nel futuro."
                )
                return
        self.accept()

    def get_start_info(self) -> tuple[float, str]:
        """Ritorna (start_ts, start_wall) pronti per avvia_gara().

        start_ts  — valore da passare a CronoThread (perf_counter già calibrato)
        start_wall — ISO string da salvare nel DB
        """
        if self._rb_adesso.isChecked():
            start_ts   = time.perf_counter()
            start_wall = datetime.now().isoformat()
            return start_ts, start_wall

        elapsed = self._elapsed_seconds() or 0.0
        start_ts   = time.perf_counter() - elapsed
        qt         = self._time_edit.time()
        now        = datetime.now()
        start_dt   = now.replace(
            hour=qt.hour(), minute=qt.minute(), second=qt.second(), microsecond=0
        )
        if elapsed < 0:                  # orario futuro ≤5min: usa il futuro
            start_dt = now + timedelta(seconds=-elapsed)
        start_wall = start_dt.isoformat()
        return start_ts, start_wall

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
        self._evento_id: Optional[int] = None
        self._gare_attive: list = []          # gare in_corso nell'evento corrente
        self._start_ts: float = 0.0
        self._thread: Optional[CronoThread] = None
        self._displays: dict[int, CronoDisplay] = {}  # gara_id → CronoDisplay
        self._undo_stack: list[tuple[int, int]] = []  # (gara_id, risultato_id) LIFO
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

        self.tbl_arrivi = QTableWidget(0, 5)
        self.tbl_arrivi.setHorizontalHeaderLabels(["#", "Pett.", "Atleta", "Gara", "Tempo"])
        self.tbl_arrivi.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_arrivi.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl_arrivi.verticalHeader().setVisible(False)
        self.tbl_arrivi.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_arrivi.setColumnHidden(3, True)   # visibile solo in modalità multi-gara
        al.addWidget(self.tbl_arrivi)

        splitter.addWidget(arrivi_panel)
        splitter.setSizes([320, 480])
        root.addWidget(splitter)

        # ── Tabella atleti in gara ────────────────────────────────────────
        self.lbl_in_gara = QLabel("In gara:")
        self.lbl_in_gara.setStyleSheet("font-weight: bold; margin-top: 8px;")
        root.addWidget(self.lbl_in_gara)

        self.tbl_in_gara = QTableWidget(0, 4)
        self.tbl_in_gara.setHorizontalHeaderLabels(["Pettorale", "Atleta", "Gara", ""])
        self.tbl_in_gara.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_in_gara.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl_in_gara.verticalHeader().setVisible(False)
        self.tbl_in_gara.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_in_gara.setColumnHidden(2, True)   # visibile solo in modalità multi-gara
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
        self._undo_stack = []
        conn = get_connection()
        gara = qg.get_by_id(conn, gara_id)
        if not gara:
            return
        self._evento_id = gara.evento_id

        ev = qev.get_by_id(conn, gara.evento_id)
        ev_nome = ev.nome if ev else ""
        self._ev_nome = ev_nome           # usato da _aggiorna_titolo
        self.lbl_gara.setText(f"{gara.nome} — {ev_nome}")

        # Aggiorna label sui display aperti
        for gid, display in self._displays.items():
            if display.isVisible():
                g_label = qg.get_by_id(conn, gid)
                lbl = f"{g_label.nome} | {ev_nome}" if g_label else ev_nome
                display.set_gara_label(lbl)

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
        # Connetti il tick a tutti i display aperti
        for display in self._displays.values():
            if display.isVisible():
                self._thread.tick.connect(display.on_tick)
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

        # ── Dialog: scelta orario di partenza ─────────────────────────────
        start_dlg = StartGaraDialog(self)
        if start_dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._start_ts, start_wall = start_dlg.get_start_info()

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
        # Ricarica la lista atleti ora che la gara è in_corso:
        # senza questa chiamata _gare_attive e _iscrizioni_cache restano
        # quelli costruiti quando la gara era in bozza (vuoti), impedendo
        # la registrazione degli arrivi sia da bottone che da pettorale.
        self._refresh_in_gara()
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

    def _registra_arrivo(
        self,
        iscrizione_id: int,
        pettorale: str,
        gara_id: Optional[int] = None,
    ) -> None:
        """Nucleo atomico: cattura il tempo, scrive nel DB, aggiorna entrambe le finestre."""
        if gara_id is None:
            gara_id = self._gara_id

        t_arrivo = time.perf_counter()
        delta_ms = round((t_arrivo - self._start_ts) * 1000)

        conn = get_connection()
        ordine = qr.count_arrivi(conn, gara_id) + 1

        try:
            risultato_id = qr.insert_arrivo(conn, iscrizione_id, delta_ms, ordine)
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Impossibile registrare l'arrivo:\n{e}")
            return

        self._undo_stack.append((gara_id, risultato_id))

        tempo_str = ms_to_str(delta_ms)

        # Nome gara (per colonna multi-gara)
        gara_nome = ""
        for g in self._gare_attive:
            if g.id == gara_id:
                gara_nome = g.nome
                break

        # Aggiorna tabella arrivi operatore (5 colonne: #, pett, atleta, gara, tempo)
        row = self.tbl_arrivi.rowCount()
        self.tbl_arrivi.insertRow(row)
        iscrizioni_map = self._get_iscrizioni_map()
        iscr = iscrizioni_map.get(iscrizione_id)
        nome = f"{iscr.atleta_cognome} {iscr.atleta_nome}" if iscr else pettorale
        categoria = iscr.categoria_effettiva or "" if iscr else ""
        for col, text in enumerate([str(ordine), pettorale, nome, gara_nome, tempo_str]):
            self.tbl_arrivi.setItem(row, col, QTableWidgetItem(text))
        self.tbl_arrivi.scrollToBottom()

        self._aggiorna_counter()

        # Rimuovi dalla tabella in gara
        self._rimuovi_da_in_gara(iscrizione_id)

        self.btn_undo.setEnabled(True)

        # Notifica il display della gara corretta (se aperto)
        self.arrivoConfermato.emit(pettorale, ordine, tempo_str, nome, categoria)
        display = self._displays.get(gara_id)
        if display and display.isVisible():
            display.on_arrivo_confermato(pettorale, ordine, tempo_str, nome, categoria)

    def _on_arrivato_click(self, iscrizione_id: int, pettorale: str) -> None:
        if not self._thread or not self._thread.isRunning():
            return
        iscr = self._get_iscrizioni_map().get(iscrizione_id)
        gara_id = iscr.gara_id if iscr else self._gara_id
        self._registra_arrivo(iscrizione_id, pettorale, gara_id=gara_id)
        self.bib_input.setFocus()

    def _on_registra_bib(self) -> None:
        if not self._thread or not self._thread.isRunning():
            return
        bib = self.bib_input.text().strip()
        if not bib:
            return
        self.bib_input.clear()

        # Cerca l'iscrizione per pettorale tra tutte le gare attive dell'evento
        conn = get_connection()
        iscrizioni_map = self._get_iscrizioni_map()
        target = None
        for iscr in iscrizioni_map.values():
            if iscr.pettorale == bib:
                arrivati = qr.get_iscritti_arrivati_ids(conn, iscr.gara_id)
                if iscr.id not in arrivati:
                    target = iscr
                    break

        if target is None:
            QMessageBox.warning(self, "Pettorale non trovato",
                                f"Nessun atleta in gara con pettorale «{bib}».")
            self.bib_input.setFocus()
            return

        self._registra_arrivo(target.id, bib, gara_id=target.gara_id)
        self.bib_input.setFocus()

    # ── Undo ─────────────────────────────────────────────────────────────

    def _on_undo(self) -> None:
        if not self._undo_stack:
            self.btn_undo.setEnabled(False)
            return

        gara_id, risultato_id = self._undo_stack[-1]
        conn = get_connection()

        # Recupera i dettagli per il dialog di conferma
        ultimo = qr.get_ultimo_arrivo(conn, gara_id)
        if not ultimo or ultimo.id != risultato_id:
            # Disallineamento (es. ricarica manuale): scarta e risincronizza
            self._undo_stack.pop()
            self.btn_undo.setEnabled(bool(self._undo_stack))
            return

        if QMessageBox.question(
            self, "Annulla ultimo arrivo",
            f"Annullare l'arrivo di «{ultimo.nome_atleta}» (pett. {ultimo.pettorale})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        self._undo_stack.pop()
        qr.delete_by_id(conn, risultato_id)

        # Rimuovi dall'ultima riga della tabella arrivi
        last_row = self.tbl_arrivi.rowCount() - 1
        if last_row >= 0:
            self.tbl_arrivi.removeRow(last_row)

        self._aggiorna_counter()

        # Rimetti l'atleta in gara
        self._refresh_in_gara()
        self.btn_undo.setEnabled(bool(self._undo_stack))

        # Notifica il display della gara corretta (se aperto)
        self.arrivoAnnullato.emit(ultimo.ordine_arrivo or 0)
        display = self._displays.get(gara_id)
        if display and display.isVisible():
            display.on_arrivo_annullato(ultimo.ordine_arrivo or 0)

    # ── Display ───────────────────────────────────────────────────────────

    def _on_apri_display(self) -> None:
        """Apre il display pubblico. Se ci sono più gare attive mostra un menu."""
        conn = get_connection()

        # Costruisce la lista di gare da mostrare
        if self._evento_id:
            gare_display = [g for g in qg.get_by_evento(conn, self._evento_id)
                            if g.stato in ('in_corso', 'conclusa')]
        else:
            gara = qg.get_by_id(conn, self._gara_id)
            gare_display = [gara] if gara else []

        if not gare_display:
            return

        if len(gare_display) == 1:
            self._apri_display_per_gara(gare_display[0])
            return

        # Più gare → menu con una voce per gara
        menu = QMenu(self)
        for gara in gare_display:
            action = menu.addAction(gara.nome)
            action.setData(gara.id)
        chosen = menu.exec(
            self.btn_apri_display.mapToGlobal(
                self.btn_apri_display.rect().bottomLeft()
            )
        )
        if chosen:
            gara_id = chosen.data()
            gara = next((g for g in gare_display if g.id == gara_id), None)
            if gara:
                self._apri_display_per_gara(gara)

    def _apri_display_per_gara(self, gara) -> None:
        """Crea o porta in primo piano il CronoDisplay per la gara specificata."""
        conn = get_connection()
        gara_id = gara.id
        display = self._displays.get(gara_id)

        if display is None or not display.isVisible():
            # Calcola start_ts della gara (può essere diverso da self._start_ts
            # se le gare sono state avviate con orari diversi)
            display = CronoDisplay(gara.nome)
            self._displays[gara_id] = display

            # Tutte le gare dell'evento condividono il timer (stesso start_wall)
            if self._thread:
                self._thread.tick.connect(display.on_tick)

            display.carica_arrivi(qr.get_arrivi(conn, gara_id))

        display.show()
        display.raise_()

    # ── Refresh tabelle ───────────────────────────────────────────────────

    def _refresh_arrivi(self) -> None:
        if not self._gara_id:
            return
        conn = get_connection()

        # Carica arrivi da tutte le gare dell'evento (in_corso o conclusa)
        if self._evento_id:
            tutte = qg.get_by_evento(conn, self._evento_id)
        else:
            gara = qg.get_by_id(conn, self._gara_id)
            tutte = [gara] if gara else []

        gare_con_arrivi = [g for g in tutte if g.stato in ('in_corso', 'conclusa')]
        multi_gara = len(gare_con_arrivi) > 1
        self.tbl_arrivi.setColumnHidden(3, not multi_gara)

        # Merge e ordina per tempo_ms
        all_arrivi: list[tuple] = []   # (gara, risultato)
        for g in gare_con_arrivi:
            for r in qr.get_arrivi(conn, g.id):
                all_arrivi.append((g, r))
        all_arrivi.sort(key=lambda x: (x[1].tempo_ms or 0, x[1].ordine_arrivo or 0))

        self.tbl_arrivi.setRowCount(0)
        for idx, (gara, r) in enumerate(all_arrivi, start=1):
            row = self.tbl_arrivi.rowCount()
            self.tbl_arrivi.insertRow(row)
            tempo_str = ms_to_str(r.tempo_ms) if r.tempo_ms is not None else "—"
            texts = [str(idx), r.pettorale or "", r.nome_atleta, gara.nome, tempo_str]
            for col, text in enumerate(texts):
                self.tbl_arrivi.setItem(row, col, QTableWidgetItem(text))

        self._aggiorna_counter()
        self.btn_undo.setEnabled(
            bool(self._undo_stack) and bool(self._thread) and self._thread.isRunning()
        )

    def _refresh_in_gara(self) -> None:
        if not self._gara_id:
            return
        conn = get_connection()

        # Raccoglie tutte le gare in_corso dell'evento (cross-gara)
        if self._evento_id:
            self._gare_attive = [g for g in qg.get_by_evento(conn, self._evento_id)
                                  if g.stato == 'in_corso']
        else:
            gara = qg.get_by_id(conn, self._gara_id)
            self._gare_attive = [gara] if gara and gara.stato == 'in_corso' else []

        multi_gara = len(self._gare_attive) > 1
        self.tbl_in_gara.setColumnHidden(2, not multi_gara)

        self.tbl_in_gara.setRowCount(0)
        self._iscrizioni_cache = {}

        for gara in self._gare_attive:
            iscrizioni  = qg.get_iscrizioni(conn, gara.id)
            arrivati_ids = qr.get_iscritti_arrivati_ids(conn, gara.id)

            for iscr in iscrizioni:
                self._iscrizioni_cache[iscr.id] = iscr
                if iscr.id in arrivati_ids:
                    continue

                row = self.tbl_in_gara.rowCount()
                self.tbl_in_gara.insertRow(row)

                item_pett = QTableWidgetItem(iscr.pettorale)
                item_pett.setFont(QFont("", 14, QFont.Weight.Bold))
                item_pett.setData(_ID_ROLE, iscr.id)
                self.tbl_in_gara.setItem(row, 0, item_pett)
                self.tbl_in_gara.setItem(row, 1, QTableWidgetItem(iscr.nome_atleta))
                if multi_gara:
                    self.tbl_in_gara.setItem(row, 2, QTableWidgetItem(gara.nome))

                btn = QPushButton("Arrivato")
                btn.setStyleSheet(
                    "background-color: #16a34a; color: white; border-radius: 4px; padding: 4px 12px;"
                )
                iscr_id = iscr.id
                pett    = iscr.pettorale
                btn.clicked.connect(lambda checked, i=iscr_id, p=pett: self._on_arrivato_click(i, p))
                self.tbl_in_gara.setCellWidget(row, 3, btn)   # sempre col 3

        n_rimasti = self.tbl_in_gara.rowCount()
        self.lbl_in_gara.setText(f"In gara: {n_rimasti}")
        self._aggiorna_titolo()

    def _aggiorna_titolo(self) -> None:
        """Aggiorna lbl_gara: modalità evento se più gare attive, altrimenti per-gara."""
        ev_nome = getattr(self, '_ev_nome', '')
        if len(self._gare_attive) > 1:
            self.lbl_gara.setText(f"{ev_nome} — Cronometro evento")
        else:
            conn = get_connection()
            gara = qg.get_by_id(conn, self._gara_id) if self._gara_id else None
            nome = gara.nome if gara else "Cronometro"
            self.lbl_gara.setText(f"{nome} — {ev_nome}" if ev_nome else nome)

    def _aggiorna_counter(self) -> None:
        """Aggiorna il label 'Arrivati' con conteggio per-gara se multi-gara."""
        conn = get_connection()
        if len(self._gare_attive) <= 1:
            n = qr.count_arrivi(conn, self._gara_id) if self._gara_id else 0
            self.lbl_arrivi_count.setText(f"Arrivati: {n}")
        else:
            parts = []
            tot = 0
            for g in self._gare_attive:
                n = qr.count_arrivi(conn, g.id)
                parts.append(f"{g.nome}: {n}")
                tot += n
            self.lbl_arrivi_count.setText(
                f"Arrivati: {tot}  (" + "  |  ".join(parts) + ")"
            )

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
