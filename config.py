import os

class Config:
    API_ID = int(os.getenv("API_ID", "29007359"))
    API_HASH = os.getenv("API_HASH", "f9ac0af85457b9d39df7f7f871850bf2")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8364195049:AAGztUzFNCOgbgCK9ljiT-pke2i2HvEbpoo")

    ACCESS_KEY = os.getenv("ACCESS_KEY", "cSJ5mt4X9273jBtt")
    SECRET_KEY = os.getenv("SECRET_KEY", "hQqXfcPbr0pQA0o4")

    PORT = int(os.getenv("PORT", 10000))