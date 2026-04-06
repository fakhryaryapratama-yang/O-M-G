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
# ── STOK ─────────────────────────────────────────────────────────────────────

def get_stok_by_kategori(kategori: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM stok WHERE kategori = ? ORDER BY produk", (kategori,)
    ).fetchall()
    conn.close()
    return rows


def get_stok_produk(produk: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM stok WHERE produk = ?", (produk,)).fetchone()
    conn.close()
    return row


def get_stok_kritis():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM stok WHERE qty <= 3 ORDER BY qty ASC"
    ).fetchall()
    conn.close()
    return rows


def kurangi_stok(produk: str, qty: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT qty FROM stok WHERE produk = ?", (produk,)).fetchone()
    if not row or row["qty"] < qty:
        conn.close()
        return False
    conn.execute("UPDATE stok SET qty = qty - ? WHERE produk = ?", (qty, produk))
    conn.commit()
    conn.close()
    return True


def kembalikan_stok(produk: str, qty: int):
    """Kembalikan stok jika pesanan ditolak."""
    conn = get_conn()
    conn.execute("UPDATE stok SET qty = qty + ? WHERE produk = ?", (qty, produk))
    conn.commit()
    conn.close()


def tambah_stok(produk: str, qty: int):
    conn = get_conn()
    conn.execute("UPDATE stok SET qty = qty + ? WHERE produk = ?", (qty, produk))
    conn.commit()
    conn.close()


def cari_produk(keyword: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM stok WHERE LOWER(produk) LIKE ? OR LOWER(kategori) LIKE ?",
        (f"%{keyword.lower()}%", f"%{keyword.lower()}%"),
    ).fetchall()
    conn.close()
    return rows
