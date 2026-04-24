"""
monitoring.py — Monitoring error otomatis untuk Bot Toko Samira
Kirim notifikasi ke Telegram admin jika ada error, startup, atau shutdown.
"""

import logging
import asyncio
from datetime import datetime
from telegram import Bot

logger = logging.getLogger(__name__)

_bot: Bot = None
_admin_id: int = 0

# Cooldown agar error yang sama tidak spam notifikasi (detik)
_COOLDOWN = 300
_error_cache: dict = {}


def init_monitoring(bot: Bot, admin_id: int):
    """Panggil sekali di main() setelah Application dibuat."""
    global _bot, _admin_id
    _bot = bot
    _admin_id = admin_id
    logger.info(f"[Monitoring] Aktif — notifikasi → admin ID {admin_id}")


# ─── Kirim notifikasi (async) ─────────────────────────────────────────────────

async def _kirim(pesan: str):
    """Internal: kirim pesan ke admin, tangkap error tanpa crash."""
    if not _bot or not _admin_id:
        return
    try:
        await _bot.send_message(chat_id=_admin_id, text=pesan, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[Monitoring] Gagal kirim notif: {e}")


async def notif_error(judul: str, detail: str, tb: str = ""):
    """
    Kirim notifikasi error ke admin via Telegram.
    Error yang sama tidak dikirim lebih dari sekali per _COOLDOWN detik.
    """
    # Cooldown check
    key = f"{judul}:{detail[:80]}"
    now = datetime.now().timestamp()
    if now - _error_cache.get(key, 0) < _COOLDOWN:
        logger.debug(f"[Monitoring] Throttled: {key}")
        return
    _error_cache[key] = now

    waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    tb_crop = tb[-800:] if tb else "-"

    teks = (
        f"🚨 *ERROR — Bot Toko Samira*\n"
        f"{'═'*30}\n"
        f"📌 *{judul}*\n"
        f"⏰ {waktu}\n\n"
        f"📋 *Detail:*\n`{detail[:300]}`"
    )
    if tb_crop != "-":
        teks += f"\n\n🔍 *Traceback:*\n```\n{tb_crop}\n```"

    await _kirim(teks)


def notif_error_sync(judul: str, detail: str, tb: str = ""):
    """
    Wrapper sync untuk dipanggil dari error_handler (non-async context).
    Menggunakan asyncio.ensure_future agar tidak blocking.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(notif_error(judul, detail, tb))
        else:
            loop.run_until_complete(notif_error(judul, detail, tb))
    except Exception as e:
        logger.error(f"[Monitoring] notif_error_sync gagal: {e}")


async def notif_startup():
    """Kirim notif ke admin bahwa bot berhasil nyala."""
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    await _kirim(
        f"✅ *Bot Toko Samira — AKTIF*\n"
        f"⏰ {waktu}\n"
        f"🟢 Bot siap menerima pesan."
    )


async def notif_shutdown():
    """Kirim notif ke admin bahwa bot dimatikan/restart."""
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    await _kirim(
        f"🔴 *Bot Toko Samira — MATI / RESTART*\n"
        f"⏰ {waktu}"
    )