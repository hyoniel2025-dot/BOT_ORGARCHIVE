import asyncio

# 🔥 FIX para Python 3.14 + Pyrogram
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
from pathlib import Path
import threading
import requests
from flask import Flask
from pyrogram import Client, filters
import internetarchive
import py7zr
from multivolumefile import MultiVolume
from config import Config

# =========================
# 📁 CARPETAS
# =========================
DOWNLOAD_PATH = Path("downloads")
COMPRESS_PATH = Path("compressed")

DOWNLOAD_PATH.mkdir(exist_ok=True)
COMPRESS_PATH.mkdir(exist_ok=True)

# =========================
# ☁️ CONFIG ARCHIVE
# =========================
internetarchive.configure(Config.ACCESS_KEY, Config.SECRET_KEY)

# =========================
# 🤖 BOT
# =========================
app_bot = Client(
    "mi_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# =========================
# ✂️ SPLIT
# =========================
def split_file(file_path, chunk_size=99*1024*1024):
    file_path = Path(file_path)
    file_name = file_path.name

    chunks = []
    with open(file_path, "rb") as f:
        chunk_num = 1
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunk_file = file_path.parent / f"{file_name}.part{chunk_num:03d}"
            with open(chunk_file, "wb") as cf:
                cf.write(chunk)
            chunks.append(chunk_file)
            chunk_num += 1
    return chunks

# =========================
# 📦 COMPRIMIR CHUNKS
# =========================
def compress_chunks(chunks, volume_size=None):
    compressed_files = []

    for chunk in chunks:
        chunk = Path(chunk)
        archive_name = COMPRESS_PATH / f"{chunk.name}.7z"

        with MultiVolume(str(archive_name), mode="wb", volume=volume_size or 99*1024*1024, ext_digits=3) as archive:
            with py7zr.SevenZipFile(archive, 'w') as z:
                z.write(chunk, arcname=chunk.name)

        for file in archive._files:
            compressed_files.append(file.name)

        chunk.unlink()  # borrar chunk original

    return compressed_files

# =========================
# 🔄 PROCESO COMPLETO
# =========================
def process_file(file_path):
    chunks = split_file(file_path)
    compressed = compress_chunks(chunks)
    return compressed

# =========================
# ☁️ SUBIR A ARCHIVE
# =========================
def upload_to_archive(files, item_name):
    internetarchive.upload(item_name, files)
    return f"https://archive.org/details/{item_name}"

# =========================
# 📄 CREAR TXT SOLO CON EL ENLACE
# =========================
def create_txt(link, original_file_name):
    txt_name = Path(original_file_name).with_suffix(".txt")
    txt_path = DOWNLOAD_PATH / txt_name

    with open(txt_path, "w") as f:
        f.write(link + "\n")  # SOLO el enlace

    return txt_path

# =========================
# 🧹 LIMPIEZA
# =========================
def cleanup(paths):
    for path in paths:
        p = Path(path)
        if p.exists():
            p.unlink()

# =========================
# 📥 ARCHIVOS TELEGRAM
# =========================
@app_bot.on_message(filters.document | filters.video | filters.audio)
async def handle_files(client, message):
    msg = await message.reply("📥 Descargando archivo...")
    file_path = await message.download(file_name=DOWNLOAD_PATH)

    await msg.edit("✂️ Dividiendo y comprimiendo...")
    compressed_parts = process_file(file_path)

    await msg.edit("☁️ Subiendo a Archive.org...")
    item_name = Path(file_path).name
    link = upload_to_archive(compressed_parts, item_name)

    txt_path = create_txt(link, item_name)
    await msg.delete()
    await message.reply_document(
        document=txt_path,
        caption="📄 Aquí tienes tu enlace de descarga"
    )

    cleanup([file_path, txt_path] + compressed_parts)

# =========================
# 🌐 LINKS DIRECTOS
# =========================
@app_bot.on_message(filters.text)
async def handle_links(client, message):
    url = message.text.strip()
    if url.startswith("http"):
        msg = await message.reply("🌐 Descargando desde URL...")
        try:
            filename = url.split("/")[-1] or "file.bin"
            path = DOWNLOAD_PATH / filename

            with requests.get(url, stream=True) as r:
                with open(path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)

            await msg.edit("✂️ Dividiendo y comprimiendo...")
            compressed_parts = process_file(path)

            await msg.edit("☁️ Subiendo a Archive.org...")
            link = upload_to_archive(compressed_parts, filename)

            txt_path = create_txt(link, filename)
            await msg.delete()
            await message.reply_document(
                document=txt_path,
                caption="📄 Aquí tienes tu enlace de descarga"
            )

            cleanup([path, txt_path] + compressed_parts)
        except Exception as e:
            await msg.edit(f"❌ Error: {e}")

# =========================
# 🌍 FLASK (HILO SECUNDARIO)
# =========================
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Bot activo ✅"

def run_web():
    web_app.run(host="0.0.0.0", port=Config.PORT)

# =========================
# 🚀 MAIN
# =========================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    print("🤖 Bot iniciado...")
    app_bot.run()
