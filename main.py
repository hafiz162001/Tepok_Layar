import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def print_banner():
    banner = """
===================================================================
      [HEWAN & NYAMUK LAYAR - SENJATA & PEMBESAR!]
===================================================================
  Aplikasi desktop serangga & hewan dengan SENJATA LENGKAP!
  - Suara dengung hewan jernih & berputar di latar belakang!
  - Pilihan Senjata:
      * 🏸 Raket Listrik (Suara sengatan listrik Zzzt-PLAKK!)
      * 🔫 Pistol (Suara tembakan DORR! + kilatan peluru laser)
      * 🔨 Palu (Smash logam berat DUKK!)
      * 🖐️ Tangan (Tepokan klasik PLAAK!)
  - Setiap ditembak/ditepok, hewan MAKIN BESAR sampai meledak!
  - 4 Pilihan Hewan: Nyamuk, Laba-laba, Rubah, Mammoth!

  Tombol Cepat (Keyboard Shortcuts):
  - Klik Kiri       : Tembak / Tepok (Senjata berayun & menyerang)
  - [ Tab ] / [ W ] : Ganti Senjata (Raket / Pistol / Palu / Tangan)
  - Angka [ 1 - 4 ] : Ganti Hewan (1: Nyamuk, 2: Laba-laba, 3: Rubah, 4: Mammoth)
  - Tombol [ R ]    : Reset Ukuran Kembali ke Level 1
  - Tombol [ Spasi ]: Bersihkan Noda Darah di Layar
  - Tombol [ M ]    : Minimize / Maximize Toolbar
  - [ ESC ] / [ Q ] : Keluar dari Aplikasi
===================================================================
Memulai aplikasi... Tekan ESC kapan saja untuk keluar.
"""
    print(banner)

def main():
    print_banner()
    try:
        from app import MosquitoApp
        app = MosquitoApp()
        app.run()
    except KeyboardInterrupt:
        print("\nAplikasi ditutup oleh pengguna.")
    except Exception as e:
        print(f"\nTerjadi kesalahan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
