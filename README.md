# 🤖 Project 2 - Bot Telegram Toko Samira
## 👥 Kelompok: O. M. G.
### Anggota:
1. Fadhil
2. Muhammad Faris Mubaroq
3. Muhammad Fakhry Arya Pratama

---

## 📌 Deskripsi Project

Bot Telegram otomatisasi layanan pelanggan untuk **Toko Samira**, toko perlengkapan rumah tangga di Kemiri, Purworejo. Bot ini menggantikan proses manual yang sebelumnya dilakukan lewat WhatsApp, memungkinkan pelanggan melihat katalog, mengecek stok, dan memesan produk langsung melalui Telegram.

---

## 🎯 Fitur

**Untuk Pelanggan:**
- Lihat katalog produk (10 kategori)
- Cek stok per kategori (aman / terbatas / habis)
- Pesan produk langsung via bot
- Notifikasi status pesanan (diterima / ditolak)
- Cari produk dengan kata kunci
- Info toko & kontak pemilik

**Untuk Pemilik (Admin):**
- Notifikasi pesanan masuk secara langsung
- Konfirmasi atau tolak pesanan dengan alasan
- Tambah stok produk via `/tambahstok`
- Laporan harian via `/laporan`
- Rekap otomatis dikirim setiap pukul 20.00
- Notifikasi otomatis saat stok kritis (≤ 3)

---

## 🛠 Teknologi yang Digunakan

- Python 3.10+
- Telegram Bot API
- Library `python-telegram-bot` v21.6 (dengan job-queue)
- Library `python-dotenv`
- SQLite (database lokal)

---

## 📦 Persyaratan Sistem

Pastikan sudah terinstall:

- Python **3.10 atau lebih baru**
- pip (Python package manager)

Cek versi Python:
```bash
python --version
```

Update pip ke versi terbaru:
```bash
python -m pip install --upgrade pip
```

Install semua library yang dibutuhkan:
```bash
pip install -r requirements.txt
```

Isi `requirements.txt`:
```
python-telegram-bot[job-queue]==21.6
python-dotenv
```

---

## ⚙️ Cara Setup

**1. Clone repository**
```bash
git clone https://github.com/username/O-M-G.git
cd O-M-G
```

**2. Install library**
```bash
pip install -r requirements.txt
```

**3. Buat file `.env`**

Buat file `.env` di folder project, isi dengan:
```
BOT_TOKEN=token_bot_kamu_dari_botfather
```
Cara dapat token: chat ke **@BotFather** di Telegram → `/newbot`

**4. Isi Telegram ID pemilik di `data.py`**
```python
"pemilik_telegram_id": 123456789  # Cek via @userinfobot → di Telegram
```

**5. Jalankan bot**
```bash
python src/Bot.py
```

---
