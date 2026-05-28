# UfensCrono — Documentazione Tecnica

> Applicazione desktop Windows per la gestione e il cronometraggio di gare sportive.
> Single-user · Offline · Portable `.exe`

---

## Indice

1. [Stack tecnologico](#1-stack-tecnologico)
2. [Struttura del progetto](#2-struttura-del-progetto)
3. [Modello dati](#3-modello-dati)
4. [Import anagrafiche da XLSX](#4-import-anagrafiche-da-xlsx)
5. [Gestione Atleti](#5-gestione-atleti)
6. [Modello Evento / Gara](#6-modello-evento--gara)
7. [Schermata Cronometro](#7-schermata-cronometro)
8. [Classifiche](#8-classifiche)
9. [Export](#9-export)
10. [Architettura UI (PyQt6)](#10-architettura-ui-pyqt6)
11. [Thread safety e timer](#11-thread-safety-e-timer)
12. [Packaging](#12-packaging)
13. [Dipendenze](#13-dipendenze)
14. [Convenzioni di codice](#14-convenzioni-di-codice)
15. [Open points](#15-open-points)

---

## 1. Stack tecnologico

| Layer | Scelta | Versione minima |
|---|---|---|
| Linguaggio | Python | 3.11 |
| GUI | PyQt6 | 6.6.0 |
| Database | SQLite 3 (stdlib) | — |
| Lettura XLSX | openpyxl | 3.1 |
| Export Excel | openpyxl | 3.1 |
| Export PDF | reportlab | 4.0 |
| Packaging | PyInstaller | 6.0 |

**Nessun ORM.** Si usa `sqlite3` della stdlib con query SQL esplicite e dataclass Python come
layer di rappresentazione. Questa scelta mantiene il codice leggibile e le dipendenze minime.

---

## 2. Struttura del progetto

```
ufenscrono/
├── main.py                    # entry point: QApplication + MainWindow
│
├── db/
│   ├── __init__.py
│   ├── connection.py          # singleton connessione SQLite, init schema
│   ├── migrations.py          # versioning schema (tabella _schema_version)
│   └── queries/
│       ├── atleti.py          # CRUD atleti
│       ├── eventi.py          # CRUD eventi
│       ├── gare.py            # CRUD gare + iscrizioni
│       └── risultati.py       # lettura/scrittura tempi, classifiche
│
├── models/
│   ├── atleta.py              # dataclass Atleta
│   ├── evento.py              # dataclass Evento
│   ├── gara.py                # dataclass Gara, Iscrizione
│   └── risultato.py           # dataclass Risultato
│
├── ui/
│   ├── main_window.py         # QMainWindow, sidebar navigazione
│   ├── atleti/
│   │   ├── lista.py           # QTableWidget lista atleti + ricerca
│   │   ├── form.py            # form inserimento/modifica atleta
│   │   └── import_xlsx.py     # wizard import da file XLSX
│   ├── eventi/
│   │   ├── lista.py           # lista eventi
│   │   └── form.py            # form crea/modifica evento
│   ├── gare/
│   │   ├── lista.py           # gare di un evento
│   │   ├── form.py            # form crea/modifica gara
│   │   └── iscrizioni.py      # assegnazione atleti a una gara
│   └── cronometro/
│       ├── schermata.py       # schermata live: timer + arrivi
│       └── classifica.py      # vista classifica post-gara
│
├── logic/
│   ├── timer.py               # QThread con perf_counter
│   ├── categorie.py           # calcolo categoria da data_nascita + anno gara
│   ├── import_xlsx.py         # parsing e mapping colonne XLSX → Atleta
│   └── classifica.py          # ranking, filtri categoria/sesso
│
├── export/
│   ├── excel.py               # openpyxl
│   └── pdf.py                 # reportlab
│
├── assets/
│   ├── logo.png
│   └── icons/
│
├── requirements.txt
└── build.spec                 # configurazione PyInstaller
```

---

## 3. Modello dati

### 3.1 Schema SQLite completo

```sql
-- Versioning schema
CREATE TABLE IF NOT EXISTS _schema_version (
    version     INTEGER NOT NULL
);

-- ────────────────────────────────────────────
-- ATLETI
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS atleti (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL,
    cognome         TEXT    NOT NULL,
    sesso           TEXT    NOT NULL CHECK(sesso IN ('M', 'F')),
    data_nascita    TEXT    NOT NULL,          -- ISO: YYYY-MM-DD
    luogo_nascita   TEXT,
    nazionalita     TEXT    DEFAULT 'ITA',
    codice_fiscale  TEXT,
    societa         TEXT,
    codice_societa  TEXT,
    tessera         TEXT,
    tessera2        TEXT,
    ente            TEXT,
    categoria       TEXT,                     -- categoria dichiarata all'iscrizione
    scad_certificato TEXT,                    -- YYYY-MM-DD
    stato_cert      TEXT,
    telefono        TEXT,
    cellulare       TEXT,
    email           TEXT,
    note            TEXT,
    -- import tracking
    source_id       TEXT,                     -- ID riga del file XLSX sorgente
    source_order_id TEXT,                     -- Order ID del sito iscrizioni
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────────
-- EVENTI
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eventi (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    data        TEXT    NOT NULL,             -- YYYY-MM-DD
    luogo       TEXT,
    note        TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────────
-- GARE  (appartenenti a un evento)
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gare (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id       INTEGER NOT NULL REFERENCES eventi(id) ON DELETE CASCADE,
    nome            TEXT    NOT NULL,         -- es. "10 km", "20 km", "Staffetta"
    tipo            TEXT,                     -- es. "corsa", "ciclismo", "sci"
    distanza_m      INTEGER,
    stato           TEXT    NOT NULL DEFAULT 'bozza'
                            CHECK(stato IN ('bozza','in_corso','conclusa')),
    start_ts        REAL,                     -- time.perf_counter() epoch al via
    start_wall      TEXT,                     -- datetime reale dello start (ISO)
    note            TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────────
-- ISCRIZIONI  (atleta ↔ gara, con pettorale)
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS iscrizioni (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    gara_id         INTEGER NOT NULL REFERENCES gare(id) ON DELETE CASCADE,
    atleta_id       INTEGER NOT NULL REFERENCES atleti(id),
    pettorale       TEXT    NOT NULL,         -- TEXT: supporta pettorali alfanumerici
    pettorale_circ  TEXT,                     -- "Pettorale circuito" dal file import
    codice_chip     TEXT,
    quota           TEXT,                     -- "Quota" dal file import
    stato_lw        TEXT,                     -- "Stato LW" (Long Walk / categoria speciale)
    partecipa       INTEGER NOT NULL DEFAULT 1,  -- 0 = DNS
    UNIQUE(gara_id, pettorale),
    UNIQUE(gara_id, atleta_id)
);

-- ────────────────────────────────────────────
-- RISULTATI
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risultati (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    iscrizione_id   INTEGER NOT NULL REFERENCES iscrizioni(id) ON DELETE CASCADE,
    tempo_ms        INTEGER,                  -- delta in ms dal via (rilevato da click)
    tempo_override  TEXT,                     -- es. "1:23:45.678" (modifica manuale)
    stato           TEXT    NOT NULL DEFAULT 'ok'
                            CHECK(stato IN ('ok','dsq','dnf','dns')),
    ordine_arrivo   INTEGER,                  -- posizione di click (1° a fare click = 1)
    note_arbitro    TEXT,
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────────
-- CATEGORIE  (configurabili)
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categorie (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,             -- es. "Allievi M", "Seniores F"
    sesso       TEXT    NOT NULL DEFAULT 'MF' CHECK(sesso IN ('M','F','MF')),
    eta_min     INTEGER,
    eta_max     INTEGER,                      -- NULL = nessun limite superiore
    ordine      INTEGER DEFAULT 0
);
```

---

### 3.2 Relazioni (ERD testuale)

```
eventi  (1) ──────────── (N)  gare
                               │
                               │ (N)
                          iscrizioni  ──── (1)  atleti
                               │
                               │ (1)
                          risultati
```

### 3.3 Logica campo `tempo_override`

Nelle query di classifica si usa sempre:

```sql
COALESCE(r.tempo_override, r.tempo_ms) AS tempo_finale
```

Questo garantisce che la modifica manuale prevalga, **senza perdere il dato originale rilevato**.
Il campo `tempo_override` viene formattato come stringa `H:MM:SS.mmm` e riconvertito in ms
per i confronti e l'ordinamento.

---

## 4. Import anagrafiche da XLSX

### 4.1 Header del file sorgente (sito di iscrizioni)

```
ID | Order ID | Evento | Gruppo | Quota | ID Quota | Pettorale | Pettorale circuito |
Codice chip | Nome | Cognome | Sesso | Data nascita | Luogo di nascita | Nazionalità |
Codice fiscale | Tessera | Tessera2 | Ente | Codice società | Società | Scadenza tessera |
Stato tessera | Categoria | Categoria reale | Tesserino giornaliero | Scadenza certificato |
Stato certificato | Stato LW | Indirizzo | Città | CAP | Provincia | Stato |
Telefono | Cellulare | E-mail
```

### 4.2 Mapping colonne → modello dati

| Colonna XLSX | Campo DB | Tabella | Note |
|---|---|---|---|
| `ID` | `source_id` | atleti | Tenuto per deduplicazione re-import |
| `Order ID` | `source_order_id` | atleti | Tenuto per riferimento ordine |
| `Nome` | `nome` | atleti | — |
| `Cognome` | `cognome` | atleti | — |
| `Sesso` | `sesso` | atleti | Normalizzare: `M`/`F` |
| `Data nascita` | `data_nascita` | atleti | Convertire in `YYYY-MM-DD` |
| `Luogo di nascita` | `luogo_nascita` | atleti | — |
| `Nazionalità` | `nazionalita` | atleti | — |
| `Codice fiscale` | `codice_fiscale` | atleti | — |
| `Tessera` | `tessera` | atleti | — |
| `Tessera2` | `tessera2` | atleti | — |
| `Ente` | `ente` | atleti | — |
| `Codice società` | `codice_societa` | atleti | — |
| `Società` | `societa` | atleti | — |
| `Categoria` | `categoria` | atleti | Categoria dichiarata all'iscrizione |
| `Scadenza certificato` | `scad_certificato` | atleti | Convertire in `YYYY-MM-DD` |
| `Stato certificato` | `stato_cert` | atleti | — |
| `Telefono` | `telefono` | atleti | — |
| `Cellulare` | `cellulare` | atleti | — |
| `E-mail` | `email` | atleti | — |
| `Pettorale` | `pettorale` | iscrizioni | Legato alla gara target dell'import |
| `Pettorale circuito` | `pettorale_circ` | iscrizioni | — |
| `Codice chip` | `codice_chip` | iscrizioni | — |
| `Quota` | `quota` | iscrizioni | — |
| `Stato LW` | `stato_lw` | iscrizioni | — |

**Colonne XLSX ignorate:** `Evento`, `Gruppo`, `ID Quota`, `Scadenza tessera`, `Stato tessera`,
`Categoria reale`, `Tesserino giornaliero`, `Indirizzo`, `Città`, `CAP`, `Provincia`, `Stato`.

> Queste colonne possono essere salvate in futuro se necessario, senza modifiche allo schema
> (aggiungere colonne nullable è retro-compatibile in SQLite).

### 4.3 Logica di import (`logic/import_xlsx.py`)

```python
def importa_xlsx(path: str, gara_id: int) -> ImportResult:
    """
    Legge il file XLSX, mappa le colonne, inserisce/aggiorna atleti
    e crea le iscrizioni per la gara specificata.

    Restituisce ImportResult con:
      - n_inseriti: nuovi atleti creati
      - n_aggiornati: atleti già esistenti aggiornati
      - n_iscrizioni: iscrizioni create
      - errori: lista di righe con problemi (numero riga + messaggio)
    """
```

**Strategia deduplicazione atleti:**

1. Cerca per `codice_fiscale` (se non vuoto)
2. Fallback: cerca per `(nome, cognome, data_nascita)`
3. Se trovato → aggiorna i campi; se non trovato → inserisce nuovo

**Normalizzazioni obbligatorie:**

- `Sesso`: `"M"`, `"F"`, case-insensitive, strip spazi
- `Data nascita`: supportare formati `DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`
  → salvare sempre come `YYYY-MM-DD`
- `Scadenza certificato`: stessa logica date
- `Pettorale`: cast a stringa, strip spazi

### 4.4 Wizard UI (`ui/atleti/import_xlsx.py`)

Flusso in 3 step:

```
Step 1 – Seleziona file XLSX
         └─ QFileDialog → mostra anteprima prime 5 righe

Step 2 – Seleziona gara target
         └─ ComboBox eventi → ComboBox gare
         └─ Checkbox "crea nuova gara automaticamente"

Step 3 – Conferma e import
         └─ Tabella di anteprima mapping
         └─ Pulsante "Importa"
         └─ Progress bar + report finale (n inseriti / aggiornati / errori)
```

---

## 5. Gestione Atleti

### 5.1 Lista atleti

- `QTableWidget` con colonne: Cognome, Nome, Sesso, Data nascita, Categoria (calcolata), Società, Tessera
- Filtro per testo (ricerca live su cognome/nome/società)
- Filtro per sesso
- Ordinamento per colonna (click su header)
- Azioni: **Nuovo**, **Modifica**, **Elimina** (soft-delete: non cancella se ha iscrizioni)

### 5.2 Form atleta (inserimento / modifica)

Campi obbligatori: Nome, Cognome, Sesso, Data di nascita.

Campi facoltativi: Luogo di nascita, Nazionalità, Codice fiscale, Società, Codice società, Ente,
Tessera, Tessera2, Scadenza certificato, Stato certificato, Telefono, Cellulare, Email, Note.

**Validazioni:**
- Data di nascita: formato valido, non futura
- Codice fiscale: lunghezza 16 se valorizzato
- Email: formato base (presenza `@`)

---

## 6. Modello Evento / Gara

### 6.1 Gerarchia

```
Evento  (es. "Corsa dei Castelli 2025", 15/09/2025, Ferentino)
  └── Gara A  (es. "10 km")
  │     └── Iscrizione atleta 1 → pettorale 001
  │     └── Iscrizione atleta 2 → pettorale 002
  └── Gara B  (es. "20 km")
        └── Iscrizione atleta 3 → pettorale 001  ← stesso pettorale, gara diversa: OK
```

Un atleta può essere iscritto a più gare dello stesso evento (es. prima fa la 10km, poi la 20km).
Il vincolo `UNIQUE(gara_id, pettorale)` agisce a livello di singola gara.

### 6.2 Ciclo di vita della gara

```
bozza ──► in_corso ──► conclusa
            │
            └── (start_ts viene registrato qui)
```

- **bozza**: si possono aggiungere/rimuovere atleti e modificare dati
- **in_corso**: il timer è attivo; le iscrizioni sono bloccate
- **conclusa**: sola lettura; i tempi possono essere modificati manualmente dall'operatore

### 6.3 Assegnazione atleti a una gara

Dalla schermata `ui/gare/iscrizioni.py`:

- Lista sinistra: **atleti disponibili** (tutti gli atleti del DB, non già iscritti a quella gara)
- Lista destra: **atleti iscritti** alla gara, con pettorale
- Trascinamento (drag & drop) o doppio-click per spostare
- Campo pettorale editabile inline nella lista destra
- Import da XLSX direttamente in questa schermata (pre-popola la lista destra)

---

## 7. Schermata Cronometro

### 7.1 Layout

```
┌─────────────────────────────────────────────────────────┐
│  UfensCrono  ·  Gara: 10 km  ·  Evento: Corsa Castelli  │
├────────────────────┬────────────────────────────────────┤
│                    │  ARRIVATI                          │
│   01:23:45.678     │  ─────────────────────────────     │
│                    │  #1  001  ROSSI Mario    01:10:32  │
│  [ START / STOP ]  │  #2  045  BIANCHI Luca   01:15:44  │
│                    │  ─────────────────────────────     │
├────────────────────┴────────────────────────────────────┤
│  IN GARA (click per registrare arrivo)                  │
│  ┌──────┬─────────────────────────┬──────────────────┐  │
│  │ 001  │ ROSSI Mario             │  [Arrivato]      │  │
│  │ 002  │ VERDI Anna              │  [Arrivato]      │  │
│  │ 045  │ BIANCHI Luca            │  [Arrivato]      │  │
│  └──────┴─────────────────────────┴──────────────────┘  │
│  Inserimento rapido pettorale: [____] [Registra]        │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Comportamento al click "Arrivato"

1. Legge il `perf_counter()` corrente → `t_arrivo`
2. `delta_ms = round((t_arrivo - start_ts) * 1000)`
3. `ordine_arrivo = len(arrivati) + 1`
4. Inserisce/aggiorna `risultati` con `(iscrizione_id, tempo_ms, ordine_arrivo)`
5. Sposta il bottone dell'atleta dalla lista "In gara" alla sezione "Arrivati"
6. Operazione atomica: tutto o niente (try/except + rollback)

### 7.3 Inserimento rapido da pettorale

L'operatore digita il numero di pettorale e preme Invio (o clicca "Registra").
Utile quando si usa la tastiera invece del mouse durante l'arrivo di gruppo.
Il campo è sempre in focus durante la gara (non serve cliccare sul campo prima di digitare).

### 7.4 Annulla ultimo arrivo

Pulsante "Annulla ultimo" visibile durante la gara:
- Rimuove l'ultimo `risultati` inserito
- Riporta l'atleta nella lista "In gara"
- Log dell'operazione in `note_arbitro`

### 7.5 Backup automatico pre-start

Prima di impostare `stato = 'in_corso'` e registrare `start_ts`, l'app:

```python
backup_path = f"data/backup/{nome_gara}_{datetime.now():%Y%m%d_%H%M%S}.db"
shutil.copy2("data/ufenscrono.db", backup_path)
```

---

## 8. Classifiche

### 8.1 Query base (classifica generale)

```sql
SELECT
    r.ordine_arrivo,
    i.pettorale,
    a.cognome,
    a.nome,
    a.sesso,
    strftime('%Y', 'now') - strftime('%Y', a.data_nascita) AS eta,
    a.societa,
    COALESCE(r.tempo_override, r.tempo_ms) AS tempo_finale,
    r.stato
FROM risultati r
JOIN iscrizioni i  ON i.id = r.iscrizione_id
JOIN atleti a      ON a.id = i.atleta_id
WHERE i.gara_id = ?
  AND r.stato = 'ok'
ORDER BY tempo_finale ASC;
```

### 8.2 Filtri disponibili

- Per sesso: `AND a.sesso = 'M'` / `AND a.sesso = 'F'`
- Per categoria: join con logica in Python (`logic/categorie.py`) oppure `CASE` inline in SQL
- Escludi stati: `AND r.stato NOT IN ('dsq', 'dns', 'dnf')`

### 8.3 Modifica manuale tempi

Dalla schermata classifica, doppio-click sulla cella tempo:
- Si apre un QDialog con campo testo formato `H:MM:SS.mmm`
- Validazione formato e range (> 0, < 24h)
- Salva in `tempo_override`; il campo `tempo_ms` originale non viene toccato
- La riga viene evidenziata con colore diverso per indicare "tempo modificato manualmente"

---

## 9. Export

### 9.1 Excel (openpyxl)

- Foglio 1: Classifica generale
- Foglio 2: Classifica M
- Foglio 3: Classifica F
- Fogli aggiuntivi: uno per categoria (se presenti)
- Header con nome gara, evento, data
- Colonne: Pos., Pettorale, Cognome, Nome, Sesso, Anno, Società, Tempo, Stato

### 9.2 PDF (reportlab)

- Intestazione con logo (se presente in `assets/logo.png`) e nome evento/gara
- Tabella classifica con righe alternate (zebratura)
- Footer con data di stampa e pagina N/M
- Formato A4 verticale; font Helvetica

---

## 10. Architettura UI (PyQt6)

### 10.1 MainWindow e navigazione

```python
class MainWindow(QMainWindow):
    # Sidebar sinistra: bottoni sezioni
    # QStackedWidget al centro: pannelli
    # Sezioni: Atleti | Eventi | Gare | Cronometro | Classifiche
```

### 10.2 Segnali e slot

Ogni schermata emette segnali tipizzati. Esempi:

```python
# In AtletiLista:
atleta_selezionato = pyqtSignal(int)       # atleta_id
importa_richiesto  = pyqtSignal()

# In CronomentroSchermata:
atleta_arrivato    = pyqtSignal(int, int)  # iscrizione_id, tempo_ms
gara_conclusa      = pyqtSignal(int)       # gara_id
```

### 10.3 Refresh dati

Le schermate non mantengono stato locale oltre al necessario.
Ogni volta che la schermata viene portata in primo piano, chiama `refresh()` che
rilegge dal DB. Questo evita problemi di sincronizzazione tra pannelli.

---

## 11. Thread safety e timer

```python
# logic/timer.py
class CronoThread(QThread):
    tick = pyqtSignal(int)   # emette ms trascorsi ogni ~50ms

    def __init__(self, start_ts: float):
        super().__init__()
        self._start_ts = start_ts
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            elapsed_ms = round((time.perf_counter() - self._start_ts) * 1000)
            self.tick.emit(elapsed_ms)
            time.sleep(0.05)   # ~20 fps display, non influisce sulla precisione

    def stop(self):
        self._running = False
        self.wait()
```

**Regola fondamentale:** il thread emette solo segnali. Non tocca mai widget o DB direttamente.
La UI riceve il segnale `tick` nello slot `on_tick(ms)` sul thread principale e aggiorna il display.

Il tempo di arrivo viene rilevato nel thread principale (click del mouse / pressione Invio)
tramite `time.perf_counter()` nel momento esatto dell'evento, **non** dal valore del tick.
Questo garantisce la massima precisione indipendentemente dalla frequenza di refresh del display.

---

## 12. Packaging

### 12.1 Struttura distribuzione

```
UfensCrono/
├── UfensCrono.exe          # generato da PyInstaller
└── data/
    ├── ufenscrono.db       # creato al primo avvio
    ├── backup/             # backup automatici pre-gara
    └── export/             # PDF ed Excel generati
```

### 12.2 Percorso dati a runtime

```python
# utils/paths.py
import sys, os

def get_data_dir() -> str:
    """
    In sviluppo:   ./data/
    In .exe:       cartella accanto all'exe (non in sys._MEIPASS che è temporanea)
    """
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, '..', 'data')
```

### 12.3 build.spec (PyInstaller)

```python
a = Analysis(
    ['main.py'],
    datas=[('assets', 'assets')],
    hiddenimports=['openpyxl', 'reportlab'],
)
exe = EXE(a.pure, a.scripts, a.binaries, a.datas,
          name='UfensCrono',
          icon='assets/logo.ico',
          console=False)   # nessuna finestra console
```

---

## 13. Dipendenze

```
# requirements.txt
PyQt6>=6.6.0
openpyxl>=3.1.0
reportlab>=4.0.0

# solo per packaging (non incluso nel bundle)
pyinstaller>=6.0.0
```

Nessuna dipendenza di rete. L'app funziona completamente offline.

---

## 14. Convenzioni di codice

- **Lingua codice:** inglese (nomi variabili, funzioni, classi)
- **Lingua UI e log:** italiano
- **Tipo date nel DB:** sempre stringa ISO `YYYY-MM-DD`
- **Tipo timestamp cronometro:** `float` da `time.perf_counter()` (relativo, non epoch Unix)
- **Tempo risultati:** sempre in **millisecondi interi** (`int`) nel DB
- **Formato display tempo:** `H:MM:SS.mmm` (es. `1:03:45.234`)
- **Soft delete:** nessuna riga viene mai cancellata fisicamente se ha relazioni attive
- **Errori DB:** sempre gestiti con `try/except sqlite3.Error` + rollback esplicito
- **Nessun `SELECT *`:** le query nominano sempre le colonne per leggibilità e stabilità

### Conversione ms ↔ stringa

```python
def ms_to_str(ms: int) -> str:
    """1234567 → '20:34.567'  |  3723456 → '1:02:03.456'"""
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms_ = divmod(rem, 1_000)
    if h:
        return f"{h}:{m:02}:{s:02}.{ms_:03}"
    return f"{m}:{s:02}.{ms_:03}"

def str_to_ms(s: str) -> int | None:
    """'1:02:03.456' → 3723456  |  formato non valido → None"""
    import re
    m = re.fullmatch(r'(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})', s.strip())
    if not m:
        return None
    h, mi, sec, ms_ = (int(x or 0) for x in m.groups())
    return h * 3_600_000 + mi * 60_000 + sec * 1_000 + ms_
```

---

## 15. Open points

- [ ] Gestione gare a **partenza intervallata** (es. cronoscalata: ogni atleta parte singolarmente)
- [ ] Supporto **import multi-gara** da un singolo file XLSX (colonna `Evento` / `Gruppo` come discriminante)
- [ ] **Chip timing**: integrazione lettura chip RFID via seriale/USB come alternativa al click manuale
- [ ] **Stampa pettorali** integrata (etichette da PDF)
- [ ] Configurazione **categorie personalizzabili** per disciplina (ora hard-coded nel codice)
- [ ] Gestione **parità di tempo** (stessa classifica a parità di ms)
- [ ] **Log operazioni** completo (audit trail di ogni modifica)
- [ ] Supporto **più operatori** in rete locale (fuori scope v1, valutare per v2)

---

*Documento generato per il progetto UfensCrono — aggiornare ad ogni modifica rilevante dello schema o delle scelte architetturali.*
