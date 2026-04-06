"""
Data Toko Samira
Edit file ini untuk mengubah info toko, katalog produk, dan stok awal.
"""

# ─── Info Toko ───────────────────────────────────────────────────────────────
INFO_TOKO = {
    "nama": "Toko Samira",
    "pemilik": "Bapak Sigit Winaryo",
    "deskripsi": "Toko perlengkapan rumah tangga lengkap & harga terjangkau",
    "alamat": "Dusun III, Kemiri Lor, Kec. Kemiri, Kab. Purworejo, Jawa Tengah 54262",
    "jam_buka": "Senin – Sabtu: 07.00 – 20.00\nMinggu: 08.00 – 17.00",
    "whatsapp": "082XXXXXXXXX",    # ← Ganti nomor asli
    "pemilik_telegram_id": 6267661434,      # ← Ganti dengan Telegram ID pemilik (angka)
                                   #   Cara cek: kirim pesan ke @userinfobot
}
# ─── Katalog Produk ──────────────────────────────────────────────────────────
KATALOG = {
    "Ember & Baskom": {
        "emoji": "🪣",
        "produk": {
            "Ember plastik kecil":         "Rp8.000 – Rp15.000",
            "Ember besar (dengan gagang)": "Rp20.000 – Rp45.000",
            "Baskom kecil":                "Rp5.000 – Rp12.000",
            "Baskom besar":                "Rp15.000 – Rp35.000",
        },
    },
    "Botol & Tempat Minum": {
        "emoji": "🍶",
        "produk": {
            "Botol minum anak":       "Rp10.000 – Rp25.000",
            "Botol plastik dewasa":   "Rp15.000 – Rp40.000",
            "Toples minum/set botol": "Rp20.000 – Rp60.000",
        },
    },
    "Kotak Makan & Wadah": {
        "emoji": "🥡",
        "produk": {
            "Kotak makan kecil":         "Rp8.000 – Rp20.000",
            "Lunch box sekat":           "Rp15.000 – Rp35.000",
            "Wadah makanan (container)": "Rp10.000 – Rp30.000",
            "Set kotak makan":           "Rp25.000 – Rp70.000",
        },
    },
    "Toples & Wadah Bumbu": {
        "emoji": "🫙",
        "produk": {
            "Toples kecil":    "Rp5.000 – Rp15.000",
            "Toples sedang":   "Rp15.000 – Rp30.000",
            "Toples besar":    "Rp30.000 – Rp60.000",
            "Wadah bumbu set": "Rp20.000 – Rp50.000",
        },
    },
