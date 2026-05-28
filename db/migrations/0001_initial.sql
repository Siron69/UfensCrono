-- Migrazione 0001: schema iniziale completo

CREATE TABLE IF NOT EXISTS atleti (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nome             TEXT    NOT NULL,
    cognome          TEXT    NOT NULL,
    sesso            TEXT    NOT NULL CHECK(sesso IN ('M', 'F')),
    data_nascita     TEXT    NOT NULL,
    luogo_nascita    TEXT,
    nazionalita      TEXT    DEFAULT 'ITA',
    codice_fiscale   TEXT,
    societa          TEXT,
    codice_societa   TEXT,
    tessera          TEXT,
    tessera2         TEXT,
    ente             TEXT,
    categoria        TEXT,
    scad_certificato TEXT,
    stato_cert       TEXT,
    telefono         TEXT,
    cellulare        TEXT,
    email            TEXT,
    note             TEXT,
    source_id        TEXT,
    source_order_id  TEXT,
    created_at       TEXT    DEFAULT (datetime('now')),
    updated_at       TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS eventi (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL,
    data       TEXT    NOT NULL,
    luogo      TEXT,
    note       TEXT,
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gare (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id   INTEGER NOT NULL REFERENCES eventi(id) ON DELETE CASCADE,
    nome        TEXT    NOT NULL,
    tipo        TEXT,
    distanza_m  INTEGER,
    stato       TEXT    NOT NULL DEFAULT 'bozza'
                        CHECK(stato IN ('bozza', 'in_corso', 'conclusa')),
    start_ts    REAL,
    start_wall  TEXT,
    note        TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS iscrizioni (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    gara_id        INTEGER NOT NULL REFERENCES gare(id) ON DELETE CASCADE,
    atleta_id      INTEGER NOT NULL REFERENCES atleti(id),
    pettorale      TEXT    NOT NULL,
    pettorale_circ TEXT,
    codice_chip    TEXT,
    quota          TEXT,
    stato_lw       TEXT,
    categoria_calc TEXT,
    categoria_override TEXT,
    partecipa      INTEGER NOT NULL DEFAULT 1,
    UNIQUE(gara_id, pettorale),
    UNIQUE(gara_id, atleta_id)
);

CREATE TABLE IF NOT EXISTS risultati (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    iscrizione_id  INTEGER NOT NULL REFERENCES iscrizioni(id) ON DELETE CASCADE,
    tempo_ms       INTEGER,
    tempo_override TEXT,
    stato          TEXT    NOT NULL DEFAULT 'ok'
                           CHECK(stato IN ('ok', 'dsq', 'dnf', 'dns')),
    ordine_arrivo  INTEGER,
    note_arbitro   TEXT,
    updated_at     TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categorie (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nome    TEXT    NOT NULL,
    sesso   TEXT    NOT NULL DEFAULT 'MF' CHECK(sesso IN ('M', 'F', 'MF')),
    eta_min INTEGER,
    eta_max INTEGER,
    ordine  INTEGER DEFAULT 0
);
