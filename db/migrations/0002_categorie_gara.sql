-- Migrazione 0002: categorie per gara specifica
-- Ricrea la tabella categorie con gara_id (era globale, ora è per-gara)

DROP TABLE IF EXISTS categorie;

CREATE TABLE IF NOT EXISTS categorie (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    gara_id  INTEGER NOT NULL REFERENCES gare(id) ON DELETE CASCADE,
    nome     TEXT    NOT NULL,
    sesso    TEXT    NOT NULL DEFAULT 'MF' CHECK(sesso IN ('M', 'F', 'MF')),
    eta_min  INTEGER,
    eta_max  INTEGER,
    ordine   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_categorie_gara ON categorie(gara_id);
