import os
import json
import time
import threading
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

# --- WEB SUNUCUSU (Render'ı Uyanık Tutmak İçin) ---
app = Flask(__name__)

@app.route('/')
def home():
    return f"Ses Kontrol Botu Aktif! Sunucu Saati: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- UYKU ENGELLEYİCİ ---
def kendi_kendini_uyandir():
    time.sleep(30)
    url = "https://whatsapp-ses-bot.onrender.com"
    while True:
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass
        time.sleep(300)

# --- BAĞLANTI BİLGİLERİ ---
ID_INSTANCE = "710722770788"
API_TOKEN = "365b2fe3080245e5a7e2af4a15638f14d3fbd2d0e8cd4f76a5"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

CHAT_ID = "120363413102409810@g.us"

MAGAZALAR = [
    "8219", "4043", "5658", "9549", "8634", 
    "8635", "9631", "9687", "8881", "8311", 
    "8914", "4289", "9671", "4229", "4945", 
    "4983", "9590", "3569", "6148", "6162"
]

DURUM_DOSYASI = "gunluk_durum.json"

# --- KALICI VERİ YÖNETİMİ ---
def durumu_yukle():
    if os.path.exists(DURUM_DOSYASI):
        try:
            with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tarih": datetime.now().strftime("%d.%m.%Y"), "durum": {kod: "BEKLIYOR" for kod in MAGAZALAR}}

def durumu_kaydet(veri):
    try:
        with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Kayıt hatası: {e}")

def mesaj_gonder(metin):
    url = f"{BASE_URL}/sendMessage/{API_TOKEN}"
    payload = {"chatId": CHAT_ID, "message": metin}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Mesaj hatası: {e}")

def anket_gonder(magaza_kodu):
    url = f"{BASE_URL}/sendPoll/{API_TOKEN}"
    tarih_str = datetime.now().strftime("%d.%m.%Y")
    payload = {
        "chatId": CHAT_ID,
        "message": f"🔊 Mağaza {magaza_kodu} | Ses Kontrolü ({tarih_str})",
        "options": [
            {"optionName": "Yapıldı ✅"},
            {"optionName": "Sorun Var ❌"}
        ],
        "multipleAnswers": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"Mağaza {magaza_kodu} anketi açıldı.")
    except Exception as e:
        print(f"Anket hatası ({magaza_kodu}): {e}")

# --- GÖREVLER ---

def gorev_0900_anketleri_baslat():
    veri = {"tarih": datetime.now().strftime("%d.%m.%Y"), "durum": {kod: "BEKLIYOR" for kod in MAGAZALAR}}
    durumu_kaydet(veri)
    
    mesaj_gonder("📢 *Günaydın! Günlük ses kontrol anketleri açılıyor...*")
    
    for kod in MAGAZALAR:
        anket_gonder(kod)
        time.sleep(1.5)

    mesaj_gonder("✅ *Tüm mağaza anketleri paylaşıldı. Lütfen kontroller tamamlandığında durumunuz
