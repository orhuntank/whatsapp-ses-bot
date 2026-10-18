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

# --- UYKU ENGELLEYİCİ (Render'ı Uyutmaz) ---
def kendi_kendini_uyandir():
    time.sleep(30)
    url = "https://whatsapp-ses-bot.onrender.com"
    while True:
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass
        time.sleep(240)  # Her 4 dakikada bir ping

# --- BAĞLANTI BİLGİLERİ ---
ID_INSTANCE = "710722770788"
API_TOKEN = "365b2fe3080245e5a7e2af4a15638f14d3fbd2d0e8cd4f76a5"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

# Test Grubu (Deneme)
CHAT_ID = "120363413102409810@g.us"

MAGAZALAR = [
    "8219", "4043", "5658", "9549", "8634", 
    "8635", "9631", "9687", "8881", "8311", 
    "8914", "4289", "9671", "4229", "4945", 
    "4983", "9590", "3569", "6148", "6162"
]

# HAFIZA (RAM + Dinamik Güncelleme)
DURUM = {kod: "BEKLIYOR" for kod in MAGAZALAR}

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
    except Exception as e:
        print(f"Anket hatası ({magaza_kodu}): {e}")

# --- ZAMANLANMIŞ GÖREVLER ---

def gorev_0900_anketleri_baslat():
    global DURUM
    DURUM = {kod: "BEKLIYOR" for kod in MAGAZALAR}
    mesaj_gonder("📢 *Günaydın! Günlük ses kontrol anketleri açılıyor...*")
    
    for kod in MAGAZALAR:
        anket_gonder(kod)
        time.sleep(1.2)

    mesaj_gonder("✅ *Tüm mağaza anketleri paylaşıldı. Lütfen kontroller tamamlandığında durumunuzu işaretleyiniz.*")

def gorev_1700_hatirlatma():
    bekleyenler = [kod for kod, dur in DURUM.items() if dur == "BEKLIYOR"]
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

def rapor_gonder(kapanis_mi=False):
    tamamlayanlar = [kod for kod, d in DURUM.items() if d == "YAPILDI"]
    sorunlular = [kod for kod, d in DURUM.items() if d == "SORUN_VAR"]
    eksikler = [kod for kod, d in DURUM.items() if d == "BEKLIYOR"]
    
    su_an = datetime.now().strftime("%H:%M")
    tarih_str = datetime.now().strftime("%d.%m.%Y")
    
    baslik = f"📊 *GÜNLÜK SES KONTROLÜ RAPORU* ({tarih_str})" if kapanis_mi else f"⏱️ *SES KONTROLÜ CANLI DURUM* ({su_an})"
    alt_bilgi = "Kontrol süresi dolmuştur (18:00)." if kapanis_mi else f"Anlık sorgulama saati: {su_an}"

    rapor = (
        f"{baslik}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Sorunsuz Tamamlananlar ({len(tamamlayanlar)}):*\n"
        + (", ".join(tamamlayanlar) if tamamlayanlar else "Yok") + "\n\n"
        f"⚠️ *Sorun Bildiren Mağazalar ({len(sorunlular)}):*\n"
        + (", ".join(sorunlular) if sorunlular else "Yok 👏") + "\n\n"
        f"❌ *Hiç İşaretlemeyenler ({len(eksikler)}):*\n"
        + (", ".join(eksikler) if eksikler else "Tüm mağazalar katılım sağladı! 👏") + "\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{alt_bilgi}"
    )
    mesaj_gonder(rapor)

def gorev_1800_kapanis_raporu():
    rapor_gonder(kapanis_mi=True)

# --- ZIRHLI OY VE MESAJ DİNLEME ---
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
        body_raw = str(body)

        # 1. ANKET OYU YAKALAMA
        if "poll" in type_webhook.lower() or "vote" in type_webhook.lower():
            # Hangi mağaza?
            hedef_magaza = None
            for kod in MAGAZALAR:
                if kod in body_raw:
                    hedef_magaza = kod
                    break

            if hedef_magaza:
                # Oylanan şıkkı net tespit et
                message_data = body.get("messageData", {})
                vote_info = message_data.get("pollVoteMessageData", {})
                votes = vote_info.get("votes", [])
                
                secimler = " ".join([str(v) for v in votes]) + " " + body_raw

                # Önce 'Sorun Var' kontrolü (bizzat seçilmişse)
                if "'Sorun Var" in secimler or "Sorun Var ❌" in secimler:
                    DURUM[hedef_magaza] = "SORUN_VAR"
                    print(f"⚠️ [ARIZA] {hedef_magaza} sorun bildirdi.")
                elif "'Yapıldı" in secimler or "Yapıldı ✅" in secimler or "Yapildi" in secimler:
                    DURUM[hedef_magaza] = "YAPILDI"
                    print(f"🟢 [OK] {hedef_magaza} sorunsuz tamamlandı.")

        # 2. METİN MESAJI İLE YEDEKLEME (Örn: Mağaza '8219 yapıldı' yazarsa da yakalar)
        for kod in MAGAZALAR:
            if kod in body_raw:
                if any(x in body_raw.lower() for x in ["ariza", "arıza", "sorun", "calismiyor", "çalışmıyor"]):
                    DURUM[kod] = "SORUN_VAR"
                elif any(x in body_raw.lower() for x in ["tamam", "ok", "yapildi", "yapıldı", "calisiyor", "çalışıyor"]):
                    DURUM[kod] = "YAPILDI"

        # 3. CANLI SORGULAMA KOMUTU (!durum veya !rapor)
        if "!durum" in body_raw.lower() or "!rapor" in body_raw.lower():
            rapor_gonder(kapanis_mi=False)

        # Bildirimi Green-API kuyruğundan sil
        if receipt_id:
            del_url = f"{BASE_URL}/deleteNotification/{API_TOKEN}/{receipt_id}"
            requests.delete(del_url, timeout=5)

    except Exception:
        pass

if __name__ == "__main__":
    # 1. Flask Web Servisi
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    # 2. Uyku Engelleyici
    t_ping = threading.Thread(target=kendi_kendini_uyandir)
    t_ping.daemon = True
    t_ping.start()

    # 3. Görev Saatleri (Türkiye Saati)
    sched = BackgroundScheduler(timezone="Europe/Istanbul")
    sched.add_job(gorev_0900_anketleri_baslat, 'cron', hour=9, minute=0)
    sched.add_job(gorev_1700_hatirlatma, 'cron', hour=17, minute=0)
    sched.add_job(gorev_1800_kapanis_raporu, 'cron', hour=18, minute=0)
    sched.start()

    print("Bot basariyla baslatildi. Tam kalici dinleme modunda...")

    while True:
        gelen_bildirimleri_dinle()
        time.sleep(1)
