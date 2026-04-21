"""
Bot Telegram Toko Samira
Fitur: Menu | Cek Stok | Pemesanan | Pembayaran (Cash/QRIS/Paylater) | Laporan
"""

import asyncio
import io
import os
import logging
from datetime import time as dtime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from data import INFO_TOKO, KATALOG, PEMBAYARAN, parse_harga, format_rupiah
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
    BAYAR_CASH,
    BAYAR_QRIS,
    BAYAR_PAYLATER,
)

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

user_state: dict = {}
OWNER_ID = INFO_TOKO["ID"]


# ══════════════════════════════════════════════════════════════════════════════
# QRIS GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def buat_qr_bytes(data: str) -> bytes:
    """Generate QR code dari string data, return bytes PNG."""
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


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


def kb_metode_bayar() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💵 Cash",     callback_data="bayar_cash"),
            InlineKeyboardButton("📷 QRIS",     callback_data="bayar_qris"),
        ],
        [
            InlineKeyboardButton("🔄 Paylater (Cicilan)", callback_data="bayar_paylater"),
        ],
        [InlineKeyboardButton("❌ Batalkan", callback_data="batalkan_pesan")],
    ])


def kb_tenor() -> InlineKeyboardMarkup:
    tenor_list = PEMBAYARAN["paylater_tenor"]
    buttons = [
        InlineKeyboardButton(f"{t} Bulan", callback_data=f"tenor_{t}")
        for t in tenor_list
    ]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("❌ Batalkan", callback_data="batalkan_pesan")])
    return InlineKeyboardMarkup(rows)


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
    if qty == 0:  return "❌ Habis"
    if qty <= 3:  return f"⚠️ Terbatas ({qty})"
    return f"✅ Ada ({qty})"


def label_metode(metode: str, tenor: int = 0) -> str:
    if metode == BAYAR_CASH:     return "💵 Cash"
    if metode == BAYAR_QRIS:     return "📷 QRIS"
    if metode == BAYAR_PAYLATER: return f"🔄 Paylater {tenor} Bulan"
    return metode


def format_detail_kategori(kategori_nama: str) -> str:
    rows = get_stok_by_kategori(kategori_nama)
    emoji = KATALOG[kategori_nama]["emoji"]
    teks = f"{emoji} *{kategori_nama}*\n{'─'*32}\n"
    for r in rows:
        teks += f"• *{r['produk']}*\n"
        teks += f"  💰 {r['harga_teks']}   {label_stok(r['qty'])}\n"
    return teks


