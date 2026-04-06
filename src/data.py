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
    "whatsapp": "082XXXXXXXXX", 
    "pemilik_telegram_id": 6267661434,
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
    "Peralatan Dapur": {
        "emoji": "🍳",
        "produk": {
            "Corong plastik":          "Rp3.000 – Rp10.000",
            "Saringan plastik":        "Rp5.000 – Rp20.000",
            "Parutan":                 "Rp8.000 – Rp25.000",
            "Sendok sayur/alat dapur": "Rp5.000 – Rp20.000",
        },
    },
    "Peralatan Makan": {
        "emoji": "🍽️",
        "produk": {
            "Piring plastik": "Rp3.000 – Rp10.000",
            "Gelas plastik":  "Rp2.000 – Rp8.000",
            "Sendok & garpu": "Rp1.000 – Rp5.000",
            "Set alat makan": "Rp10.000 – Rp30.000",
        },
    },
    "Peralatan Rumah Tangga": {
        "emoji": "🏠",
        "produk": {
            "Keranjang plastik": "Rp15.000 – Rp50.000",
            "Tempat sampah":     "Rp20.000 – Rp60.000",
            "Rak plastik kecil": "Rp30.000 – Rp100.000",
        },
    },
    "Plastik & Kemasan": {
        "emoji": "🛍️",
        "produk": {
            "Plastik kiloan": "Rp15.000 – Rp40.000/kg",
            "Kantong kresek": "Rp10.000 – Rp25.000/pack",
            "Mika makanan":   "Rp10.000 – Rp50.000/pack",
            "Styrofoam":      "Rp20.000 – Rp60.000/pack",
        },
    },
    "Cetakan & Loyang": {
        "emoji": "🧁",
        "produk": {
            "Cetakan es batu": "Rp5.000 – Rp15.000",
            "Cetakan kue":     "Rp10.000 – Rp30.000",
            "Loyang plastik":  "Rp15.000 – Rp40.000",
        },
    },
    "Produk Lainnya": {
        "emoji": "🛒",
        "produk": {
            "Tikar plastik": "Rp20.000 – Rp80.000",
            "Gayung":        "Rp5.000 – Rp15.000",
            "Tutup saji":    "Rp10.000 – Rp25.000",
        },
    },
}

# ─── Stok Awal ───────────────────────────────────────────────────────────────
# Dipakai SEKALI saat database pertama kali dibuat.
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
