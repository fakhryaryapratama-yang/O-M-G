"""
Database handler — SQLite
Tabel: stok, pesanan, log_aktivitas, log_transaksi
"""

import sqlite3
from datetime import datetime

DB_PATH = "toko_samira.db"

STATUS_MENUNGGU  = "menunggu"
STATUS_DITERIMA  = "diterima"
STATUS_DITOLAK   = "ditolak"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    from data import KATALOG, STOK_AWAL
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS stok (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kategori   TEXT NOT NULL,
            produk     TEXT NOT NULL UNIQUE,
            harga_teks TEXT NOT NULL,
            qty        INTEGER NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pesanan (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            username     TEXT,
            nama         TEXT NOT NULL,
            hp           TEXT NOT NULL,
            alamat       TEXT NOT NULL,
            catatan      TEXT DEFAULT '',
            produk       TEXT NOT NULL,
            harga_teks   TEXT NOT NULL,
            qty          INTEGER NOT NULL,
            status       TEXT NOT NULL DEFAULT 'menunggu',
            pesan_tolak  TEXT DEFAULT '',
            waktu        TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS log_aktivitas (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER,
            username TEXT,
            aksi     TEXT,
            detail   TEXT,
            waktu    TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()

    c.execute("SELECT COUNT(*) as n FROM stok")
    if c.fetchone()["n"] == 0:
        for kat, data in KATALOG.items():
            for produk, harga_teks in data["produk"].items():
                qty_awal = STOK_AWAL.get(kat, {}).get(produk, 10)
                c.execute(
                    "INSERT OR IGNORE INTO stok (kategori, produk, harga_teks, qty) VALUES (?,?,?,?)",
                    (kat, produk, harga_teks, qty_awal),
                )
        conn.commit()

    conn.close()
