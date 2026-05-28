# UfensCrono

Applicazione desktop per la gestione e la cronometrazione di gare podistiche.  
Permette di registrare atleti, creare eventi e gare, gestire le iscrizioni, cronometrare gli arrivi in tempo reale e generare classifiche in formato Excel e PDF.

---

## Requisiti

- **Windows 10 / 11** (64 bit)
- **Python 3.11 o superiore** — scaricabile da [python.org](https://www.python.org/downloads/)  
  *(solo se vuoi avviare da sorgente; non serve per il .exe)*

---

## Avvio da sorgente (sviluppatori)

### 1. Scarica il codice

```
git clone git@github-personal:Siron69/UfensCrono.git
cd UfensCrono
```

Oppure scarica lo ZIP dalla pagina GitHub e decomprimi la cartella.

### 2. Crea un ambiente virtuale e installa le dipendenze

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Avvia l'applicazione

```
python main.py
```

Al primo avvio il database viene creato automaticamente nella cartella `data/`.

---

## Creare il file .exe (eseguibile autonomo)

Con il file .exe puoi distribuire l'applicazione su un PC **senza dover installare Python**.

### 1. Installa PyInstaller (una volta sola)

Con l'ambiente virtuale attivo:

```
pip install pyinstaller
```

### 2. Genera il .exe

```
pyinstaller --onefile --windowed --name UfensCrono main.py
```

- `--onefile` → tutto in un singolo file `.exe`
- `--windowed` → nessuna finestra nera di terminale in background

Il file viene creato in `dist\UfensCrono.exe`.

### 3. Copia la cartella `data/`

Il .exe salva il database e i file esportati nella cartella `data/` accanto all'eseguibile.  
Se vuoi spostare `UfensCrono.exe` su un altro PC, porta con te anche la cartella `data/` (o lascia che venga ricreata automaticamente al primo avvio).

> **Nota:** se il PC di destinazione ha un antivirus aggressivo, potrebbe bloccare il .exe alla prima esecuzione. In quel caso aggiungi un'eccezione o usa la modalità "Esegui comunque".

---

## Struttura delle cartelle (dati utente)

```
data/
  ufenscrono.db      ← database principale
  backup/            ← backup automatici creati prima di ogni gara
  export/            ← file Excel e PDF generati dall'app
```

---

## Documentazione

- **[MANUALE.md](MANUALE.md)** — guida all'uso dell'applicazione e domande frequenti (FAQ)
- **[UfensCrono_TECHNICAL.md](UfensCrono_TECHNICAL.md)** — documentazione tecnica per sviluppatori

---

## Licenza

Uso interno — tutti i diritti riservati.