def format_notif_pemilik(p) -> str:
    metode_str = label_metode(p["metode_bayar"], p["tenor_bulan"])
    cicilan_str = ""
    if p["metode_bayar"] == BAYAR_PAYLATER and p["cicilan_per_bln"] > 0:
        cicilan_str = f"\n💳 *Cicilan:* {format_rupiah(p['cicilan_per_bln'])}/bulan"
    return (
        f"🔔 *PESANAN BARU — #{p['id']}*\n"
        f"{'═'*30}\n"
        f"👤 *Nama:* {p['nama']}\n"
        f"📱 *HP/WA:* {p['hp']}\n"
        f"📍 *Alamat:* {p['alamat']}\n"
        f"📝 *Catatan:* {p['catatan'] or '-'}\n\n"
        f"🛍️ *Produk:* {p['produk']}\n"
        f"💰 *Harga satuan:* {p['harga_teks']}\n"
        f"🔢 *Jumlah:* {p['qty']}\n"
        f"🧾 *Total:* {format_rupiah(p['total_harga'])}\n"
        f"💳 *Pembayaran:* {metode_str}{cicilan_str}\n\n"
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
    teks += "🛒 *Pesanan Hari Ini:*\n"
    if lap["pesanan"]:
        diterima = [p for p in lap["pesanan"] if p["status"] == "diterima"]
        ditolak  = [p for p in lap["pesanan"] if p["status"] == "ditolak"]
        menunggu = [p for p in lap["pesanan"] if p["status"] == "menunggu"]
        teks += f"  ✅ {len(diterima)} diterima  ❌ {len(ditolak)} ditolak  ⏳ {len(menunggu)} menunggu\n"
        for p in lap["pesanan"]:
            icon = {"diterima": "✅", "ditolak": "❌", "menunggu": "⏳"}.get(p["status"], "•")
            metode = label_metode(p["metode_bayar"], p["tenor_bulan"])
            teks += f"  {icon} #{p['id']} {p['produk']} x{p['qty']} | {format_rupiah(p['total_harga'])} | {metode}\n"
    else:
        teks += "  _Belum ada pesanan_\n"

    teks += "\n🔥 *Produk Paling Diminati:*\n"
    if lap["top_produk"]:
        for i, p in enumerate(lap["top_produk"], 1):
            teks += f"  {i}. {p['detail']} ({p['n']}x)\n"
    else:
        teks += "  _Belum ada data_\n"

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
    uid, uname = update.effective_user.id, update.effective_user.username
    log_aktivitas(uid, uname, "start")
    await update.message.reply_text(
        f"👋 Halo, *{update.effective_user.first_name}*! Selamat datang di\n"
        f"🏪 *{INFO_TOKO['nama']}*\n\n_{INFO_TOKO['deskripsi']}_\n\nPilih menu di bawah:",
        parse_mode="Markdown", reply_markup=kb_menu_utama(),
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Panduan Bot Toko Samira*\n\n"
        "• 📦 *Katalog* → Produk & harga per kategori\n"
        "• 🔍 *Cek Stok* → Ketersediaan stok real-time\n"
        "• 🛒 *Pesan Sekarang* → Order langsung via bot\n"
        "• 📍 *Info Toko* → Alamat & jam buka\n"
        "• 📞 *Hubungi Pemilik* → Kontak WhatsApp\n\n"
        "Ketik nama produk untuk mencari langsung.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "*Metode Pembayaran:*\n"
        "💵 Cash · 📷 QRIS · 🔄 Paylater (Cicilan)\n\n"
        "*Perintah Pemilik:*\n"
        "/laporan — Laporan hari ini\n"
        "/tambahstok — Tambah stok produk",
        parse_mode="Markdown", reply_markup=kb_menu_utama(),
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
        "📥 *Tambah Stok*\n\nKetik nama produk:", parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d     = q.data
    uid   = q.from_user.id
    uname = q.from_user.username

    # ── Menu Utama ──
    if d == "menu_utama":
        user_state.pop(uid, None)
        await q.edit_message_text(
            "🏪 *Menu Utama Toko Samira*\n\nPilih yang kamu butuhkan:",
            parse_mode="Markdown", reply_markup=kb_menu_utama(),
        )

    # ── Katalog ──
    elif d == "katalog":
        log_aktivitas(uid, uname, "katalog")
        await q.edit_message_text(
            "📦 *Pilih Kategori Produk:*", parse_mode="Markdown",
            reply_markup=kb_kategori("kat"),
        )

    elif d.startswith("kat_"):
        idx  = int(d.split("_")[1])
        keys = list(KATALOG.keys())
        if idx < len(keys):
            kat = keys[idx]
            log_aktivitas(uid, uname, "lihat_produk", kat)
            await q.edit_message_text(
                format_detail_kategori(kat), parse_mode="Markdown",
                reply_markup=kb_kembali_katalog(),
            )

    # ── Cek Stok ──
    elif d == "cek_stok":
        log_aktivitas(uid, uname, "cek_stok")
        keys = list(KATALOG.keys())
        buttons = [
            InlineKeyboardButton(f"{KATALOG[k]['emoji']} {k}", callback_data=f"stok_kat_{i}")
            for i, k in enumerate(keys)
        ]
        rows_kb = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        rows_kb.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")])
        await q.edit_message_text(
            "🔍 *Cek Stok — Pilih Kategori:*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows_kb),
        )

    elif d.startswith("stok_kat_"):
        idx  = int(d.split("_")[2])
        keys = list(KATALOG.keys())
        if idx < len(keys):
            kat_nama  = keys[idx]
            rows_stok = get_stok_by_kategori(kat_nama)
            aman     = [r for r in rows_stok if r["qty"] > 3]
            terbatas = [r for r in rows_stok if 0 < r["qty"] <= 3]
            habis    = [r for r in rows_stok if r["qty"] == 0]
            teks = f"{KATALOG[kat_nama]['emoji']} *{kat_nama}*\n{'─'*30}\n\n"
            teks += "✅ *Aman:*\n"
            teks += "".join(f"  • {r['produk']} — stok: {r['qty']}\n" for r in aman) or "  _tidak ada_\n"
            teks += "\n⚠️ *Terbatas (sisa ≤ 3):*\n"
            teks += "".join(f"  • {r['produk']} — sisa: {r['qty']}\n" for r in terbatas) or "  _tidak ada_\n"
            teks += "\n❌ *Habis:*\n"
            teks += "".join(f"  • {r['produk']}\n" for r in habis) or "  _tidak ada_\n"
            await q.edit_message_text(
                teks, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Pilih Kategori Lain", callback_data="cek_stok")],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")],
                ]),
            )

    # ── Info Toko ──
    elif d == "info_toko":
        log_aktivitas(uid, uname, "info_toko")
        await q.edit_message_text(
            f"📍 *Informasi Toko*\n\n"
            f"🏪 *Nama:* {INFO_TOKO['nama']}\n"
            f"👤 *Pemilik:* {INFO_TOKO['pemilik']}\n\n"
            f"📌 *Alamat:*\n{INFO_TOKO['alamat']}\n\n"
            f"🕐 *Jam Buka:*\n{INFO_TOKO['jam_buka']}",
            parse_mode="Markdown", reply_markup=kb_kembali_menu(),
        )

    # ── Hubungi Pemilik ──
    elif d == "hubungi":
        log_aktivitas(uid, uname, "hubungi")
        await q.edit_message_text(
            f"📞 *Hubungi Kami*\n\n"
            f"👤 *{INFO_TOKO['pemilik']}*\n"
            f"📱 WhatsApp: {INFO_TOKO['whatsapp']}\n\n_Kami siap membantu!_ 😊",
            parse_mode="Markdown", reply_markup=kb_kembali_menu(),
        )

    # ══════════════════════════════════════════════════════════════════════════
    # ALUR PEMESANAN
    # ══════════════════════════════════════════════════════════════════════════

    elif d == "mulai_pesan":
        log_aktivitas(uid, uname, "mulai_pesan")
        user_state[uid] = {"step": "pesan_pilih_kategori"}
        await q.edit_message_text(
            "🛒 *Pemesanan — Pilih Kategori*", parse_mode="Markdown",
            reply_markup=kb_kategori("pesan_kat"),
        )

    elif d.startswith("pesan_kat_"):
        idx  = int(d.split("_")[2])
        keys = list(KATALOG.keys())
        if idx < len(keys):
            kat      = keys[idx]
            tersedia = [r for r in get_stok_by_kategori(kat) if r["qty"] > 0]
            if not tersedia:
                await q.edit_message_text(
                    f"😕 Semua produk di *{kat}* sedang habis.",
                    parse_mode="Markdown", reply_markup=kb_kategori("pesan_kat"),
                )
                return
            user_state[uid] = {"step": "pesan_pilih_produk", "kategori": kat}
            buttons = [
                [InlineKeyboardButton(
                    f"{r['produk']} | {r['harga_teks']} | Stok: {r['qty']}",
                    callback_data=f"pesan_prod_{r['produk']}"
                )]
                for r in tersedia
            ]
            buttons.append([InlineKeyboardButton("⬅️ Ganti Kategori", callback_data="mulai_pesan")])
            await q.edit_message_text(
                f"🛒 *{kat}*\n\nPilih produk:", parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

    elif d.startswith("pesan_prod_"):
        produk_nama = d[len("pesan_prod_"):]
        row = get_stok_produk(produk_nama)
        if not row or row["qty"] == 0:
            await q.edit_message_text(
                f"❌ Stok *{produk_nama}* sudah habis.",
                parse_mode="Markdown", reply_markup=kb_kembali_menu(),
            )
            return
        state = user_state.get(uid, {})
        state.update({
            "step": "pesan_qty",
            "produk": produk_nama,
            "harga_teks": row["harga_teks"],
            "harga_satuan": parse_harga(row["harga_teks"]),
            "stok": row["qty"],
        })
        user_state[uid] = state
        await q.edit_message_text(
            f"🛒 *{produk_nama}*\n💰 {row['harga_teks']}\n📦 Stok: *{row['qty']}*\n\n"
            f"Ketik *jumlah* yang ingin dipesan:",
            parse_mode="Markdown",
        )

    elif d == "batalkan_pesan":
        user_state.pop(uid, None)
        await q.edit_message_text("❌ Pemesanan dibatalkan.", reply_markup=kb_menu_utama())

    # ── Pilih Metode Pembayaran ──
    elif d == "bayar_cash":
        state = user_state.get(uid, {})
        state["metode_bayar"]  = BAYAR_CASH
        state["tenor_bulan"]   = 0
        state["cicilan_per_bln"] = 0
        state["step"] = "pesan_konfirmasi"
        user_state[uid] = state
        await _tampil_ringkasan(q, state)

    elif d == "bayar_qris":
        state = user_state.get(uid, {})
        state["metode_bayar"]  = BAYAR_QRIS
        state["tenor_bulan"]   = 0
        state["cicilan_per_bln"] = 0
        state["step"] = "pesan_konfirmasi"
        user_state[uid] = state
        await _tampil_ringkasan(q, state)

    elif d == "bayar_paylater":
        state = user_state.get(uid, {})
        state["metode_bayar"] = BAYAR_PAYLATER
        state["step"] = "pesan_pilih_tenor"
        user_state[uid] = state
        total = state.get("total_harga", 0)
        await q.edit_message_text(
            f"🔄 *Paylater / Cicilan*\n\n"
            f"Total belanja: *{format_rupiah(total)}*\n\n"
            f"Pilih tenor cicilan:",
            parse_mode="Markdown", reply_markup=kb_tenor(),
        )

    elif d.startswith("tenor_"):
        tenor = int(d.split("_")[1])
        state = user_state.get(uid, {})
        total = state.get("total_harga", 0)
        cicilan = total // tenor if tenor > 0 else total
        state["tenor_bulan"]   = tenor
        state["cicilan_per_bln"] = cicilan
        state["step"] = "pesan_konfirmasi"
        user_state[uid] = state
        await _tampil_ringkasan(q, state)

    # ── Konfirmasi Pemilik ──
    elif d.startswith("terima_"):
        pesanan_id = int(d.split("_")[1])
        if OWNER_ID != 0 and uid != OWNER_ID:
            await q.answer("⛔ Hanya pemilik toko.", show_alert=True)
            return
        p = get_pesanan(pesanan_id)
        if not p or p["status"] != "menunggu":
            await q.edit_message_text(f"ℹ️ Pesanan #{pesanan_id} sudah diproses.")
            return
        update_status_pesanan(pesanan_id, STATUS_DITERIMA)
        await q.edit_message_text(
            format_notif_pemilik(p) + "\n\n✅ *PESANAN DITERIMA*", parse_mode="Markdown"
        )
        # Notif ke pelanggan
        metode_str = label_metode(p["metode_bayar"], p["tenor_bulan"])
        pesan_bayar = ""
        if p["metode_bayar"] == BAYAR_CASH:
            pesan_bayar = f"💵 Bayar *{format_rupiah(p['total_harga'])}* saat barang diterima."
        elif p["metode_bayar"] == BAYAR_PAYLATER:
            pesan_bayar = (
                f"🔄 Cicilan *{format_rupiah(p['cicilan_per_bln'])}/bulan* "
                f"selama *{p['tenor_bulan']} bulan*."
            )
        try:
            await ctx.bot.send_message(
                p["user_id"],
                f"🎉 *Pesanan Kamu Diterima!*\n\n"
                f"🛍️ *{p['produk']}* x{p['qty']}\n"
                f"🧾 *Total:* {format_rupiah(p['total_harga'])}\n"
                f"💳 *Pembayaran:* {metode_str}\n"
                f"{pesan_bayar}\n\n"
                f"Toko akan menghubungi kamu di *{p['hp']}*. 🙏",
                parse_mode="Markdown",
            )
            # Kirim QR code jika metode QRIS
            if p["metode_bayar"] == BAYAR_QRIS:
                qr_data = f"{PEMBAYARAN['qris_id']}|{p['total_harga']}|#{pesanan_id}"
                qr_bytes = buat_qr_bytes(qr_data)
                await ctx.bot.send_photo(
                    p["user_id"],
                    photo=qr_bytes,
                    caption=(
                        f"📷 *QR Code Pembayaran*\n\n"
                        f"Scan QR ini untuk membayar *{format_rupiah(p['total_harga'])}* via QRIS.\n"
                        f"No. Pesanan: *#{pesanan_id}*"
                    ),
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Gagal kirim notif ke pelanggan: {e}")

    elif d.startswith("tolak_"):
        pesanan_id = int(d.split("_")[1])
        if OWNER_ID != 0 and uid != OWNER_ID:
            await q.answer("⛔ Hanya pemilik toko.", show_alert=True)
            return
        p = get_pesanan(pesanan_id)
        if not p or p["status"] != "menunggu":
            await q.edit_message_text(f"ℹ️ Pesanan #{pesanan_id} sudah diproses.")
            return
        user_state[uid] = {"step": "tolak_alasan", "pesanan_id": pesanan_id}
        await q.edit_message_text(
            f"❌ Tolak pesanan #{pesanan_id}\n\nKetik *alasan penolakan*:",
            parse_mode="Markdown",
        )


async def _tampil_ringkasan(q, state: dict):
    """Tampilkan ringkasan pesanan lengkap dengan metode bayar."""
    total      = state.get("total_harga", 0)
    metode     = state.get("metode_bayar", BAYAR_CASH)
    tenor      = state.get("tenor_bulan", 0)
    cicilan    = state.get("cicilan_per_bln", 0)

    metode_str = label_metode(metode, tenor)
    bayar_info = ""
    if metode == BAYAR_PAYLATER:
        bayar_info = f"\n💳 Cicilan: *{format_rupiah(cicilan)}/bulan* × {tenor} bulan"
    elif metode == BAYAR_QRIS:
        bayar_info = "\n📷 QR Code akan dikirim setelah pesanan dikonfirmasi pemilik"

    ringkasan = (
        f"📋 *Ringkasan Pesanan*\n{'─'*30}\n"
        f"🛍️ *Produk:* {state['produk']}\n"
        f"💰 *Harga:* {state['harga_teks']}\n"
        f"🔢 *Jumlah:* {state['qty']}\n"
        f"🧾 *Total:* {format_rupiah(total)}\n\n"
        f"👤 *Nama:* {state['nama']}\n"
        f"📱 *HP/WA:* {state['hp']}\n"
        f"📍 *Alamat:* {state['alamat']}\n"
        f"📝 *Catatan:* {state.get('catatan') or '-'}\n\n"
        f"💳 *Metode Bayar:* {metode_str}{bayar_info}\n\n"
        f"Apakah data sudah benar?"
    )
    await q.edit_message_text(
        ringkasan, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ya, Pesan Sekarang!", callback_data="konfirmasi_pesan"),
                InlineKeyboardButton("❌ Batalkan",            callback_data="batalkan_pesan"),
            ]
        ]),
    )


