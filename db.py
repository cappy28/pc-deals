import sqlite3
import statistics
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("deals.db")


def _con():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init():
    with closing(_con()) as con, con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS offres (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                source    TEXT NOT NULL,
                ext_id    TEXT NOT NULL,
                composant TEXT NOT NULL,
                type      TEXT NOT NULL,
                titre     TEXT NOT NULL,
                prix      REAL,
                url       TEXT,
                lieu      TEXT,
                vu_le     TEXT NOT NULL,
                UNIQUE(source, ext_id)
            )""")


def ajouter(o) -> bool:
    """Ajoute une offre. Renvoie True si elle est nouvelle."""
    with closing(_con()) as con, con:
        cur = con.execute(
            "INSERT OR IGNORE INTO offres (source, ext_id, composant, type, titre, prix, url, lieu, vu_le) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (o["source"], o["ext_id"], o["composant"], o["type"], o["titre"],
             o["prix"], o["url"], o["lieu"], o["vu_le"]),
        )
        return cur.rowcount == 1


def nombre() -> int:
    with closing(_con()) as con:
        return con.execute("SELECT COUNT(*) FROM offres").fetchone()[0]


def _depuis(jours):
    return (datetime.now() - timedelta(days=jours)).isoformat(timespec="seconds")


def mediane(composant, jours=30):
    """Prix médian d'occasion (Leboncoin) sur les X derniers jours."""
    with closing(_con()) as con:
        rows = con.execute(
            "SELECT prix FROM offres WHERE composant=? AND source='leboncoin' "
            "AND prix IS NOT NULL AND vu_le>=?", (composant, _depuis(jours))).fetchall()
    prix = [r["prix"] for r in rows]
    return statistics.median(prix) if len(prix) >= 3 else None


def offres_composant(composant, jours=7):
    with closing(_con()) as con:
        rows = con.execute(
            "SELECT * FROM offres WHERE composant=? AND prix IS NOT NULL AND vu_le>=? "
            "ORDER BY prix ASC", (composant, _depuis(jours))).fetchall()
    return [dict(r) for r in rows]


def offres(type_=None, source=None, limite=300):
    sql, params = "SELECT * FROM offres WHERE 1=1", []
    if type_:
        sql += " AND type=?"; params.append(type_)
    if source:
        sql += " AND source=?"; params.append(source)
    sql += " ORDER BY vu_le DESC LIMIT ?"; params.append(limite)
    with closing(_con()) as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
