import requests
import time

# URL'nin sonuna alert/ eklendi
WEBHOOK_URL = 'http://127.0.0.1:8000/api/webhook/alert/' 
API_KEY = 'your_webhook_api_key_here' # .env dosyasındaki WAZUH_API_KEY ile aynı olmalı

headers = {'X-API-Key': API_KEY, 'Content-Type': 'application/json'}

print("--- AIOps ÇÖKME VE SİBER SALDIRI SİMÜLASYONU BAŞLATILIYOR ---")
time.sleep(1)

# Sistemin çöküşünü ve SLA alarmını tetikleyecek kritik veri
payload = {
    "ip": "10.0.0.5", # Ağda var olan bir cihazın IP'si (Eğer farklıysa değiştir)
    "message": "[CRITICAL] CPU %99 seviyesinde darboğaza ulaştı! SSH Brute-Force algılandı.",
    "attacker_ip": "192.168.50.100"
}

print("Kritik saldırı ve darboğaz verisi sisteme (Webhook) enjekte ediliyor...")
try:
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    if response.status_code == 200:
        print("BAŞARILI: Veri iletildi. Lütfen Dashboard'u yenileyin!")
        print("Beklenen Sonuç: Kırmızı AIOps uyarısı ve Otonom Destek Bileti.")
    else:
        print(f"HATA: Sunucu reddetti. Kod: {response.status_code}")
except Exception as e:
    print(f"Bağlantı Hatası: {e}")