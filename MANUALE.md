# Manuale utente — UfensCrono

Guida all'utilizzo dell'applicazione e risposte alle domande più comuni.

---

## Indice

1. [Panoramica generale](#1-panoramica-generale)
2. [Gestione atleti](#2-gestione-atleti)
3. [Gestione eventi e gare](#3-gestione-eventi-e-gare)
4. [Iscrizioni e categorie](#4-iscrizioni-e-categorie)
5. [Import da file Excel](#5-import-da-file-excel)
6. [Cronometro](#6-cronometro)
7. [Classifica](#7-classifica)
8. [Export Excel e PDF](#8-export-excel-e-pdf)
9. [FAQ — Domande frequenti](#9-faq--domande-frequenti)

---

## 1. Panoramica generale

UfensCrono è organizzato con una barra di navigazione a sinistra. Le sezioni principali sono:

| Sezione | A cosa serve |
|---|---|
| **Atleti** | Archivio di tutti gli atleti registrati |
| **Eventi** | Elenco degli eventi (es. "Gara Podistica 2025") |
| **Gare** | Le singole gare all'interno di un evento |
| **Cronometro** | Registrazione degli arrivi in tempo reale |
| **Classifiche** | Visualizzazione, correzione e export dei risultati |

Il flusso normale è: **creare un evento → creare una gara → iscrivere gli atleti → avviare il cronometro → consultare la classifica**.

---

## 2. Gestione atleti

### Aggiungere un atleta

1. Clicca su **Atleti** nella barra laterale.
2. Premi il pulsante **+ Nuovo atleta**.
3. Compila i campi (nome, cognome, sesso, data di nascita sono obbligatori).
4. Premi **Salva**.

### Modificare o eliminare un atleta

- **Doppio clic** su una riga per aprire il form di modifica.
- Seleziona una riga e premi **Elimina** per rimuoverlo.
  - Se l'atleta ha iscrizioni attive, l'eliminazione non è permessa per evitare di perdere dati storici.

### Cercare un atleta

Usa il campo di ricerca in cima alla lista: filtra in tempo reale su nome, cognome e società.  
Puoi anche filtrare per sesso con il menu a tendina.

---

## 3. Gestione eventi e gare

### Creare un evento

1. Clicca su **Eventi**.
2. Premi **+ Nuovo evento**, inserisci il nome e la data, premi **Salva**.

### Aprire le gare di un evento

- Doppio clic sull'evento oppure selezionalo e premi **Apri gare →**.

### Creare una gara

1. Dalla lista gare, premi **+ Nuova gara**.
2. Inserisci nome, tipo (es. "corsa") e distanza in metri.
3. Premi **Salva**.

### Stati di una gara

| Stato | Significato |
|---|---|
| **Bozza** | In preparazione, si possono modificare dati e iscrizioni |
| **In corso** | Il cronometro è avviato, si registrano gli arrivi |
| **Conclusa** | Gara terminata, disponibile solo la classifica |

---

## 4. Iscrizioni e categorie

### Iscrivere un atleta manualmente

1. Seleziona una gara e premi **Iscrizioni →**.
2. Nella colonna di sinistra appare l'elenco degli atleti disponibili; selezionane uno e premi **Iscrivi**.
3. Assegna il numero di pettorale (viene proposto quello successivo disponibile).
4. La categoria viene calcolata automaticamente dall'età dell'atleta; puoi sovrascriverla manualmente se necessario.

### Gestire le categorie della gara

Nella schermata iscrizioni trovi il pulsante **Categorie**: puoi aggiungere, modificare o eliminare le categorie definite per quella specifica gara (nome, sesso, fascia d'età).

---

## 5. Import da file Excel

Utile per importare in massa le iscrizioni da un file scaricato da un portale esterno.

1. Vai su **Iscrizioni →** della gara di destinazione.
2. Premi **Importa XLSX**.
3. **Passo 1** — seleziona il file Excel e controlla l'anteprima delle prime righe.
4. **Passo 2** — scegli l'evento e la gara di destinazione (già preimpostata se sei partito dalla gara).
5. **Passo 3** — conferma e avvia l'import. Viene mostrato un riepilogo con il numero di atleti creati, aggiornati e iscrizioni aggiunte.

> Il sistema evita i duplicati: se un atleta con lo stesso codice fiscale (o nome+cognome+data di nascita) è già presente, vengono aggiornati i suoi dati anziché creare un doppione.

---

## 6. Cronometro

### Avviare una gara

1. Dalla lista gare, seleziona la gara e premi **Avvia cronometro →**.
2. Nella schermata operatore, premi **▶ Avvia gara**.
   - Viene creato un backup automatico del database prima di partire.
3. Il timer inizia a scorrere.

### Registrare un arrivo

Hai due modi:

- **Click sul pulsante "Arrivato"** accanto all'atleta nella tabella in basso.
- **Digitare il numero di pettorale** nel campo in fondo allo schermo e premere Invio.

L'arrivo viene salvato istantaneamente con il tempo preciso.

### Finestra display pubblica

Premi **Apri display pubblica** per aprire una seconda finestra con:
- Il timer in grande (ideale su uno schermo proiettato).
- La lista degli arrivi in ordine, con nome atleta e tempo.

Puoi trascinare questa finestra su un secondo monitor.

### Annullare l'ultimo arrivo

Premi **↩ Annulla ultimo** per correggere un errore di registrazione. Ti verrà chiesta conferma.

### Ripristino dopo un crash

Se l'applicazione si chiude inaspettatamente mentre una gara è in corso, al successivo avvio il cronometro viene ricostruito automaticamente dall'orario di partenza salvato. I tempi già registrati sono conservati nel database.

---

## 7. Classifica

Accessibile dalla lista gare (pulsante **Classifica →**) per le gare in corso o concluse.

### Le quattro viste

| Tab | Contenuto |
|---|---|
| **Assoluta** | Tutti gli atleti ordinati per tempo |
| **Per Categoria** | Ordinati per categoria, poi per tempo all'interno |
| **Uomini** | Solo atleti maschili, ordinati per tempo |
| **Donne** | Solo atlete femminili, ordinate per tempo |

### Modificare lo stato di un atleta

Fai **doppio clic** su qualsiasi riga per aprire il pannello di modifica:

- **Stato**: OK / DSQ (squalificato) / DNF (non ha terminato) / DNS (non partito)
- **Tempo corretto**: puoi inserire un tempo manuale (es. `1:23.456`) che sostituisce quello registrato. Il tempo originale rimane salvato nel database.

Gli atleti con stato diverso da OK appaiono in grigio in fondo alla classifica.

---

## 8. Export Excel e PDF

Dalla schermata **Classifiche**, una volta caricata una gara:

- **Esporta Excel** → genera un file `.xlsx` con quattro fogli (Assoluta, Per Categoria, Uomini, Donne). Ti viene chiesto dove salvarlo.
- **Esporta PDF** → genera un report `.pdf` impaginato, con intestazione, numero di pagina, righe zebrate e atleti non classificati in grigio.

I file vengono salvati dove vuoi tu tramite la finestra di salvataggio.  
Se usi il percorso predefinito, i file finiscono nella cartella `data/export/` accanto all'applicazione.

---

## 9. FAQ — Domande frequenti

---

**L'applicazione non si avvia / viene bloccata dall'antivirus**

È un comportamento comune con i .exe generati da PyInstaller sui PC Windows.  
Soluzione: clicca su *Ulteriori informazioni* → *Esegui comunque* nella schermata di Windows SmartScreen.  
In alternativa, aggiungi il file alle eccezioni dell'antivirus.

---

**Al primo avvio non vedo nessun dato**

È normale: il database viene creato vuoto. Inizia aggiungendo un atleta dalla sezione **Atleti**, poi crea un evento e una gara.

---

**Ho avviato una gara per sbaglio, posso tornare indietro?**

Una volta avviata (stato *In corso*), la gara non può tornare a *Bozza*.  
Puoi però non registrare nessun arrivo e concluderla subito, oppure usare il backup automatico (vedi sotto).

---

**Dove sono i backup automatici?**

Prima di ogni avvio gara, l'applicazione crea una copia del database in `data/backup/`.  
Il nome del file contiene il nome della gara e la data/ora del backup.  
Per ripristinare: chiudi l'applicazione, rinomina il file di backup in `ufenscrono.db` e copialo in `data/`.

---

**Ho registrato un arrivo sbagliato**

Usa il pulsante **↩ Annulla ultimo** nella schermata cronometro. Puoi annullare solo l'ultimo arrivo registrato.  
Se l'errore è più vecchio, vai nella sezione **Classifiche** e modifica lo stato dell'atleta a DNF o DSQ.

---

**Il tempo di un atleta è sbagliato**

Dalla schermata **Classifiche**, fai doppio clic sulla riga dell'atleta e inserisci il tempo corretto nel campo *Tempo corretto*. Il tempo originale viene conservato, ma la classifica usa quello corretto.

---

**Il file Excel o PDF non si apre**

- Excel: assicurati di avere Microsoft Excel o LibreOffice installato.
- PDF: assicurati di avere un lettore PDF (Adobe Reader, il browser di Windows, ecc.).

---

**Ho perso il database / si è corrotto**

Controlla la cartella `data/backup/`. Se non ci sono backup, purtroppo i dati non sono recuperabili.  
Per ridurre il rischio, copia periodicamente la cartella `data/` su un'altra posizione (chiavetta USB, cloud, ecc.).

---

**Posso usare l'applicazione su più PC contemporaneamente?**

No: il database è un file locale SQLite. Non è pensato per l'uso in rete simultaneo.  
Per condividere i dati, copia il file `data/ufenscrono.db` tra i PC.

---

**Come aggiorno l'applicazione?**

- **Da sorgente**: esegui `git pull` e poi `python main.py`.
- **Da .exe**: scarica la nuova versione e sostituisci il vecchio `.exe`. La cartella `data/` con il database rimane invariata.
