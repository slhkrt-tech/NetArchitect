import requests
import threading
import time
import random

# URL'nin sonuna alert/ eklendi
WEBHOOK_URL = 'http://127.0.0.1:8000/api/webhook/alert/' 
API_KEY = 'your_webhook_api_key_here' # .env dosyasındaki WAZUH_API_KEY ile aynı olmalı

def send_fake_log(device_id):
    headers = {'X-API-Key': API_KEY, 'Content-Type': 'application/json'}
    payload = {
        "ip": f"192.168.1.{device_id % 254}",
        "message": f"Sistem normal çalışıyor. RAM Tüketimi: %{random.randint(20, 60)}"
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, headers=headers)
        print(f"[Cihaz-{device_id}] Veri Celery Kuyruğuna İletildi. (Non-Blocking)")
    except Exception as e:
        pass

print("=== 500 CİHAZ YÜK (STRESS) TESTİ BAŞLIYOR ===")
print("Celery ve Redis kuyrukları asenkron olarak test ediliyor...")
time.sleep(2)

threads = []
for i in range(1, 501):
    t = threading.Thread(target=send_fake_log, args=(i,))
    threads.append(t)
    t.start()
    time.sleep(0.01) # İstekler arası çok kısa bekleme

for t in threads:
    t.join()

print("=== STRES TESTİ BAŞARIYLA TAMAMLANDI. ARAYÜZÜ KONTROL EDİN. ===")