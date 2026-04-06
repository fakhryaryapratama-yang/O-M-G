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


# ── PESANAN ──────────────────────────────────────────────────────────────────

def buat_pesanan(user_id, username, nama, hp, alamat, catatan, produk, harga_teks, qty) -> int:
    """Simpan pesanan baru. Return id pesanan."""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO pesanan (user_id, username, nama, hp, alamat, catatan, produk, harga_teks, qty, status)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (user_id, username or "unknown", nama, hp, alamat, catatan, produk, harga_teks, qty, STATUS_MENUNGGU),
    )
    pesanan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pesanan_id


def get_pesanan(pesanan_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM pesanan WHERE id = ?", (pesanan_id,)).fetchone()
    conn.close()
    return row


def update_status_pesanan(pesanan_id: int, status: str, pesan_tolak: str = ""):
    conn = get_conn()
    conn.execute(
        "UPDATE pesanan SET status = ?, pesan_tolak = ? WHERE id = ?",
        (status, pesan_tolak, pesanan_id),
    )
    conn.commit()
    conn.close()


def get_semua_pesanan_hari_ini():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM pesanan WHERE waktu LIKE ? ORDER BY waktu DESC",
        (f"{today}%",),
    ).fetchall()
    conn.close()
    return rows


# ── LOG ───────────────────────────────────────────────────────────────────────

def log_aktivitas(user_id, username, aksi, detail=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO log_aktivitas (user_id, username, aksi, detail) VALUES (?,?,?,?)",
        (user_id, username or "unknown", aksi, detail),
    )
    conn.commit()
    conn.close()


# ── LAPORAN ───────────────────────────────────────────────────────────────────

def laporan_hari_ini():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")

    total_interaksi = conn.execute(
        "SELECT COUNT(*) as n FROM log_aktivitas WHERE waktu LIKE ?", (f"{today}%",)
    ).fetchone()["n"]

    pengguna_unik = conn.execute(
        "SELECT COUNT(DISTINCT user_id) as n FROM log_aktivitas WHERE waktu LIKE ?", (f"{today}%",)
    ).fetchone()["n"]

    top_produk = conn.execute(
        """SELECT detail, COUNT(*) as n FROM log_aktivitas
           WHERE aksi='lihat_produk' AND waktu LIKE ?
           GROUP BY detail ORDER BY n DESC LIMIT 5""",
        (f"{today}%",),
    ).fetchall()

    pesanan_hari_ini = get_semua_pesanan_hari_ini()
    stok_kritis = get_stok_kritis()

    conn.close()
    return {
        "tanggal": today,
        "total_interaksi": total_interaksi,
        "pengguna_unik": pengguna_unik,
        "top_produk": top_produk,
        "pesanan": pesanan_hari_ini,
        "stok_kritis": stok_kritis,
    }
