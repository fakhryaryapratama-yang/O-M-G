"""
Bot Telegram Toko Samira
Fitur: Menu | Cek Stok | Pemesanan via Bot | Konfirmasi Pemilik | Laporan
"""

import asyncio
import logging
from datetime import time as dtime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from data import INFO_TOKO, KATALOG
from database import (
    init_db,
    get_stok_by_kategori,
    get_stok_produk,
    get_stok_kritis,
    cari_produk,
    kurangi_stok,
    kembalikan_stok,
    tambah_stok,
    buat_pesanan,
    get_pesanan,
    update_status_pesanan,
    log_aktivitas,
    laporan_hari_ini,
    STATUS_DITERIMA,
    STATUS_DITOLAK,
)
# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# State sementara per user (alur multi-step pemesanan)
user_state: dict = {}

OWNER_ID = INFO_TOKO["pemilik_telegram_id"]

# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def kb_menu_utama() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Katalog Produk",  callback_data="katalog"),
            InlineKeyboardButton("🔍 Cek Stok",        callback_data="cek_stok"),
        ],
        [
            InlineKeyboardButton("🛒 Pesan Sekarang",  callback_data="mulai_pesan"),
            InlineKeyboardButton("📍 Info Toko",       callback_data="info_toko"),
        ],
        [
            InlineKeyboardButton("📞 Hubungi Pemilik", callback_data="hubungi"),
        ],
    ])


def kb_kategori(prefix="kat") -> InlineKeyboardMarkup:
    keys = list(KATALOG.keys())
    buttons = [
        InlineKeyboardButton(
            f"{KATALOG[k]['emoji']} {k}", callback_data=f"{prefix}_{i}"
        )
        for i, k in enumerate(keys)
    ]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")])
    return InlineKeyboardMarkup(rows)


def kb_kembali_katalog() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kategori Lain", callback_data="katalog")],
        [InlineKeyboardButton("🏠 Menu Utama",    callback_data="menu_utama")],
    ])


def kb_kembali_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")]
    ])


def kb_konfirmasi_pemilik(pesanan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Terima Pesanan", callback_data=f"terima_{pesanan_id}"),
            InlineKeyboardButton("❌ Tolak Pesanan",  callback_data=f"tolak_{pesanan_id}"),
        ]
    ])

