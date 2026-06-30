# 🌐 OmniOps: AIOps & Network Management System

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-Web_Framework-092E20?style=for-the-badge&logo=django)
![Celery](https://img.shields.io/badge/Celery-Asynchronous_Task_Queue-37814A?style=for-the-badge&logo=celery)
![Redis](https://img.shields.io/badge/Redis-Message_Broker-DC382D?style=for-the-badge&logo=redis)

**OmniOps**, kurumsal ağ altyapılarını yönetmek, otomatize etmek ve otonom güvenlik kararları (AIOps) almak için geliştirilmiş kapsamlı bir Ağ Yönetim (NMS) ve IT Hizmet Yönetimi (ITSM) platformudur.

Sistem, darboğazları önlemek için asenkron mesaj kuyruğu (Producer-Consumer) mimarisi üzerine inşa edilmiş olup, fiziksel veri merkezi haritalamasından, derin ağ keşfine kadar birçok gelişmiş mühendislik algoritması barındırmaktadır.

---

## 🚀 Öne Çıkan Özellikler ve Algoritmalar

* 🧠 **AIOps Otonom Kural Motoru (Rule-Based Expert System):** Webhook üzerinden gelen ağ loglarını parse eder. Kritik saldırıları (örn: Brute-Force, Broadcast Storm) saniyeler içinde analiz eder ve Celery üzerinden hedefe yönelik *Active Response* (Otonom Engelleme) uygular.
* ⚡ **Asenkron Dağıtık Mimari:** 500+ cihaza aynı anda konfigürasyon gönderimi yapabilmek için **Celery & Redis** entegrasyonu ile *Producer-Consumer* deseni kullanılmıştır. Ana thread asla kilitlenmez.
* 🕸️ **Graf Teorisi ile Ağ Topolojisi:** Ağdaki donanımları ve ilişkilerini (Node & Edge) *Force-Directed Graph* algoritması kullanarak interaktif bir topoloji haritasına dönüştürür.
* 💾 **Konfigürasyon Fark Analizi (Config Diff):** Cihaz yedekleri arasındaki farkları *Longest Common Subsequence (LCS)* türevi algoritmalarla tespit edip görselleştirir.
* 📊 **Zaman Serisi Isı Haritası:** Log frekanslarını 7x24 boyutunda bir matris ile kümeleyerek sistem yoğunluğunu anlamlı bir ısı haritasına (Heatmap) dönüştürür.
* 🗄️ **Dinamik Kabin (Rack) Haritalama:** Donanımların U yüksekliklerini matematiksel olarak hesaplayıp, *Absolute Positioning* ile 42U'luk fiziksel veri merkezi görünümü oluşturur.
* 🧮 **Görsel IPAM & Subnet Hesaplama:** IP bloklamalarını *Bitwise (Bit düzeyinde)* algoritmalarla hesaplayıp görsel bir matris üzerinde dolu/boş durumunu haritalandırır.
* 🔒 **Rol ve Nesne Bazlı Yetkilendirme (RBAC & OLP):** Django-Guardian kullanılarak her yöneticinin sadece kendi zimmetindeki cihazları görmesi sağlanmıştır.

---

## 🛠️ Kurulum ve Çalıştırma (Geliştirici Ortamı)

Projeyi kendi bilgisayarınızda test etmek için aşağıdaki adımları sırasıyla uygulayınız.

### 1. Gereksinimler
* **Python 3.9+**
* **Redis Server** (Asenkron kuyruk işlemleri için zorunludur. Docker üzerinden çalıştırılması tavsiye edilir).
* **Git**

### 2. Projeyi Klonlayın
```bash
git clone [https://github.com/slhkrt-tech/OmniOps.git](https://github.com/slhkrt-tech/OmniOps.git)
cd OmniOps

Sanal Ortam (Virtual Environment) ve Bağımlılıklar

python -m venv venv
# Windows için:
venv\Scripts\activate
# Linux/Mac için:
# source venv/bin/activate

pip install -r requirements.txt

Çevre Değişkenleri

Proje ana dizininde .env adında bir dosya oluşturun ve Webhook güvenlik şifresini belirleyin:

WAZUH_API_KEY=omniops_gizli_sifre_2026

Veritabanı Kurulumu

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # Admin hesabı oluşturun

Redis ve Celery'yi Başlatın

Asenkron işlemlerin ve AIOps engelleme simülasyonlarının çalışması için sistemde Redis açık olmalıdır:

# Eğer Docker kullanıyorsanız Redis'i tek komutla başlatın:
docker run -d -p 6379:6379 redis

# Yeni bir terminal sekmesi açın (venv aktifken) ve Celery Worker'ı başlatın:
celery -A core worker -l info --pool=solo

Sunucuyu Başlatın

Ana terminalinize dönün ve Django projesini ayağa kaldırın:

python manage.py runserver

Sisteme http://127.0.0.1:8000 adresinden giriş yapabilirsiniz.

---

## Müşteri / Production Kurulum Kontrol Listesi

1. `.env.example` dosyasını `.env` olarak kopyalayın ve aşağıdaki değerleri mutlaka değiştirin:
   - `DJANGO_SECRET_KEY`
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
   - `POSTGRES_PASSWORD`
   - `WAZUH_API_KEY`
   - `REMOTE_PROBE_SHARED_SECRET`

2. İlk kurulum:
```bash
docker compose up --build -d
```

3. Sağlık kontrolü:
```bash
curl http://127.0.0.1:8000/health/
```

4. TLS/Reverse proxy kullanıyorsanız:
   - Proxy HTTPS terminasyonu yapıyorsa `SECURE_SSL_REDIRECT=False` bırakılabilir.
   - Uygulama doğrudan HTTPS sunuyorsa `SECURE_SSL_REDIRECT=True` kullanılmalıdır.
   - Canlı domain `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS` içinde yer almalıdır.

5. Production doğrulama:
```bash
python manage.py check
python manage.py test inventory
```

6. Kalıcı veriler:
   - PostgreSQL: `postgres_data`
   - Redis: `redis_data`
   - Kullanıcı dosyaları: `media_data`
   - Uygulama logları: `logs_data`

Not: Derin ağ taraması için container `NET_RAW` ve `NET_ADMIN` capability ile çalışır. Bu, tam `privileged` moddan daha dar bir yetki setidir.

