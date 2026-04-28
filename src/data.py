import os
from dotenv import load_dotenv
import re

load_dotenv()

"""
Data Toko Samira
Edit file ini untuk mengubah info toko, katalog produk, stok awal, dan pembayaran.
"""

# ─── Info Toko ───────────────────────────────────────────────────────────────
INFO_TOKO = {
    "nama": "Toko Samira",
    "pemilik": "Bapak Sigit Winaryo",
    "deskripsi": "Toko perlengkapan rumah tangga lengkap & harga terjangkau",
    "alamat": "Dusun III, Kemiri Lor, Kec. Kemiri, Kab. Purworejo, Jawa Tengah 54262",
    "maps": "https://goo.gl/maps/xxxxxxx",  # ← Ganti dengan link Google Maps asli
    "jam_buka": "Senin – Sabtu: 07.00 – 20.00\nMinggu: 08.00 – 17.00",
    "whatsapp": "082XXXXXXXXX",             # ← Ganti nomor asli
    "ID": int(os.getenv("ID") or 0),      # ← Ganti dengan Telegram ID pemilik (angka)
}

# ─── Konfigurasi Pembayaran ──────────────────────────────────────────────────
# QRIS: isi dengan string ID merchant / nomor rekening QRIS kamu.
# Contoh: "00020101021226570011ID.CO.BRI.WWW01189360050300000000000220303UMI..."

PEMBAYARAN = {
    "qris_id": "QRIS_ID_TOKO_SAMIRA",  # ← Ganti dengan ID QRIS asli
}

# ─── Katalog Produk ──────────────────────────────────────────────────────────
KATALOG = {
    "Ember & Baskom": {
        "emoji": "🪣",
        "produk": {
            "Ember plastik kecil":         "Rp8.000",
            "Ember besar (dengan gagang)": "Rp20.000",
            "Baskom kecil":                "Rp5.000",
            "Baskom besar":                "Rp15.000",
        },
    },
    "Botol & Tempat Minum": {
        "emoji": "🍶",
        "produk": {
            "Botol minum anak":       "Rp10.000",
            "Botol plastik dewasa":   "Rp15.000",
            "Toples minum/set botol": "Rp40.000",
        },
    },
    "Kotak Makan & Wadah": {
        "emoji": "🥡",
        "produk": {
            "Kotak makan kecil":         "Rp10.000",
            "Lunch box sekat":           "Rp15.000",
            "Wadah makanan (container)": "Rp30.000",
            "Set kotak makan":           "Rp50.000",
        },
    },
    "Toples & Wadah Bumbu": {
        "emoji": "🫙",
        "produk": {
            "Toples kecil":    "Rp5.000",
            "Toples sedang":   "Rp15.000",
            "Toples besar":    "Rp30.000",
            "Wadah bumbu set": "Rp25.000",
        },
    },
    "Peralatan Dapur": {
        "emoji": "🍳",
        "produk": {
            "Corong plastik":          "Rp3.000",
            "Saringan plastik":        "Rp5.000",
            "Parutan":                 "Rp8.000",
            "Sendok sayur/alat dapur": "Rp5.000",
        },
    },
    "Peralatan Makan": {
        "emoji": "🍽️",
        "produk": {
            "Piring plastik": "Rp5.000",
            "Gelas plastik":  "Rp3.000",
            "Sendok & garpu": "Rp5.000",
            "Set alat makan": "Rp20.000",
        },
    },
    "Peralatan Rumah Tangga": {
        "emoji": "🏠",
        "produk": {
            "Keranjang plastik": "Rp15.000",
            "Tempat sampah":     "Rp20.000",
            "Rak plastik kecil": "Rp30.000",
        },
    },
    "Plastik & Kemasan": {
        "emoji": "🛍️",
        "produk": {
            "Plastik kiloan": "Rp18.000/kg",
            "Kantong kresek": "Rp15.000/pack",
            "Mika makanan":   "Rp40.000/pack",
            "Styrofoam":      "Rp30.000/pack",
        },
    },
    "Cetakan & Loyang": {
        "emoji": "🧁",
        "produk": {
            "Cetakan es batu": "Rp8.000",
            "Cetakan kue":     "Rp10.000",
            "Loyang plastik":  "Rp15.000",
        },
    },
    "Produk Lainnya": {
        "emoji": "🛒",
        "produk": {
            "Tikar plastik": "Rp25.000",
            "Gayung":        "Rp8.000",
            "Tutup saji":    "Rp15.000",
        },
    },
}

# ─── Stok Awal ───────────────────────────────────────────────────────────────
STOK_AWAL = {
    "Ember & Baskom": {
        "Ember plastik kecil": 20, "Ember besar (dengan gagang)": 15,
        "Baskom kecil": 25, "Baskom besar": 10,
    },
    "Botol & Tempat Minum": {
        "Botol minum anak": 30, "Botol plastik dewasa": 20, "Toples minum/set botol": 15,
    },
    "Kotak Makan & Wadah": {
        "Kotak makan kecil": 25, "Lunch box sekat": 20,
        "Wadah makanan (container)": 20, "Set kotak makan": 10,
    },
    "Toples & Wadah Bumbu": {
        "Toples kecil": 30, "Toples sedang": 20, "Toples besar": 15, "Wadah bumbu set": 10,
    },
    "Peralatan Dapur": {
        "Corong plastik": 20, "Saringan plastik": 20,
        "Parutan": 15, "Sendok sayur/alat dapur": 25,
    },
    "Peralatan Makan": {
        "Piring plastik": 40, "Gelas plastik": 40, "Sendok & garpu": 50, "Set alat makan": 15,
    },
    "Peralatan Rumah Tangga": {
        "Keranjang plastik": 20, "Tempat sampah": 15, "Rak plastik kecil": 10,
    },
    "Plastik & Kemasan": {
        "Plastik kiloan": 20, "Kantong kresek": 30, "Mika makanan": 25, "Styrofoam": 20,
    },
    "Cetakan & Loyang": {
        "Cetakan es batu": 20, "Cetakan kue": 15, "Loyang plastik": 15,
    },
    "Produk Lainnya": {
        "Tikar plastik": 10, "Gayung": 25, "Tutup saji": 20,
    },
}


# ─── Helper: parse harga dari string ─────────────────────────────────────────
def parse_harga(harga_teks: str) -> int:
    """Ambil angka dari string harga. Contoh: 'Rp8.000' → 8000"""
    angka = re.sub(r"[^\d]", "", harga_teks.split("/")[0])
    return int(angka) if angka else 0


def format_rupiah(nominal: int) -> str:
    """Format angka ke string rupiah. Contoh: 16000 → 'Rp16.000'"""
    return f"Rp{nominal:,.0f}".replace(",", ".")