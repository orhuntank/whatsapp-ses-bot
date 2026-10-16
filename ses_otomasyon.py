import os
import time
import threading
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

# --- RENDER WEB SUNUCUSU (Sistemi 7/24 Ayakta Tutar) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Ses Kontrol Botu 7/24 Aktif ve Calisiyor!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- BAĞLANTI BİLGİLERİ ---
ID_INSTANCE = "710722770788"
API_TOKEN = "365b2fe3080245e5a7e2af4a15638f14d3fbd2d0e8cd4f76a5"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

# Test Grubu (Aşk Grubu) ID'si
CHAT_ID = "120363413102409810@g.us"

# 20 Mağaza Kodunuz
MAGAZALAR = [
    "8219", "4043", "5658", "9549", "8634", 
    "8635", "9631", "9687", "8881", "8311", 
    "8914", "4289", "9671", "4229", "4945", 
    "4983", "9590", "3569", "6148", "6162"
]

gunluk_durum = {kod: False for kod in MAGAZALAR}

def mesaj_gonder(metin):
    url = f"{BASE_URL}/sendMessage/{API_TOKEN}"
    payload = {"chatId": CHAT_ID, "message": metin}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Mesaj hatasi: {e}")

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
        print(f"Magaza {magaza_kodu} anketi acildi.")
    except Exception as e:
        print(f"Anket hatasi ({magaza_kodu}): {e}")

def gorev_0900_anketleri_baslat():
    global gunluk_durum
    gunluk_durum = {kod: False for kod in MAGAZALAR}
    mesaj_gonder("📢 *Günaydın! Günlük ses kontrol anketleri açılıyor...*")
    
    for kod in MAGAZALAR:
        anket_gonder(kod)
        time.sleep(1.5)

    mesaj_gonder("✅ *Tüm mağaza anketleri paylaşıldı. Lütfen kontroller tamamlandığında işaretleyiniz.*")

def gorev_1700_hatirlatma():
    yapmayanlar = [kod for kod, durum in gunluk_durum.items() if not durum]
    if not yapmayanlar:
        mesaj_gonder("🎉 *Tebrikler! Saat 17:00 itibarıyla tüm mağazalar ses kontrolünü tamamladı.*")
        return

    uyari = (
        f"⚠️ *DİKKAT: SES KONTROLÜ HATIRLATMASI (17:00)*\n\n"
        f"Henüz işaretleme yapmayan *{len(yapmayanlar)}* mağazamız:\n"
        f"👉 *{', '.join(yapmayanlar)}*\n\n"
        f"Lütfen saat *18:00*'e kadar anket üzerinden durumunuzu belirtiniz!"
    )
    mesaj_gonder(uyari)

def gorev_1800_kapanis_raporu():
    tamamlayanlar = [kod for kod, durum in gunluk_durum.items() if durum]
    eksikler = [kod for kod, durum in gunluk_durum.items() if not durum]
    tarih_str = datetime.now().strftime("%d.%m.%Y")
    
    rapor = (
        f"📊 *GÜNLÜK SES KONTROLÜ RAPORU* ({tarih_str})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Tamamlayanlar ({len(tamamlayanlar)}/{len(MAGAZALAR)}):*\n"
        + (", ".join(tamamlayanlar) if tamamlayanlar else "Hiçbiri") + "\n\n"
        f"❌ *Eksik Kalanlar ({len(eksikler)}/{len(MAGAZALAR)}):*\n"
        + (", ".join(eksikler) if eksikler else "Tüm mağazalar eksiksiz tamamladı! 👏") + "\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Kontrol süresi dolmuştur (18:00)."
    )
    mesaj_gonder(rapor)

def gelen_oylari_dinle():
    url = f"{BASE_URL}/receiveNotification/{API_TOKEN}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data:
            receipt_id = data.get("receiptId")
            body = data.get("body", {})
            type_webhook = body.get("typeWebhook")

            if type_webhook == "pollVoteMessage":
                message_data = body.get("messageData", {})
                poll_name = message_data.get("pollMessageData", {}).get("name", "")
                votes = message_data.get("pollVoteMessageData", {}).get("votes", [])

                for kod in MAGAZALAR:
                    if kod in poll_name:
                        for vote in votes:
                            if "Yapıldı" in vote.get("optionName", ""):
                                gunluk_durum[kod] = True
                                print(f"🟢 Magaza {kod} ses kontrolunu yapti.")

            del_url = f"{BASE_URL}/deleteNotification/{API_TOKEN}/{receipt_id}"
            requests.delete(del_url, timeout=5)
    except Exception:
        pass

if __name__ == "__main__":
    # Web sunucusunu arka planda başlat
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Zamanlayıcı görevlerini başlat (Türkiye Saati: UTC+3)
    sched = BackgroundScheduler(timezone="Europe/Istanbul")
    sched.add_job(gorev_0900_anketleri_baslat, 'cron', hour=9, minute=0)
    sched.add_job(gorev_1700_hatirlatma, 'cron', hour=17, minute=0)
    sched.add_job(gorev_1800_kapanis_raporu, 'cron', hour=18, minute=0)
    sched.start()
    
    print("Bot basariyla baslatildi. 7/24 dinleme devrede...")

    while True:
        gelen_oylari_dinle()
        time.sleep(1)
