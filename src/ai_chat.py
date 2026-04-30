"""
ai_chat.py — Modul AI Chat untuk Bot Toko Samira
Menggunakan Groq (GRATIS) sebagai AI engine.
Model: llama-3.3-70b-versatile

Cara dapat API key:
1. Buka https://console.groq.com
2. Daftar / login pakai Google
3. Klik "API Keys" → "Create API Key"
4. Tambahkan ke .env: GROQ_API_KEY=gsk_xxxxxxxxxx
"""

import os
import logging
from groq import Groq

from data import INFO_TOKO, KATALOG, PEMBAYARAN
from database import get_stok_by_kategori, get_stok_kritis

logger = logging.getLogger(__name__)


# ─── Bangun konteks toko dari database ───────────────────────────────────────

def _build_context() -> str:
    """Ambil data toko + stok real-time dari DB, jadikan teks konteks untuk AI."""
    lines = []

    lines.append("=== INFO TOKO ===")
    lines.append(f"Nama      : {INFO_TOKO['nama']}")
    lines.append(f"Pemilik   : {INFO_TOKO['pemilik']}")
    lines.append(f"Deskripsi : {INFO_TOKO['deskripsi']}")
    lines.append(f"Alamat    : {INFO_TOKO['alamat']}")
    lines.append(f"Jam Buka  : {INFO_TOKO['jam_buka']}")
    lines.append(f"WhatsApp  : {INFO_TOKO['whatsapp']}")
    lines.append("")

    lines.append("=== METODE PEMBAYARAN ===")
    lines.append("- Cash (bayar langsung / COD)")
    lines.append("- QRIS (scan QR, bayar digital)")
    lines.append("")

    lines.append("=== KATALOG & STOK PRODUK ===")
    for kat_nama in KATALOG:
        rows = get_stok_by_kategori(kat_nama)
        lines.append(f"\n[{kat_nama}]")
        for r in rows:
            if r["qty"] == 0:
                stok_label = "HABIS"
            elif r["qty"] <= 3:
                stok_label = f"Terbatas (sisa {r['qty']})"
            else:
                stok_label = f"Tersedia ({r['qty']} pcs)"
            lines.append(f"  • {r['produk']}: {r['harga_teks']} — {stok_label}")

    kritis = get_stok_kritis()
    if kritis:
        lines.append("\n=== STOK HAMPIR HABIS ===")
        for s in kritis:
            lines.append(f"  • {s['produk']}: sisa {s['qty']}")

    return "\n".join(lines)


# ─── System prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Kamu adalah asisten virtual {nama_toko}, toko perlengkapan rumah tangga di Purworejo, Jawa Tengah.

TUGAS:
- Bantu pelanggan: cek produk, harga, stok, cara pesan, jam buka, info toko, dll.
- Jawab dengan bahasa Indonesia yang ramah, santai, dan sopan.
- Jika pelanggan bertanya produk, sebutkan harga dan status stok dari data di bawah.
- Jika pelanggan mau memesan, arahkan tekan tombol "🛒 Pesan Sekarang" di menu.

BATASAN KETAT:
- HANYA jawab seputar {nama_toko}. Tolak semua pertanyaan di luar konteks toko.
- Yang HARUS ditolak: politik, berita nasional, matematika umum, resep masakan, dll.
- Jika di luar konteks: balas sopan "Maaf, saya hanya bisa membantu urusan {nama_toko} 🙏"
- JANGAN mengarang harga atau stok. Pakai hanya data yang tersedia di bawah.
- JANGAN sebut nama model AI atau teknologi yang kamu gunakan.

FORMAT:
- Singkat dan padat (3–5 kalimat cukup).
- Gunakan emoji secukupnya agar terasa ramah.
- Tawarkan bantuan lanjutan jika relevan.

DATA TOKO (real-time dari database):
{konteks}
"""


# ─── Fungsi utama ─────────────────────────────────────────────────────────────

def tanya_ai(pesan_user: str, riwayat: list = None) -> str:
    """
    Kirim pesan ke Groq dan kembalikan jawabannya.

    Args:
        pesan_user : teks dari pelanggan
        riwayat    : list dict {"role": "user"/"assistant", "content": "..."}

    Returns:
        str — jawaban AI
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY tidak ditemukan di .env")

    client = Groq(api_key=api_key)

    # System prompt fresh setiap request supaya data stok selalu real-time
    system = _SYSTEM_PROMPT.format(
        nama_toko=INFO_TOKO["nama"],
        konteks=_build_context(),
    )

    # Susun messages: system → riwayat (maks 10 terakhir) → pesan baru
    messages = [{"role": "system", "content": system}]
    if riwayat:
        for msg in riwayat[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": pesan_user})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=512,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()