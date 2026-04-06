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

