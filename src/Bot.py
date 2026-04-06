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

# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q     = update.callback_query
    await q.answer()
    d     = q.data
    uid   = q.from_user.id
    uname = q.from_user.username

    # ── Menu Utama ──
    if d == "menu_utama":
        user_state.pop(uid, None)  # Reset state
        await q.edit_message_text(
            "🏪 *Menu Utama Toko Samira*\n\nPilih yang kamu butuhkan:",
            parse_mode="Markdown",
            reply_markup=kb_menu_utama(),
        )

    # ── Katalog ──
    elif d == "katalog":
        log_aktivitas(uid, uname, "katalog")
        await q.edit_message_text(
            "📦 *Pilih Kategori Produk:*",
            parse_mode="Markdown",
            reply_markup=kb_kategori("kat"),
        )

    elif d.startswith("kat_"):
        idx  = int(d.split("_")[1])
        keys = list(KATALOG.keys())
        if idx < len(keys):
            kat = keys[idx]
            log_aktivitas(uid, uname, "lihat_produk", kat)
            await q.edit_message_text(
                format_detail_kategori(kat),
                parse_mode="Markdown",
                reply_markup=kb_kembali_katalog(),
            )

    # ── Cek Stok ──
    elif d == "cek_stok":
        log_aktivitas(uid, uname, "cek_stok")
        keys = list(KATALOG.keys())
        buttons = [
            InlineKeyboardButton(
                f"{KATALOG[k]['emoji']} {k}", callback_data=f"stok_kat_{i}"
            )
            for i, k in enumerate(keys)
        ]
        rows_kb = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        rows_kb.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama")])
        await q.edit_message_text(
            "🔍 *Cek Stok — Pilih Kategori:*\n\nPilih kategori untuk melihat detail stok tiap produk.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows_kb),
        )

    elif d.startswith("stok_kat_"):
        idx  = int(d.split("_")[2])
        keys = list(KATALOG.keys())
        if idx < len(keys):
            kat_nama  = keys[idx]
            emoji     = KATALOG[kat_nama]["emoji"]
            rows_stok = get_stok_by_kategori(kat_nama)

            aman     = [r for r in rows_stok if r["qty"] > 3]
            terbatas = [r for r in rows_stok if 0 < r["qty"] <= 3]
            habis    = [r for r in rows_stok if r["qty"] == 0]

            teks = f"{emoji} *{kat_nama}*\n" + "─" * 30 + "\n\n"

            teks += "✅ *Aman:*\n"
            if aman:
                for r in aman:
                    teks += f"  • {r['produk']} — stok: {r['qty']}\n"
            else:
                teks += "  _tidak ada_\n"

            teks += "\n⚠️ *Terbatas (sisa ≤ 3):*\n"
            if terbatas:
                for r in terbatas:
                    teks += f"  • {r['produk']} — sisa: {r['qty']}\n"
            else:
                teks += "  _tidak ada_\n"

            teks += "\n❌ *Habis:*\n"
            if habis:
                for r in habis:
                    teks += f"  • {r['produk']}\n"
            else:
                teks += "  _tidak ada_\n"

            await q.edit_message_text(
                teks,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Pilih Kategori Lain", callback_data="cek_stok")],
                    [InlineKeyboardButton("🏠 Menu Utama",           callback_data="menu_utama")],
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
            parse_mode="Markdown",
            reply_markup=kb_kembali_menu(),
        )

    # ── Hubungi Pemilik ──
    elif d == "hubungi":
        log_aktivitas(uid, uname, "hubungi")
        await q.edit_message_text(
            f"📞 *Hubungi Kami*\n\n"
            f"👤 *{INFO_TOKO['pemilik']}*\n"
            f"📱 WhatsApp: {INFO_TOKO['whatsapp']}\n\n"
            f"_Kami siap membantu!_ 😊",
            parse_mode="Markdown",
            reply_markup=kb_kembali_menu(),
        )
    # ══════════════════════════════════════════════════════════════════════════
    # ALUR PEMESANAN
    # ══════════════════════════════════════════════════════════════════════════

    elif d == "mulai_pesan":
        log_aktivitas(uid, uname, "mulai_pesan")
        user_state[uid] = {"step": "pesan_pilih_kategori"}
        await q.edit_message_text(
            "🛒 *Pemesanan — Pilih Kategori*\n\nPilih kategori produk yang ingin dipesan:",
            parse_mode="Markdown",
            reply_markup=kb_kategori("pesan_kat"),
        )

    elif d.startswith("pesan_kat_"):
        idx  = int(d.split("_")[2])
        keys = list(KATALOG.keys())
        if idx < len(keys):
            kat  = keys[idx]
            rows = get_stok_by_kategori(kat)
            tersedia = [r for r in rows if r["qty"] > 0]
            if not tersedia:
                await q.edit_message_text(
                    f"😕 Semua produk di *{kat}* sedang habis.\nPilih kategori lain:",
                    parse_mode="Markdown",
                    reply_markup=kb_kategori("pesan_kat"),
                )
                return
            user_state[uid] = {"step": "pesan_pilih_produk", "kategori": kat}
            # Tampilkan produk tersedia di kategori ini
            buttons = []
            for r in tersedia:
                label = f"{r['produk']} | {r['harga_teks']} | Stok: {r['qty']}"
                buttons.append([InlineKeyboardButton(label, callback_data=f"pesan_prod_{r['produk']}")])
            buttons.append([InlineKeyboardButton("⬅️ Ganti Kategori", callback_data="mulai_pesan")])
            await q.edit_message_text(
                f"🛒 *{kat}*\n\nPilih produk yang ingin dipesan:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

    elif d.startswith("pesan_prod_"):
        produk_nama = d[len("pesan_prod_"):]
        row = get_stok_produk(produk_nama)
        if not row or row["qty"] == 0:
            await q.edit_message_text(
                f"❌ Stok *{produk_nama}* sudah habis.\nSilakan pilih produk lain.",
                parse_mode="Markdown",
                reply_markup=kb_kembali_menu(),
            )
            return
        state = user_state.get(uid, {})
        state.update({"step": "pesan_qty", "produk": produk_nama, "harga_teks": row["harga_teks"], "stok": row["qty"]})
        user_state[uid] = state
        await q.edit_message_text(
            f"🛒 *{produk_nama}*\n"
            f"💰 {row['harga_teks']}\n"
            f"📦 Stok tersedia: *{row['qty']}*\n\n"
            f"Ketik *jumlah* yang ingin dipesan (angka saja):",
            parse_mode="Markdown",
        )

    elif d == "pesan_lanjut_nama":
        # Lanjut setelah qty dikonfirmasi (dari tombol)
        state = user_state.get(uid, {})
        state["step"] = "pesan_nama"
        user_state[uid] = state
        await q.edit_message_text(
            "📝 *Data Pemesan — Langkah 1/4*\n\nKetik *nama lengkap* kamu:",
            parse_mode="Markdown",
        )

    elif d == "batalkan_pesan":
        user_state.pop(uid, None)
        await q.edit_message_text(
            "❌ Pemesanan dibatalkan.",
            parse_mode="Markdown",
            reply_markup=kb_menu_utama(),
        )

    # ── Konfirmasi oleh Pemilik ──
    elif d.startswith("terima_"):
        pesanan_id = int(d.split("_")[1])
        if OWNER_ID != 0 and uid != OWNER_ID:
            await q.answer("⛔ Hanya pemilik toko yang bisa konfirmasi.", show_alert=True)
            return
        p = get_pesanan(pesanan_id)
        if not p:
            await q.edit_message_text("⚠️ Pesanan tidak ditemukan.")
            return
        if p["status"] != "menunggu":
            await q.edit_message_text(
                f"ℹ️ Pesanan #{pesanan_id} sudah diproses sebelumnya (status: {p['status']})."
            )
            return

        update_status_pesanan(pesanan_id, STATUS_DITERIMA)
        # Edit pesan notif pemilik
        await q.edit_message_text(
            format_notif_pemilik(p) + "\n\n✅ *PESANAN DITERIMA*",
            parse_mode="Markdown",
        )
        # Kirim notif ke pelanggan
        try:
            await ctx.bot.send_message(
                p["user_id"],
                f"🎉 *Pesanan Kamu Diterima!*\n\n"
                f"🛍️ *{p['produk']}* x{p['qty']}\n"
                f"💰 {p['harga_teks']}\n\n"
                f"Pesanan #{pesanan_id} telah dikonfirmasi oleh toko.\n"
                f"Toko akan segera menghubungi kamu di nomor *{p['hp']}*.\n\n"
                f"Terima kasih sudah belanja di *{INFO_TOKO['nama']}*! 🙏",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Gagal kirim notif ke pelanggan: {e}")

    elif d.startswith("tolak_"):
        pesanan_id = int(d.split("_")[1])
        if OWNER_ID != 0 and uid != OWNER_ID:
            await q.answer("⛔ Hanya pemilik toko yang bisa konfirmasi.", show_alert=True)
            return
        p = get_pesanan(pesanan_id)
        if not p:
            await q.edit_message_text("⚠️ Pesanan tidak ditemukan.")
            return
        if p["status"] != "menunggu":
            await q.edit_message_text(
                f"ℹ️ Pesanan #{pesanan_id} sudah diproses sebelumnya (status: {p['status']})."
            )
            return
        # Minta pemilik ketik alasan penolakan
        user_state[uid] = {"step": "tolak_alasan", "pesanan_id": pesanan_id}
        await q.edit_message_text(
            f"❌ Tolak pesanan #{pesanan_id}\n\nKetik *alasan penolakan* untuk dikirim ke pelanggan:",
            parse_mode="Markdown",
        )

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

    # ══════════════════════════════════════════════════════════════════════════
    # ALUR PEMILIK: TOLAK PESANAN (ketik alasan)
    # ══════════════════════════════════════════════════════════════════════════
    if step == "tolak_alasan":
        pesanan_id = state["pesanan_id"]
        p = get_pesanan(pesanan_id)
        user_state.pop(uid, None)

        update_status_pesanan(pesanan_id, STATUS_DITOLAK, teks)
        # Kembalikan stok
        kembalikan_stok(p["produk"], p["qty"])

        await update.message.reply_text(
            f"✅ Pesanan #{pesanan_id} ditolak.\nStok *{p['produk']}* dikembalikan +{p['qty']}.",
            parse_mode="Markdown",
        )
        # Notif ke pelanggan
        try:
            await ctx.bot.send_message(
                p["user_id"],
                f"😔 *Pesanan Kamu Ditolak*\n\n"
                f"🛍️ *{p['produk']}* x{p['qty']}\n\n"
                f"📝 *Alasan dari toko:*\n_{teks}_\n\n"
                f"Silakan hubungi kami untuk informasi lebih lanjut:\n"
                f"📱 {INFO_TOKO['whatsapp']}",
                parse_mode="Markdown",
                reply_markup=kb_menu_utama(),
            )
        except Exception as e:
            logger.warning(f"Gagal kirim notif tolak ke pelanggan: {e}")
        return
    # ══════════════════════════════════════════════════════════════════════════
    # ALUR PEMILIK: TAMBAH STOK
    # ══════════════════════════════════════════════════════════════════════════
    if step == "tambahstok_nama":
        hasil = cari_produk(teks)
        if not hasil:
            await update.message.reply_text(
                f"❌ Produk *\"{teks}\"* tidak ditemukan. Coba kata lain:",
                parse_mode="Markdown",
            )
            return
        if len(hasil) == 1:
            user_state[uid] = {"step": "tambahstok_qty", "produk": hasil[0]["produk"]}
            await update.message.reply_text(
                f"✅ *{hasil[0]['produk']}*\nStok saat ini: *{hasil[0]['qty']}*\n\nKetik jumlah yang ingin ditambahkan:",
                parse_mode="Markdown",
            )
        else:
            buttons = [[InlineKeyboardButton(r["produk"], callback_data=f"pesan_prod_{r['produk']}")] for r in hasil[:8]]
            user_state[uid] = {"step": "tambahstok_nama"}
            await update.message.reply_text(
                f"🔍 Ditemukan {len(hasil)} produk. Pilih yang dimaksud:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        return

    if step == "tambahstok_qty":
        if not teks.isdigit() or int(teks) <= 0:
            await update.message.reply_text("⚠️ Masukkan angka positif. Contoh: 10")
            return
        qty    = int(teks)
        produk = state["produk"]
        tambah_stok(produk, qty)
        user_state.pop(uid, None)
        row = get_stok_produk(produk)
        await update.message.reply_text(
            f"✅ Stok *{produk}* ditambah *{qty}*\nStok sekarang: *{row['qty']}*",
            parse_mode="Markdown",
            reply_markup=kb_menu_utama(),
        )
        return
