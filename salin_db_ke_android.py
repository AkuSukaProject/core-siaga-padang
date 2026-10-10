"""
Salin hasil_build/ranah_siaga_v4.db ke aset aplikasi Android Siaga Padang.

Aplikasi membundel DB tanpa zip sebagai app/src/main/assets/ranah_siaga.db dan membaca
assets/dataset_manifest.json dengan format {version, checksum, size_bytes}, di mana checksum adalah
SHA-256 file .db (lihat DatasetStorage.kt). build_db.py sudah menulis manifest berformat itu di
hasil_build/dataset_manifest_android.json; skrip ini memeriksa checksum lalu menyalin keduanya.

Pemakaian:
  env\\Scripts\\python.exe salin_db_ke_android.py C:\\siagapadang            # hanya tampilkan rencana
  env\\Scripts\\python.exe salin_db_ke_android.py C:\\siagapadang --tulis    # salin sungguhan
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DB_SUMBER = os.path.join("hasil_build", "ranah_siaga_v4.db")
MANIFEST_SUMBER = os.path.join("hasil_build", "dataset_manifest_android.json")
DIR_ASET = os.path.join("android", "app", "src", "main", "assets")
NAMA_DB_ASET = "ranah_siaga.db"
NAMA_MANIFEST_ASET = "dataset_manifest.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description="Salin DB hasil build ke aset aplikasi Android")
    p.add_argument("repo_android", help="Root repositori aplikasi (berisi folder android/)")
    p.add_argument("--tulis", action="store_true", help="Benar-benar menyalin (tanpa ini hanya rencana)")
    args = p.parse_args()

    dir_aset = os.path.join(args.repo_android, DIR_ASET)
    if not os.path.isdir(dir_aset):
        sys.exit(f"[ERROR] Folder aset tidak ditemukan: {dir_aset}")

    manifest_baru = json.load(open(MANIFEST_SUMBER, encoding="utf-8"))
    checksum = sha256(DB_SUMBER)
    if checksum != manifest_baru["checksum"].lower() or os.path.getsize(DB_SUMBER) != manifest_baru["size_bytes"]:
        sys.exit("[ERROR] hasil_build/ranah_siaga_v4.db tidak cocok dengan manifest Android. Jalankan ulang build_db.py.")

    path_manifest = os.path.join(dir_aset, NAMA_MANIFEST_ASET)
    lama = json.load(open(path_manifest, encoding="utf-8")) if os.path.exists(path_manifest) else {}
    print(f"Aset tujuan : {dir_aset}")
    print(f"Sekarang    : versi {lama.get('version', '-')}, {lama.get('size_bytes', 0) / 2**20:.1f} MB, checksum {str(lama.get('checksum', '-'))[:16]}")
    print(f"Baru        : versi {manifest_baru['version']}, {manifest_baru['size_bytes'] / 2**20:.1f} MB, checksum {checksum[:16]}")
    if lama.get("checksum", "").lower() == checksum:
        print("Aset sudah memakai DB ini. Tidak ada yang disalin.")
        return
    if not args.tulis:
        print("\nBelum ada yang disalin. Tambahkan --tulis untuk menyalin.")
        print("Sebelum itu pastikan aplikasi sudah menyesuaikan perubahan v4 (docs/handoff_android.md).")
        return

    shutil.copyfile(DB_SUMBER, os.path.join(dir_aset, NAMA_DB_ASET))
    shutil.copyfile(MANIFEST_SUMBER, path_manifest)
    print(f"\nDisalin: {NAMA_DB_ASET} dan {NAMA_MANIFEST_ASET}. Commit di repositori aplikasi.")


if __name__ == "__main__":
    main()
