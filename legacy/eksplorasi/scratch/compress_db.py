import zipfile, os, hashlib

# Compress
zf = zipfile.ZipFile('ranah_siaga_v2.db.zip', 'w', zipfile.ZIP_DEFLATED)
zf.write('ranah_siaga_v2.db')
zf.close()

db_size = os.path.getsize('ranah_siaga_v2.db') / (1024*1024)
zip_size = os.path.getsize('ranah_siaga_v2.db.zip') / (1024*1024)

# Hash
sha256_hash = hashlib.sha256()
with open('ranah_siaga_v2.db', 'rb') as f:
    for block in iter(lambda: f.read(4096), b''):
        sha256_hash.update(block)

print(f"DB size:  {db_size:.2f} MB")
print(f"ZIP size: {zip_size:.2f} MB")
print(f"SHA-256:  {sha256_hash.hexdigest()}")
