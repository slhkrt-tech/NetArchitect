from django.test import TestCase


class InventorySmokeTests(TestCase):
    def test_smoke(self):
        """Basit duman testi: test framework'ün çalıştığını doğrular."""
        self.assertTrue(True)


if __name__ == '__main__':
    # Örnek webhook çağrusu sadece doğrudan script olarak çalıştırıldığında gönderilir.
    import requests

    payload = {
        "ip": "192.168.1.10",
        "message": "%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down."
    }

    try:
        response = requests.post("http://127.0.0.1:8000/api/webhook/alert/", json=payload, timeout=5)
        print(response.json())
    except Exception as e:
        print(f"Webhook örneği çalıştırılamadı: {e}")