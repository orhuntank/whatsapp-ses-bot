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

# --- KALICI VERİ YÖNETİMİ (Sunucu Resetlense Bile Kaybolmaz) ---
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

    mesaj_gonder("✅ *Tüm mağaza anketleri paylaşıldı. Lütfen kontroller tamamlandığında durumunuzu işaretleyiniz.*")

def gorev_1700_hatirlatma():
    veri = durumu_yukle()
    bekleyenler = [kod for kod, dur in veri["durum"].items() if dur == "BEKLIYOR"]
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

def rapor_olustur(kapanis_mi=False):
    veri = durumu_yukle()
    durum_sozlugu = veri["durum"]
    
    tamamlayanlar = [kod for kod, d in durum_sozlugu.items() if d == "YAPILDI"]
    sorunlular = [kod for kod, d in durum_sozlugu.items() if d == "SORUN_VAR"]
    eksikler = [kod for kod, d in durum_sozlugu.items() if d == "BEKLIYOR"]
    
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
    rapor_olustur(kapanis_mi=True)

def gelen_bildirimleri_dinle():
    url = f"{BASE_URL}/receiveNotification/{API_TOKEN}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if not data:
            return

        receipt_id = data.get("receiptId")
        body = data.get("body", {})
        body_str = str(body)

        # 1. Anket Oyu Yakalama (Gelen tüm veri paketini tara)
        if "poll" in body_str.lower() or "vote" in body_str.lower():
            veri = durumu_yukle()
            degisiklik_var = False

            for kod in MAGAZALAR:
                if kod in body_str:
                    if "Sorun Var" in body_str:
                        veri["durum"][kod] = "SORUN_VAR"
                        degisiklik_var = True
                        print(f"⚠️ [SORUN] Mağaza {kod} arıza bildirdi.")
                    elif "Yapıldı" in body_str or "Yapildi" in body_str:
                        veri["durum"][kod] = "YAPILDI"
                        degisiklik_var = True
                        print(f"🟢 [TAMAM] Mağaza {kod} kontrolü tamamladı.")

            if degisiklik_var:
                durumu_kaydet(veri)

        # 2. Canlı Sorgulama: !durum yazıldığında anlık tabloyu at
        if "!durum" in body_str.lower() or "!rapor" in body_str.lower():
            rapor_olustur(kapanis_mi=False)

        # Bildirimi kuyruktan temizle
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
    
    print("Bot basariyla baslatildi. Kalici veri modu devrede...")

    while True:
        gelen_bildirimleri_dinle()
        time.sleep(1)