# ══════════════════════════════════════════════════════════════════════════════
# KONFIRMASI PESANAN
# ══════════════════════════════════════════════════════════════════════════════

async def handle_konfirmasi_pesan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q     = update.callback_query
    await q.answer()
    uid   = q.from_user.id
    uname = q.from_user.username
    state = user_state.get(uid, {})

    if state.get("step") != "pesan_konfirmasi":
        await q.edit_message_text("⚠️ Sesi pemesanan tidak ditemukan.", reply_markup=kb_menu_utama())
        return

    produk = state["produk"]
    qty    = state["qty"]

    berhasil = kurangi_stok(produk, qty)
    if not berhasil:
        user_state.pop(uid, None)
        row  = get_stok_produk(produk)
        sisa = row["qty"] if row else 0
        await q.edit_message_text(
            f"❌ Stok *{produk}* tidak mencukupi. Tersisa: *{sisa}*",
            parse_mode="Markdown", reply_markup=kb_menu_utama(),
        )
        return

    pesanan_id = buat_pesanan(
        user_id       = uid,
        username      = uname,
        nama          = state["nama"],
        hp            = state["hp"],
        alamat        = state["alamat"],
        catatan       = state.get("catatan", ""),
        produk        = produk,
        harga_teks    = state["harga_teks"],
        qty           = qty,
        total_harga   = state.get("total_harga", 0),
        metode_bayar  = state.get("metode_bayar", BAYAR_CASH),
        tenor_bulan   = state.get("tenor_bulan", 0),
        cicilan_per_bln = state.get("cicilan_per_bln", 0),
    )
    user_state.pop(uid, None)
    log_aktivitas(uid, uname, "pesan", f"#{pesanan_id} {produk} x{qty}")

    metode_str = label_metode(state.get("metode_bayar", BAYAR_CASH), state.get("tenor_bulan", 0))
    await q.edit_message_text(
        f"✅ *Pesanan Berhasil Dikirim!*\n\n"
        f"📋 No. Pesanan: *#{pesanan_id}*\n"
        f"🛍️ *{produk}* x{qty}\n"
        f"🧾 *Total:* {format_rupiah(state.get('total_harga', 0))}\n"
        f"💳 *Pembayaran:* {metode_str}\n\n"
        f"Pesanan sedang diproses. Kamu akan dinotifikasi setelah dikonfirmasi. ⏳",
        parse_mode="Markdown", reply_markup=kb_menu_utama(),
    )

    if OWNER_ID != 0:
        p = get_pesanan(pesanan_id)
        try:
            await ctx.bot.send_message(
                OWNER_ID, format_notif_pemilik(p),
                parse_mode="Markdown",
                reply_markup=kb_konfirmasi_pemilik(pesanan_id),
            )
        except Exception as e:
            logger.error(f"Gagal kirim notif ke pemilik: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_pesan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    teks  = update.message.text.strip()
    uid   = update.effective_user.id
    uname = update.effective_user.username
    lower = teks.lower()
    state = user_state.get(uid, {})
    step  = state.get("step", "")

    # ── Tolak pesanan (pemilik ketik alasan) ──
    if step == "tolak_alasan":
        pesanan_id = state["pesanan_id"]
        p = get_pesanan(pesanan_id)
        user_state.pop(uid, None)
        update_status_pesanan(pesanan_id, STATUS_DITOLAK, teks)
        kembalikan_stok(p["produk"], p["qty"])
        await update.message.reply_text(
            f"✅ Pesanan #{pesanan_id} ditolak. Stok *{p['produk']}* dikembalikan +{p['qty']}.",
            parse_mode="Markdown",
        )
        try:
            await ctx.bot.send_message(
                p["user_id"],
                f"😔 *Pesanan Kamu Ditolak*\n\n"
                f"🛍️ *{p['produk']}* x{p['qty']}\n\n"
                f"📝 *Alasan:*\n_{teks}_\n\n"
                f"Hubungi kami: 📱 {INFO_TOKO['whatsapp']}",
                parse_mode="Markdown", reply_markup=kb_menu_utama(),
            )
        except Exception as e:
            logger.warning(f"Gagal kirim notif tolak: {e}")
        return

    # ── Tambah stok (pemilik) ──
    if step == "tambahstok_nama":
        hasil = cari_produk(teks)
        if not hasil:
            await update.message.reply_text(f"❌ *\"{teks}\"* tidak ditemukan.", parse_mode="Markdown")
            return
        if len(hasil) == 1:
            user_state[uid] = {"step": "tambahstok_qty", "produk": hasil[0]["produk"]}
            await update.message.reply_text(
                f"✅ *{hasil[0]['produk']}*\nStok: *{hasil[0]['qty']}*\n\nKetik jumlah tambahan:",
                parse_mode="Markdown",
            )
        else:
            buttons = [[InlineKeyboardButton(r["produk"], callback_data=f"pesan_prod_{r['produk']}")] for r in hasil[:8]]
            await update.message.reply_text("Pilih produk:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if step == "tambahstok_qty":
        if not teks.isdigit() or int(teks) <= 0:
            await update.message.reply_text("⚠️ Masukkan angka positif.")
            return
        qty    = int(teks)
        produk = state["produk"]
        tambah_stok(produk, qty)
        user_state.pop(uid, None)
        row = get_stok_produk(produk)
        await update.message.reply_text(
            f"✅ Stok *{produk}* +{qty} → sekarang *{row['qty']}*",
            parse_mode="Markdown", reply_markup=kb_menu_utama(),
        )
        return

    # ── Pemesanan: jumlah ──
    if step == "pesan_qty":
        if not teks.isdigit() or int(teks) <= 0:
            await update.message.reply_text("⚠️ Masukkan angka positif.")
            return
        qty  = int(teks)
        stok = state.get("stok", 0)
        if qty > stok:
            await update.message.reply_text(f"❌ Stok hanya *{stok}*.", parse_mode="Markdown")
            return
        total = state.get("harga_satuan", 0) * qty
        state.update({"qty": qty, "total_harga": total, "step": "pesan_nama"})
        user_state[uid] = state
        await update.message.reply_text(
            f"✅ *{state['produk']}* x{qty} = *{format_rupiah(total)}*\n\n"
            f"📝 *Langkah 1/4* — Ketik *nama lengkap* kamu:",
            parse_mode="Markdown",
        )
        return

    # ── Pemesanan: nama ──
    if step == "pesan_nama":
        if len(teks) < 2:
            await update.message.reply_text("⚠️ Nama terlalu pendek.")
            return
        state.update({"nama": teks, "step": "pesan_hp"})
        user_state[uid] = state
        await update.message.reply_text("📝 *Langkah 2/4* — Ketik *nomor HP/WA*:", parse_mode="Markdown")
        return

    # ── Pemesanan: HP ──
    if step == "pesan_hp":
        bersih = teks.replace("-", "").replace(" ", "")
        if not bersih.lstrip("+").isdigit() or len(bersih) < 9:
            await update.message.reply_text("⚠️ Nomor HP tidak valid. Contoh: 08123456789")
            return
        state.update({"hp": teks, "step": "pesan_alamat"})
        user_state[uid] = state
        await update.message.reply_text("📝 *Langkah 3/4* — Ketik *alamat pengiriman*:", parse_mode="Markdown")
        return

    # ── Pemesanan: alamat ──
    if step == "pesan_alamat":
        if len(teks) < 5:
            await update.message.reply_text("⚠️ Alamat terlalu pendek.")
            return
        state.update({"alamat": teks, "step": "pesan_catatan"})
        user_state[uid] = state
        await update.message.reply_text(
            "📝 *Langkah 4/4* — Ketik *catatan tambahan* (atau *-* jika tidak ada):",
            parse_mode="Markdown",
        )
        return

    # ── Pemesanan: catatan → pilih metode bayar ──
    if step == "pesan_catatan":
        state.update({"catatan": "" if teks == "-" else teks, "step": "pesan_pilih_bayar"})
        user_state[uid] = state
        total = state.get("total_harga", 0)
        await update.message.reply_text(
            f"💳 *Pilih Metode Pembayaran*\n\n"
            f"🛍️ *{state['produk']}* x{state['qty']}\n"
            f"🧾 *Total: {format_rupiah(total)}*\n\n"
            f"Pilih cara pembayaran:",
            parse_mode="Markdown", reply_markup=kb_metode_bayar(),
        )
        return

    if step == "pesan_konfirmasi":
        await update.message.reply_text(
            "Silakan tekan tombol *Ya, Pesan Sekarang!* di atas.", parse_mode="Markdown"
        )
        return

    # ── Salam ──
    salam_list = ["halo", "hi", "hai", "hei", "selamat", "pagi", "siang", "sore", "malam", "permisi", "hola"]
    if any(s in lower for s in salam_list):
        log_aktivitas(uid, uname, "salam")
        await update.message.reply_text(
            f"👋 Halo, *{update.effective_user.first_name}*! Ada yang bisa dibantu?",
            parse_mode="Markdown", reply_markup=kb_menu_utama(),
        )
        return

    # ── Pencarian produk ──
    hasil = cari_produk(lower)
    log_aktivitas(uid, uname, "lihat_produk", teks)
    if hasil:
        pesan = f"🔍 *Hasil: \"{teks}\"*\n{'─'*30}\n\n"
        for r in hasil[:8]:
            pesan += f"• *{r['produk']}*\n  📂 {r['kategori']}   💰 {r['harga_teks']}   {label_stok(r['qty'])}\n\n"
        if len(hasil) > 8:
            pesan += f"_...dan {len(hasil)-8} lainnya_\n\n"
        await update.message.reply_text(
            pesan, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Pesan Sekarang", callback_data="mulai_pesan")],
                [InlineKeyboardButton("🏠 Menu Utama",     callback_data="menu_utama")],
            ]),
        )
    else:
        await update.message.reply_text(
            f"😕 *\"{teks}\"* tidak ditemukan.", parse_mode="Markdown", reply_markup=kb_menu_utama()
        )


# ══════════════════════════════════════════════════════════════════════════════
# REKAP OTOMATIS & ERROR HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def kirim_rekap_harian(ctx: ContextTypes.DEFAULT_TYPE):
    if OWNER_ID == 0:
        return
    lap = laporan_hari_ini()
    try:
        await ctx.bot.send_message(
            OWNER_ID, f"🌙 *Rekap Harian Otomatis*\n\n" + format_laporan(lap),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Gagal kirim rekap: {e}")


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception:", exc_info=ctx.error)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("Database siap.")

    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise ValueError("TOKEN tidak ditemukan di .env")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("laporan",    cmd_laporan))
    app.add_handler(CommandHandler("tambahstok", cmd_tambah_stok))

    app.add_handler(CallbackQueryHandler(handle_konfirmasi_pesan, pattern="^konfirmasi_pesan$"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pesan))

    app.job_queue.run_daily(kirim_rekap_harian, time=dtime(hour=20, minute=0), name="rekap_harian")
    app.add_error_handler(error_handler)

    logger.info("Bot Toko Samira aktif...")

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Tekan Ctrl+C untuk berhenti.")
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())