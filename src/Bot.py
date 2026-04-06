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

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FORMAT
# ══════════════════════════════════════════════════════════════════════════════

def label_stok(qty: int) -> str:
    if qty == 0:   return "❌ Habis"
    if qty <= 3:   return f"⚠️ Terbatas ({qty})"
    return f"✅ Ada ({qty})"


def format_detail_kategori(kategori_nama: str) -> str:
    rows = get_stok_by_kategori(kategori_nama)
    emoji = KATALOG[kategori_nama]["emoji"]
    teks = f"{emoji} *{kategori_nama}*\n{'─'*32}\n"
    for r in rows:
        teks += f"• *{r['produk']}*\n"
        teks += f"  💰 {r['harga_teks']}   {label_stok(r['qty'])}\n"
    return teks


def format_notif_pemilik(p) -> str:
    """Format notifikasi pesanan baru untuk pemilik."""
    return (
        f"🔔 *PESANAN BARU — #{p['id']}*\n"
        f"{'═'*30}\n"
        f"👤 *Nama:* {p['nama']}\n"
        f"📱 *HP/WA:* {p['hp']}\n"
        f"📍 *Alamat:* {p['alamat']}\n"
        f"📝 *Catatan:* {p['catatan'] or '-'}\n\n"
        f"🛍️ *Produk:* {p['produk']}\n"
        f"💰 *Harga:* {p['harga_teks']}\n"
        f"🔢 *Jumlah:* {p['qty']}\n\n"
        f"⏰ {p['waktu']}"
    )


def format_laporan(lap: dict) -> str:
    teks = (
        f"📊 *Laporan Harian Toko Samira*\n"
        f"📅 {lap['tanggal']}\n"
        f"{'═'*32}\n\n"
        f"👥 Pelanggan unik: *{lap['pengguna_unik']}*\n"
        f"💬 Total interaksi: *{lap['total_interaksi']}*\n\n"
    )

    # Pesanan hari ini
    teks += "🛒 *Pesanan Hari Ini:*\n"
    if lap["pesanan"]:
        diterima = [p for p in lap["pesanan"] if p["status"] == "diterima"]
        ditolak  = [p for p in lap["pesanan"] if p["status"] == "ditolak"]
        menunggu = [p for p in lap["pesanan"] if p["status"] == "menunggu"]
        teks += f"  ✅ Diterima: {len(diterima)}  ❌ Ditolak: {len(ditolak)}  ⏳ Menunggu: {len(menunggu)}\n"
        for p in lap["pesanan"]:
            icon = {"diterima": "✅", "ditolak": "❌", "menunggu": "⏳"}.get(p["status"], "•")
            teks += f"  {icon} #{p['id']} {p['produk']} x{p['qty']} — {p['nama']}\n"
    else:
        teks += "  _Belum ada pesanan_\n"

    # Top produk dilihat
    teks += "\n🔥 *Produk Paling Diminati:*\n"
    if lap["top_produk"]:
        for i, p in enumerate(lap["top_produk"], 1):
            teks += f"  {i}. {p['detail']} ({p['n']}x)\n"
    else:
        teks += "  _Belum ada data_\n"

    # Stok kritis
    teks += "\n⚠️ *Stok Perlu Diperhatikan:*\n"
    if lap["stok_kritis"]:
        for s in lap["stok_kritis"]:
            st = "❌ HABIS" if s["qty"] == 0 else f"⚠️ Sisa {s['qty']}"
            teks += f"  • {s['produk']} → {st}\n"
    else:
        teks += "  ✅ Semua stok aman\n"

    return teks

# ══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    uname = update.effective_user.username
    nama  = update.effective_user.first_name
    log_aktivitas(uid, uname, "start")
    await update.message.reply_text(
        f"👋 Halo, *{nama}*! Selamat datang di\n"
        f"🏪 *{INFO_TOKO['nama']}*\n\n"
        f"_{INFO_TOKO['deskripsi']}_\n\n"
        f"Pilih menu di bawah:",
        parse_mode="Markdown",
        reply_markup=kb_menu_utama(),
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Panduan Bot Toko Samira*\n\n"
        "• 📦 *Katalog* → Produk & harga per kategori\n"
        "• 🔍 *Cek Stok* → Ketersediaan stok real-time\n"
        "• 🛒 *Pesan Sekarang* → Order langsung via bot\n"
        "• 📍 *Info Toko* → Alamat & jam buka\n"
        "• 📞 *Hubungi Pemilik* → Kontak WhatsApp\n\n"
        "Atau ketik nama produk untuk mencari.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "*Perintah Pemilik:*\n"
        "/laporan — Laporan hari ini\n"
        "/tambahstok — Tambah stok produk",
        parse_mode="Markdown",
        reply_markup=kb_menu_utama(),
    )


async def cmd_laporan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if OWNER_ID != 0 and uid != OWNER_ID:
        await update.message.reply_text("⛔ Fitur ini hanya untuk pemilik toko.")
        return
    lap = laporan_hari_ini()
    await update.message.reply_text(
        format_laporan(lap), parse_mode="Markdown", reply_markup=kb_kembali_menu()
    )


async def cmd_tambah_stok(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if OWNER_ID != 0 and uid != OWNER_ID:
        await update.message.reply_text("⛔ Fitur ini hanya untuk pemilik toko.")
        return
    user_state[uid] = {"step": "tambahstok_nama"}
    await update.message.reply_text(
        "📥 *Tambah Stok*\n\nKetik nama produk yang ingin ditambah stoknya:",
        parse_mode="Markdown",
    )

