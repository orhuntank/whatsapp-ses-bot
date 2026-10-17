import os
import time
import threading
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

# --- WEB SUNUCUSU ---
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
            print("🟢 [Anti-Sleep] Kendi kendine ping atıldı.")
        except Exception as e:
            print(f"Ping hatası: {e}")
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

gunluk_durum = {kod: "BEKLIYOR" for kod in MAGAZALAR}
# Anket Mesaj ID'si -> Mağaza Kodu eşleştirmesi
anket_id_haritasi = {}

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
        resp = requests.post(url, json=payload, timeout=10)
        res_data = resp.json()
        # Anketin oluşturulan mesaj ID'sini hafızaya al
        msg_id = res_data.get("idMessage")
        if msg_id:
            anket_id_haritasi[msg_id] = magaza_kodu
            print(f"Mağaza {magaza_kodu} anketi açıldı (ID: {msg_id})")
    except Exception as e:
        print(f"Anket hatası ({magaza_kodu}): {e}")

def gorev_0900_anketleri_baslat():
    global gunluk_durum, anket_id_haritasi
    gunluk_durum = {kod: "BEKLIYOR" for kod in MAGAZALAR}
    anket_id_haritasi = {}
    
    mesaj_gonder("📢 *Günaydın! Günlük ses kontrol anketleri açılıyor...*")
    
    for kod in MAGAZALAR:
        anket_gonder(kod)
        time.sleep(1.5)

    mesaj_gonder("✅ *Tüm mağaza anketleri paylaşıldı. Lütfen kontroller tamamlandığında durumunuzu işaretleyiniz.*")

def gorev_1700_hatirlatma():
    bekleyenler = [kod for kod, durum in gunluk_durum.items() if durum == "BEKLIYOR"]
    if not bekleyenler:
        mesaj_gonder("🎉 *Saat 17:00 itibarıyla tüm mağazalarımız kontrol durumunu bildirmiştir.*")
        return

    uyari = (
        f"⚠️ *DİKKAT: SES KONTROLÜ HATIRLATMASI (17:00)*\n\n"
        f"Henüz işaretleme yapmayan *{len(bekleyenler)}* mağazamız:\n"
        f"👉 *{', '.join(bekleyenler)}*\n\n"
        f"Lütfen saat *18:00*'e kadar anketi işaretleyiniz!"
    )
    mesaj_gonder(uyari)

def gorev_1800_kapanis_raporu():
    tamamlayanlar = [kod for kod, durum in gunluk_durum.items() if durum == "YAPILDI"]
    sorunlular = [kod for kod, durum in gunluk_durum.items() if durum == "SORUN_VAR"]
    eksikler = [kod for kod, durum in gunluk_durum.items() if durum == "BEKLIYOR"]
    tarih_str = datetime.now().strftime("%d.%m.%Y")
    
    rapor = (
        f"📊 *GÜNLÜK SES KONTROLÜ RAPORU* ({tarih_str})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Sorunsuz Tamamlananlar ({len(tamamlayanlar)}):*\n"
        + (", ".join(tamamlayanlar) if tamamlayanlar else "Yok") + "\n\n"
        f"⚠️ *Sorun Bildiren Mağazalar ({len(sorunlular)}):*\n"
        + (", ".join(sorunlular) if sorunlular else "Yok 👏") + "\n\n"
        f"❌ *Hiç İşaretlemeyenler ({len(eksikler)}):*\n"
        + (", ".join(eksikler) if eksikler else "Tüm mağazalar katılım sağladı! 👏") + "\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Kontrol süresi dolmuştur (18:00)."
    )
    mesaj_gonder(rapor)

def gelen_bildirimleri_dinle():
    url = f"{BASE_URL}/receiveNotification/{API_TOKEN}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if not data:
            return

        receipt_id = data.get("receiptId")
        body = data.get("body", {})
        type_webhook = body.get("typeWebhook", "")
        body_str = str(body)

        # 1. Anket Oyu Yakalama (Hem ID hem Metin Üzerinden Çift Eşleme)
        if "poll" in type_webhook.lower() or "vote" in type_webhook.lower():
            bulunan_magaza = None

            # Yöntem A: Mesaj ID'sinden bul
            for msg_id, kod in anket_id_haritasi.items():
                if msg_id in body_str:
                    bulunan_magaza = kod
                    break

            # Yöntem B: Metin içindeki mağaza kodundan bul
            if not bulunan_magaza:
                for kod in MAGAZALAR:
                    if kod in body_str:
                        bulunan_magaza = kod
                        break

            if bulunan_magaza:
                if "Sorun Var" in body_str:
                    gunluk_durum[bulunan_magaza] = "SORUN_VAR"
                    print(f"⚠️ [SORUN] Mağaza {bulunan_magaza} sorun bildirdi.")
                elif "Yapıldı" in body_str or "Yapildi" in body_str:
                    gunluk_durum[bulunan_magaza] = "YAPILDI"
                    print(f"🟢 [TAMAM] Mağaza {bulunan_magaza} kontrolü tamamladı.")

        # 2. Canlı Komut Kontrolü (!durum veya !rapor)
        if "!durum" in body_str.lower() or "!rapor" in body_str.lower():
            gorev_1800_kapanis_raporu()

        if receipt_id:
            del_url = f"{BASE_URL}/deleteNotification/{API_TOKEN}/{receipt_id}"
            requests.delete(del_url, timeout=5)

    except Exception:
        pass

if __name__ == "__main__":
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    t_ping = threading.Thread(target=kendi_kendini_uyandir)
    t_ping.daemon = True
    t_ping.start()

    sched = BackgroundScheduler(timezone="Europe/Istanbul")
    sched.add_job(gorev_0900_anketleri_baslat, 'cron', hour=9, minute=0)
    sched.add_job(gorev_1700_hatirlatma, 'cron', hour=17, minute=0)
    sched.add_job(gorev_1800_kapanis_raporu, 'cron', hour=18, minute=0)
    sched.start()
    
    print("Bot basariyla baslatildi. Dinleme devrede...")

    while True:
        gelen_bildirimleri_dinle()
        time.sleep(1)
